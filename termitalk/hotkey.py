"""Global push-to-talk hotkey listener."""

import logging
import threading
from typing import Callable

from pynput.keyboard import Key, Listener

from termitalk import config

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Listens for a global key combination and triggers callbacks on press/release.

    The hotkey is "hold to talk" — all keys in the combo must be held simultaneously
    to activate recording. Releasing any key in the combo stops recording.
    """

    def __init__(self, on_activate: Callable[[], None], on_deactivate: Callable[[], None]):
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._pressed: set = set()
        self._active = False
        self._listener: Listener | None = None
        self._hotkey_keys = config.get_hotkey_keys()

    def start(self):
        """Start the global hotkey listener in a background thread."""
        self._listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        hotkey_names = " + ".join(_key_name(k) for k in self._hotkey_keys)
        logger.info("Hotkey listener started — hold [%s] to talk", hotkey_names)

    def stop(self):
        """Stop the listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key):
        key = _normalize_key(key)
        self._pressed.add(key)

        if not self._active and self._hotkey_keys.issubset(self._pressed):
            self._active = True
            logger.debug("Hotkey activated")
            threading.Thread(target=self._on_activate, daemon=True).start()

    def _on_release(self, key):
        key = _normalize_key(key)
        self._pressed.discard(key)

        if self._active and not self._hotkey_keys.issubset(self._pressed):
            self._active = False
            logger.debug("Hotkey deactivated")
            threading.Thread(target=self._on_deactivate, daemon=True).start()


def _normalize_key(key) -> Key | str:
    """Normalize key to match config format."""
    mapping = {
        Key.ctrl_r: Key.ctrl_l,
        Key.shift_r: Key.shift,
        Key.alt_r: Key.alt_l,
    }
    if hasattr(key, "value"):
        return mapping.get(key, key)
    return key


def _key_name(key) -> str:
    """Human-readable name for a key."""
    names = {
        Key.ctrl_l: "Ctrl",
        Key.ctrl_r: "Ctrl",
        Key.shift: "Shift",
        Key.shift_r: "Shift",
        Key.alt_l: "Alt",
        Key.alt_r: "Alt",
        Key.space: "Space",
        Key.enter: "Enter",
    }
    if key in names:
        return names[key]
    if hasattr(key, "char"):
        return key.char.upper() if key.char else str(key)
    return str(key).replace("Key.", "").capitalize()
