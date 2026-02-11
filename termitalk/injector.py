"""Keyboard injection: types transcribed text into the active window."""

import logging
import time

from pynput.keyboard import Controller, Key

from termitalk import config

logger = logging.getLogger(__name__)

_keyboard = Controller()


def inject_text(text: str):
    """Type text into the currently focused window using simulated keystrokes.

    Args:
        text: The text to inject.
    """
    if not text:
        return

    logger.debug("Injecting %d characters: %r", len(text), text[:80])

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

    if config.AUTO_ENTER:
        time.sleep(config.KEYSTROKE_DELAY)
        _keyboard.press(Key.enter)
        _keyboard.release(Key.enter)
        logger.debug("Auto-enter sent")
