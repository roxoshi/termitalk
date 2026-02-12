"""Configuration constants for TermiTalk."""

# --- Hotkey ---
# Push-to-talk key combination — stored as string tuples, resolved at runtime.
# Format: pynput.keyboard.Key attribute names
HOTKEY_KEYS_SPEC = ("ctrl_l", "shift", "space")


def get_hotkey_keys():
    """Resolve hotkey key spec to actual pynput Key objects (requires display)."""
    from pynput.keyboard import Key, KeyCode
    keys = set()
    for name in HOTKEY_KEYS_SPEC:
        if hasattr(Key, name):
            keys.add(getattr(Key, name))
        elif len(name) == 1:
            keys.add(KeyCode.from_char(name))
        else:
            raise ValueError(f"Cannot resolve key: {name!r}")
    return keys


# Map human-readable key names to pynput Key attribute names
_KEY_ALIASES = {
    "ctrl": "ctrl_l", "control": "ctrl_l", "ctrl_l": "ctrl_l", "ctrl_r": "ctrl_r",
    "shift": "shift", "shift_l": "shift", "shift_r": "shift_r",
    "alt": "alt_l", "option": "alt_l", "alt_l": "alt_l", "alt_r": "alt_r",
    "cmd": "cmd", "command": "cmd", "super": "cmd", "meta": "cmd", "cmd_l": "cmd_l", "cmd_r": "cmd_r",
    "space": "space", "enter": "enter", "return": "enter",
    "tab": "tab", "esc": "esc", "escape": "esc",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5", "f6": "f6",
    "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
}


def parse_hotkey(hotkey_str: str) -> tuple[str, ...]:
    """Parse a human-readable hotkey string into a HOTKEY_KEYS_SPEC tuple.

    Examples:
        "ctrl+shift+space" → ("ctrl_l", "shift", "space")
        "cmd+alt+r" → ("cmd", "alt_l", "r")

    Raises ValueError for unrecognized key names.
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    result = []
    for part in parts:
        if part in _KEY_ALIASES:
            result.append(_KEY_ALIASES[part])
        elif len(part) == 1 and part.isalnum():
            result.append(part)  # Single character key
        else:
            valid = ", ".join(sorted(set(_KEY_ALIASES.keys())))
            raise ValueError(
                f"Unknown key: {part!r}. Valid modifier/special keys: {valid}"
            )
    return tuple(result)


# --- Whisper Model ---
MODEL_NAME = "large-v3-turbo"  # Fastest large model; alternatives: distil-large-v3, tiny.en, base.en
DEVICE = "auto"  # "auto", "cpu", or "cuda"
COMPUTE_TYPE = "int8"  # "int8" for CPU, "float16" for GPU
BEAM_SIZE = 1  # 1 = fastest, 5 = most accurate
LANGUAGE = "en"
TEMPERATURE = 0.0  # Single pass, no fallback — avoids up to 5 retry passes
CONDITION_ON_PREVIOUS_TEXT = False  # Skip prompt reuse — faster for short commands
CPU_THREADS = 0  # CTranslate2 intra-op threads (0 = auto/all cores)

# Initial prompt to bias Whisper toward CLI/programming vocabulary
INITIAL_PROMPT = (
    "ls cd git commit push pull sudo apt pip npm docker kubectl "
    "grep sed awk cat echo chmod chown mkdir rm -rf --help -la "
    "python node bash zsh ssh scp curl wget tar zip unzip "
    "| > >> < && || ; $ ~ / ./ ../ "
)

# --- Audio ---
SAMPLE_RATE = 16000  # Hz — Whisper's native rate, no resampling needed
CHANNELS = 1  # Mono
DTYPE = "float32"  # Audio sample format for sounddevice

# --- VAD ---
VAD_THRESHOLD = 0.5  # Silero VAD speech probability threshold
VAD_MIN_SPEECH_MS = 250  # Minimum speech duration to keep (ms)
VAD_MIN_SILENCE_MS = 100  # Minimum silence to mark end of speech (ms)
VAD_WINDOW_SIZE_MS = 30  # VAD analysis window size (ms) — must be 30, 60, or 100

# --- Keyboard Injection ---
KEYSTROKE_DELAY = 0.008  # Seconds between simulated keystrokes
AUTO_ENTER = False  # If True, press Enter after injecting text
PASTE_MODE = False  # If True, use clipboard paste (Ctrl+Shift+V) instead of keystroke typing

# --- UX ---
VERBOSE = False
SOUND_ENABLED = True  # Play audio cues on record start/stop/error
HISTORY_ENABLED = True  # Log transcriptions to ~/.local/share/termitalk/history.log
