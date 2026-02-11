"""Configuration constants for TermiTalk."""

# --- Hotkey ---
# Push-to-talk key combination — stored as string tuples, resolved at runtime.
# Format: pynput.keyboard.Key attribute names
HOTKEY_KEYS_SPEC = ("ctrl_l", "shift", "space")


def get_hotkey_keys():
    """Resolve hotkey key spec to actual pynput Key objects (requires display)."""
    from pynput.keyboard import Key
    return {getattr(Key, name) for name in HOTKEY_KEYS_SPEC}


# --- Whisper Model ---
MODEL_NAME = "large-v3-turbo"  # Fastest large model; alternatives: distil-large-v3, tiny.en, base.en
DEVICE = "auto"  # "auto", "cpu", or "cuda"
COMPUTE_TYPE = "int8"  # "int8" for CPU, "float16" for GPU
BEAM_SIZE = 1  # 1 = fastest, 5 = most accurate
LANGUAGE = "en"
TEMPERATURE = 0.0  # Single pass, no fallback — avoids up to 5 retry passes
CONDITION_ON_PREVIOUS_TEXT = False  # Skip prompt reuse — faster for short commands
CPU_THREADS = 4  # CTranslate2 intra-op threads (0 = auto)

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
