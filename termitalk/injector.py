"""Keyboard injection: types or pastes transcribed text into the active window."""

import logging
import os
import platform
import subprocess
import time

from pynput.keyboard import Controller, Key

from termitalk import config

logger = logging.getLogger(__name__)

_keyboard = Controller()
_platform = platform.system()  # "Darwin", "Linux", "Windows"


def inject_text(text: str):
    """Inject text into the currently focused window.

    Uses paste mode (clipboard) when config.PASTE_MODE is True,
    otherwise falls back to simulated keystroke typing.
    """
    if not text:
        return

    if config.PASTE_MODE:
        _paste_text(text)
    else:
        _type_text(text)

    if config.AUTO_ENTER:
        time.sleep(0.05)
        _keyboard.press(Key.enter)
        _keyboard.release(Key.enter)
        logger.debug("Auto-enter sent")


def _paste_text(text: str):
    """Inject text via clipboard paste — near-instant regardless of text length.

    Detects the platform and uses the appropriate clipboard tool and paste shortcut:
      - macOS:         pbcopy/pbpaste + Cmd+V
      - Linux/Wayland: wl-copy/wl-paste + Ctrl+Shift+V
      - Linux/X11:     xclip/xsel + Ctrl+Shift+V
    """
    logger.debug("Paste-injecting %d characters", len(text))

    # Save current clipboard
    old_clipboard = _get_clipboard()

    # Set clipboard to our text
    if not _set_clipboard(text):
        logger.warning("Clipboard write failed, falling back to keystroke typing")
        _type_text(text)
        return

    # Small delay to ensure clipboard is set
    time.sleep(0.02)

    # Paste with platform-appropriate shortcut
    if _platform == "Darwin":
        # macOS: Cmd+V
        _keyboard.press(Key.cmd)
        _keyboard.press("v")
        _keyboard.release("v")
        _keyboard.release(Key.cmd)
    else:
        # Linux terminals: Ctrl+Shift+V
        _keyboard.press(Key.ctrl_l)
        _keyboard.press(Key.shift)
        _keyboard.press("v")
        _keyboard.release("v")
        _keyboard.release(Key.shift)
        _keyboard.release(Key.ctrl_l)

    # Small delay then restore old clipboard
    time.sleep(0.05)
    if old_clipboard is not None:
        _set_clipboard(old_clipboard)


def _type_text(text: str):
    """Inject text via simulated keystrokes — character by character."""
    logger.debug("Type-injecting %d characters: %r", len(text), text[:80])

    for char in text:
        if char == "\n":
            _keyboard.press(Key.enter)
            _keyboard.release(Key.enter)
        elif char == "\t":
            _keyboard.press(Key.tab)
            _keyboard.release(Key.tab)
        else:
            _keyboard.type(char)

        if config.KEYSTROKE_DELAY > 0:
            time.sleep(config.KEYSTROKE_DELAY)


# ---------------------------------------------------------------------------
# Platform-aware clipboard helpers
# ---------------------------------------------------------------------------

def _get_clipboard() -> str | None:
    """Read current clipboard contents. Returns None on failure."""
    for cmd in _clipboard_read_commands():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _set_clipboard(text: str) -> bool:
    """Write text to the clipboard. Returns True on success."""
    for cmd in _clipboard_write_commands():
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(input=text.encode(), timeout=2)
            if proc.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    logger.warning("No working clipboard tool found")
    return False


def _clipboard_read_commands() -> list[list[str]]:
    """Return ordered list of clipboard read commands for the current platform."""
    if _platform == "Darwin":
        return [["pbpaste"]]
    # Linux — try Wayland first, then X11
    cmds = []
    if _is_wayland():
        cmds.append(["wl-paste", "--no-newline"])
    cmds.append(["xclip", "-selection", "clipboard", "-o"])
    cmds.append(["xsel", "--clipboard", "--output"])
    return cmds


def _clipboard_write_commands() -> list[list[str]]:
    """Return ordered list of clipboard write commands for the current platform."""
    if _platform == "Darwin":
        return [["pbcopy"]]
    # Linux — try Wayland first, then X11
    cmds = []
    if _is_wayland():
        cmds.append(["wl-copy"])
    cmds.append(["xclip", "-selection", "clipboard"])
    cmds.append(["xsel", "--clipboard", "--input"])
    return cmds


def _is_wayland() -> bool:
    """Check if running under a Wayland session."""
    return bool(os.environ.get("WAYLAND_DISPLAY"))
