"""Command history — logs all transcriptions for review and debugging."""

import logging
import os
from datetime import datetime
from pathlib import Path

from termitalk import config

logger = logging.getLogger(__name__)

_HISTORY_DIR = Path(os.environ.get(
    "TERMITALK_HISTORY_DIR",
    Path.home() / ".local" / "share" / "termitalk",
))
_HISTORY_FILE = _HISTORY_DIR / "history.log"


def log_transcription(raw: str, formatted: str, elapsed_ms: float = 0):
    """Append a transcription entry to the history log.

    Does nothing if config.HISTORY_ENABLED is False.
    """
    if not config.HISTORY_ENABLED:
        return

    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_HISTORY_FILE, "a") as f:
            if raw == formatted:
                f.write(f"[{timestamp}] ({elapsed_ms:.0f}ms) {formatted}\n")
            else:
                f.write(f"[{timestamp}] ({elapsed_ms:.0f}ms) raw: {raw!r} -> {formatted}\n")
    except Exception as e:
        logger.debug("Failed to write history: %s", e)


def show_history(n: int = 20):
    """Print the last N history entries to stdout."""
    if not _HISTORY_FILE.exists():
        print("No history yet.")
        return

    lines = _HISTORY_FILE.read_text().splitlines()
    for line in lines[-n:]:
        print(line)
