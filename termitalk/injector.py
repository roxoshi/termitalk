"""Keyboard injection: types or pastes transcribed text into the active window."""

import logging
import subprocess
import time

from pynput.keyboard import Controller, Key

from termitalk import config

logger = logging.getLogger(__name__)

_keyboard = Controller()


def inject_text(text: str):
    """Inject text into the currently focused window.

    Uses paste mode (clipboard + Ctrl+Shift+V) when config.PASTE_MODE is True,
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

    Saves and restores the previous clipboard contents.
    """
    logger.debug("Paste-injecting %d characters", len(text))

    # Save current clipboard
    old_clipboard = _get_clipboard()

    # Set clipboard to our text
    _set_clipboard(text)

    # Small delay to ensure clipboard is set
    time.sleep(0.02)

    # Paste: Ctrl+Shift+V (terminal-standard paste that strips formatting)
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


def _get_clipboard() -> str | None:
    """Read current clipboard contents. Returns None on failure."""
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True, timeout=2,
        )
        return result.stdout if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        try:
            result = subprocess.run(
                ["xsel", "--clipboard", "--output"],
                capture_output=True, text=True, timeout=2,
            )
            return result.stdout if result.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None


def _set_clipboard(text: str):
    """Write text to the clipboard."""
    try:
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=text.encode(), timeout=2)
        return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.Popen(
            ["xsel", "--clipboard", "--input"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=text.encode(), timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("No clipboard tool found (install xclip or xsel). Falling back to type mode.")
        _type_text(text)
