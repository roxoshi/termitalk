"""Startup dependency health checks with actionable install instructions."""

import os
import platform
import shutil
import sys

_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"

_OK = f"  {_GREEN}\u2713{_RESET} "
_FAIL = f"  {_RED}\u2717{_RESET} "
_WARN = f"  {_YELLOW}\u2717{_RESET} "

_system = platform.system()


def check_dependencies(paste_mode: bool = False) -> bool:
    """Check system prerequisites and print diagnostic lines.

    Returns True if all critical dependencies are satisfied.
    Paste-tool checks are warnings only (non-blocking).
    """
    ok = True

    # --- PortAudio ---
    ok &= _check_portaudio()

    # --- ffmpeg ---
    ok &= _check_ffmpeg()

    # --- Paste tools (warning only) ---
    if paste_mode:
        _check_paste_tools()

    print(file=sys.stderr)
    return ok


def _check_portaudio() -> bool:
    try:
        import sounddevice as sd
        sd.query_devices()
        print(f"{_OK}PortAudio found", file=sys.stderr)
        return True
    except OSError:
        if _system == "Darwin":
            hint = "brew install portaudio"
        elif shutil.which("pacman"):
            hint = "sudo pacman -S portaudio"
        else:
            hint = "sudo apt install libportaudio2"
        print(
            f"{_FAIL}PortAudio not found {_DIM}\u2014 install with: {_BOLD}{hint}{_RESET}",
            file=sys.stderr,
        )
        return False
    except ImportError:
        print(
            f"{_FAIL}sounddevice not installed {_DIM}\u2014 run: {_BOLD}uv sync{_RESET}",
            file=sys.stderr,
        )
        return False


def _check_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        print(f"{_OK}ffmpeg found", file=sys.stderr)
        return True
    if _system == "Darwin":
        hint = "brew install ffmpeg"
    elif shutil.which("pacman"):
        hint = "sudo pacman -S ffmpeg"
    else:
        hint = "sudo apt install ffmpeg"
    print(
        f"{_FAIL}ffmpeg not found {_DIM}\u2014 install with: {_BOLD}{hint}{_RESET}",
        file=sys.stderr,
    )
    return False


def _check_paste_tools():
    """Check for clipboard tools (warning only, not a blocker)."""
    if _system == "Darwin":
        # pbcopy is always available on macOS
        if shutil.which("pbcopy"):
            print(f"{_OK}pbcopy found", file=sys.stderr)
        else:
            print(f"{_WARN}pbcopy not found (unexpected on macOS)", file=sys.stderr)
        return

    # Linux — check based on session type
    found = False
    if _is_wayland():
        if shutil.which("wl-copy"):
            print(f"{_OK}wl-copy found (Wayland)", file=sys.stderr)
            found = True
        else:
            print(
                f"{_WARN}wl-clipboard not found {_DIM}\u2014 install with: "
                f"{_BOLD}sudo apt install wl-clipboard{_RESET}",
                file=sys.stderr,
            )
    else:
        if shutil.which("xclip"):
            print(f"{_OK}xclip found (X11)", file=sys.stderr)
            found = True
        elif shutil.which("xsel"):
            print(f"{_OK}xsel found (X11)", file=sys.stderr)
            found = True
        else:
            print(
                f"{_WARN}xclip not found {_DIM}\u2014 install with: "
                f"{_BOLD}sudo apt install xclip{_RESET}",
                file=sys.stderr,
            )

    if not found and not _is_wayland():
        pass  # warning already printed


def _is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))
