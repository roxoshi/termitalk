"""TermiTalk — main entry point and daemon loop."""

import argparse
import logging
import platform
import signal
import sys
import threading
import time

from termitalk import __version__, config
from termitalk.doctor import check_dependencies

logger = logging.getLogger("termitalk")

# ANSI colors for terminal output
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_RESET = "\033[0m"


def _load_app_modules():
    """Import heavy dependencies (audio, model, etc.) after arg parsing."""
    from termitalk.audio import Recorder, trim_silence
    from termitalk.transcriber import load_model, warm_up, transcribe, get_backend
    from termitalk.formatter import format_text, load_user_corrections
    from termitalk.injector import inject_text
    from termitalk.hotkey import HotkeyListener
    from termitalk import sounds
    from termitalk.history import log_transcription, show_history

    return {
        "Recorder": Recorder, "trim_silence": trim_silence,
        "load_model": load_model, "warm_up": warm_up,
        "transcribe": transcribe, "get_backend": get_backend,
        "format_text": format_text, "load_user_corrections": load_user_corrections,
        "inject_text": inject_text, "HotkeyListener": HotkeyListener,
        "sounds": sounds,
        "log_transcription": log_transcription, "show_history": show_history,
    }


# Populated by _load_app_modules() before TermiTalk is instantiated
_m: dict = {}


class TermiTalk:
    """Core application: wires hotkey → recorder → transcriber → formatter → injector."""

    def __init__(self):
        self._recorder = _m["Recorder"]()
        self._processing_lock = threading.Lock()
        self._hotkey = _m["HotkeyListener"](
            on_activate=self._on_record_start,
            on_deactivate=self._on_record_stop,
        )

    def _on_record_start(self):
        """Called when the push-to-talk hotkey is pressed."""
        _m["sounds"].play("start")
        self._recorder.start()
        _status("recording", "Listening...")

    def _on_record_stop(self):
        """Called when the push-to-talk hotkey is released."""
        audio = self._recorder.stop()

        if audio is None or len(audio) == 0:
            _m["sounds"].play("error")
            _status("warn", "No audio captured")
            return

        # Process in the current thread (already off the main thread via hotkey callback)
        with self._processing_lock:
            t0 = time.perf_counter()
            _status("processing", "Processing...")

            # VAD: trim silence
            trimmed = _m["trim_silence"](audio)
            if trimmed is None:
                _m["sounds"].play("error")
                _status("warn", "No speech detected")
                return

            # Transcribe
            raw_text = _m["transcribe"](trimmed)
            if not raw_text:
                _m["sounds"].play("error")
                _status("warn", "No text recognized")
                return

            # Format
            formatted = _m["format_text"](raw_text)
            if not formatted:
                _m["sounds"].play("error")
                _status("warn", "Empty after formatting")
                return

            elapsed_ms = (time.perf_counter() - t0) * 1000
            _m["sounds"].play("stop")
            _status("result", formatted)

            # Log to history
            _m["log_transcription"](raw_text, formatted, elapsed_ms)

            # Inject into active window
            _m["inject_text"](formatted)

    def run(self):
        """Start the daemon."""
        _banner()
        _check_macos_accessibility()
        _print_config()

        # Load user corrections
        n = _m["load_user_corrections"]()
        if n > 0:
            _status("info", f"Loaded {n} custom corrections")

        # Load model and warm up
        _m["load_model"]()
        _m["warm_up"]()

        # Start hotkey listener
        self._hotkey.start()
        print(file=sys.stderr)
        _status("ready", "Ready! Hold hotkey to speak.")
        _m["sounds"].play("ready")

        # Block main thread until interrupted
        shutdown = threading.Event()

        def _handle_signal(sig, frame):
            _status("info", "Shutting down...")
            self._hotkey.stop()
            shutdown.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        shutdown.wait()
        print()


def _banner():
    print(f"""
{_BOLD}{_CYAN}╔══════════════════════════════════════╗
║          T E R M I T A L K           ║
║   Local Speech-to-Text for Terminal  ║
╚══════════════════════════════════════╝{_RESET}
""")


def _check_macos_accessibility():
    """On macOS, check if the process has Accessibility permissions and guide the user."""
    if platform.system() != "Darwin":
        return

    try:
        import subprocess
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke ""'],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            raise PermissionError()
    except Exception:
        terminal = _detect_macos_terminal()
        print(f"""{_YELLOW}{_BOLD}  Accessibility permission required{_RESET}

  macOS needs you to grant Accessibility access so TermiTalk
  can listen for the global hotkey and type into other apps.

  {_BOLD}To fix:{_RESET}
  1. Open {_BOLD}System Settings > Privacy & Security > Accessibility{_RESET}
  2. Click the + button and add {_BOLD}{terminal}{_RESET}
  3. Restart TermiTalk
""", file=sys.stderr)


def _detect_macos_terminal() -> str:
    """Best-effort detection of which terminal app is running on macOS."""
    import os
    term_program = os.environ.get("TERM_PROGRAM", "")
    mapping = {
        "iTerm.app": "iTerm2",
        "Apple_Terminal": "Terminal.app",
        "vscode": "Visual Studio Code",
        "WarpTerminal": "Warp",
        "Alacritty": "Alacritty",
        "ghostty": "Ghostty",
    }
    return mapping.get(term_program, term_program or "your terminal app")


def _print_config():
    """Display active configuration."""
    hotkey_names = " + ".join(k.capitalize() for k in config.HOTKEY_KEYS_SPEC)
    backend = _m["get_backend"]()
    if backend == "mlx-whisper":
        backend_label = "mlx-whisper (Apple Silicon GPU)"
    else:
        backend_label = f"faster-whisper ({config.COMPUTE_TYPE} on {config.DEVICE})"
    fast_tag = f" {_YELLOW}[fast]{_RESET}" if config.MODEL_NAME == "small.en" else ""
    print(f"  {_DIM}Model:{_RESET}   {config.MODEL_NAME} via {backend_label}{fast_tag}", file=sys.stderr)
    print(f"  {_DIM}Hotkey:{_RESET}  {hotkey_names}", file=sys.stderr)
    if config.PASTE_MODE:
        paste_key = "Cmd+V" if platform.system() == "Darwin" else "Ctrl+Shift+V"
        inject_mode = f"paste ({paste_key})"
    else:
        inject_mode = "keystroke"
    print(f"  {_DIM}Inject:{_RESET}  {inject_mode}", file=sys.stderr)
    opts = []
    if config.AUTO_ENTER:
        opts.append("auto-enter")
    if not config.SOUND_ENABLED:
        opts.append("no-sound")
    if config.VERBOSE:
        opts.append("verbose")
    if opts:
        print(f"  {_DIM}Options:{_RESET} {', '.join(opts)}", file=sys.stderr)
    print(file=sys.stderr)


def _status(kind: str, message: str):
    """Print a status line to stderr (so it doesn't mix with piped output)."""
    icons = {
        "recording": f"  {_RED}● REC{_RESET}  ",
        "processing": f"  {_YELLOW}⟳ {_RESET}  ",
        "result": f"  {_GREEN}✓{_RESET}  ",
        "warn": f"  {_YELLOW}⚠{_RESET}  ",
        "ready": f"  {_GREEN}▶{_RESET}  ",
        "info": f"  {_DIM}ℹ{_RESET}  ",
    }
    icon = icons.get(kind, "    ")
    # Overwrite-style for transient statuses; newline for final ones
    if kind in ("recording", "processing"):
        print(f"\r\033[2K{icon}{message}", end="", file=sys.stderr, flush=True)
    else:
        print(f"\r\033[2K{icon}{message}", file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(
        prog="termitalk",
        description="Local, privacy-focused speech-to-text for the terminal.",
    )
    parser.add_argument(
        "--version", action="version", version=f"termitalk {__version__}",
    )
    parser.add_argument(
        "--check", action="store_true", default=False,
        help="Check system dependencies and exit",
    )
    parser.add_argument(
        "--model", default=config.MODEL_NAME,
        help=f"Whisper model name (default: {config.MODEL_NAME})",
    )
    parser.add_argument(
        "--fast", action="store_true", default=False,
        help="Use small.en model for faster inference (overrides --model)",
    )
    parser.add_argument(
        "--backend", default=config.BACKEND,
        choices=["auto", "faster-whisper", "mlx-whisper"],
        help=f"Transcription backend (default: {config.BACKEND}). "
             "auto selects mlx-whisper on Apple Silicon, faster-whisper elsewhere",
    )
    parser.add_argument(
        "--device", default=config.DEVICE,
        choices=["auto", "cpu", "cuda"],
        help=f"Compute device (default: {config.DEVICE})",
    )
    parser.add_argument(
        "--compute-type", default=config.COMPUTE_TYPE,
        help=f"Compute type — int8, float16, float32 (default: {config.COMPUTE_TYPE})",
    )
    parser.add_argument(
        "--hotkey", default=None,
        help='Push-to-talk key combo, e.g. "ctrl+shift+space" or "cmd+alt+r" (default: ctrl+shift+space)',
    )
    parser.add_argument(
        "--auto-enter", action="store_true", default=config.AUTO_ENTER,
        help="Press Enter after injecting text",
    )
    parser.add_argument(
        "--paste", action="store_true", default=config.PASTE_MODE,
        help="Use clipboard paste (Ctrl+Shift+V) instead of keystroke typing — much faster, ideal for Claude Code",
    )
    parser.add_argument(
        "--no-sound", action="store_true", default=False,
        help="Disable audio feedback cues",
    )
    parser.add_argument(
        "--no-history", action="store_true", default=False,
        help="Disable transcription history logging",
    )
    parser.add_argument(
        "--history", action="store_true", default=False,
        help="Show recent transcription history and exit",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=config.VERBOSE,
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()

    # Handle --history: show history and exit
    if args.history:
        from termitalk.history import show_history
        show_history()
        return

    # Apply CLI overrides to config
    if args.hotkey:
        try:
            config.HOTKEY_KEYS_SPEC = config.parse_hotkey(args.hotkey)
        except ValueError as e:
            parser.error(str(e))

    if args.fast:
        config.MODEL_NAME = "small.en"
    else:
        config.MODEL_NAME = args.model
    config.BACKEND = args.backend
    config.DEVICE = args.device
    config.COMPUTE_TYPE = args.compute_type
    config.AUTO_ENTER = args.auto_enter
    config.PASTE_MODE = args.paste
    config.SOUND_ENABLED = not args.no_sound
    config.HISTORY_ENABLED = not args.no_history
    config.VERBOSE = args.verbose

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    # Handle --check: run dependency checks and exit
    if args.check:
        ok = check_dependencies(paste_mode=args.paste)
        sys.exit(0 if ok else 1)

    # Startup health checks
    if not check_dependencies(paste_mode=args.paste):
        print(
            f"\n  {_RED}Cannot start — fix the issues above and try again.{_RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load heavy modules now that deps are verified
    global _m
    _m = _load_app_modules()

    try:
        app = TermiTalk()
        app.run()
    except KeyboardInterrupt:
        print(file=sys.stderr)
    except RuntimeError as e:
        print(f"\n  {_RED}Error:{_RESET} {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(
                f"\n  {_RED}Unexpected error:{_RESET} {e}\n"
                f"  {_DIM}Run with --verbose for full traceback{_RESET}",
                file=sys.stderr,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
