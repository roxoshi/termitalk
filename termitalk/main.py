"""TermiTalk — main entry point and daemon loop."""

import argparse
import logging
import platform
import signal
import sys
import threading

from termitalk import config
from termitalk.audio import Recorder, trim_silence
from termitalk.transcriber import load_model, warm_up, transcribe
from termitalk.formatter import format_text
from termitalk.injector import inject_text
from termitalk.hotkey import HotkeyListener

logger = logging.getLogger("termitalk")

# ANSI colors for terminal output
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_RESET = "\033[0m"


class TermiTalk:
    """Core application: wires hotkey → recorder → transcriber → formatter → injector."""

    def __init__(self):
        self._recorder = Recorder()
        self._processing_lock = threading.Lock()
        self._hotkey = HotkeyListener(
            on_activate=self._on_record_start,
            on_deactivate=self._on_record_stop,
        )

    def _on_record_start(self):
        """Called when the push-to-talk hotkey is pressed."""
        self._recorder.start()
        _status("recording", "Listening...")

    def _on_record_stop(self):
        """Called when the push-to-talk hotkey is released."""
        audio = self._recorder.stop()

        if audio is None or len(audio) == 0:
            _status("warn", "No audio captured")
            return

        # Process in the current thread (already off the main thread via hotkey callback)
        with self._processing_lock:
            _status("processing", "Processing...")

            # VAD: trim silence
            trimmed = trim_silence(audio)
            if trimmed is None:
                _status("warn", "No speech detected")
                return

            # Transcribe
            raw_text = transcribe(trimmed)
            if not raw_text:
                _status("warn", "No text recognized")
                return

            # Format
            formatted = format_text(raw_text)
            if not formatted:
                _status("warn", "Empty after formatting")
                return

            _status("result", formatted)

            # Inject into active window
            inject_text(formatted)

    def run(self):
        """Start the daemon."""
        _banner()
        _check_macos_accessibility()
        _print_config()

        # Load model and warm up
        load_model()
        warm_up()

        # Start hotkey listener
        self._hotkey.start()
        print(file=sys.stderr)
        _status("ready", "Ready! Hold hotkey to speak.")

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
    print(f"  {_DIM}Model:{_RESET}   {config.MODEL_NAME} ({config.COMPUTE_TYPE} on {config.DEVICE})", file=sys.stderr)
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
    print(f"\r{icon}{message}", file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(
        prog="termitalk",
        description="Local, privacy-focused speech-to-text for the terminal.",
    )
    parser.add_argument(
        "--model", default=config.MODEL_NAME,
        help=f"Whisper model name (default: {config.MODEL_NAME})",
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
        "--auto-enter", action="store_true", default=config.AUTO_ENTER,
        help="Press Enter after injecting text",
    )
    parser.add_argument(
        "--paste", action="store_true", default=config.PASTE_MODE,
        help="Use clipboard paste (Ctrl+Shift+V) instead of keystroke typing — much faster, ideal for Claude Code",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=config.VERBOSE,
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()

    # Apply CLI overrides to config
    config.MODEL_NAME = args.model
    config.DEVICE = args.device
    config.COMPUTE_TYPE = args.compute_type
    config.AUTO_ENTER = args.auto_enter
    config.PASTE_MODE = args.paste
    config.VERBOSE = args.verbose

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    app = TermiTalk()
    app.run()


if __name__ == "__main__":
    main()
