# TermiTalk

A 100% local, privacy-focused speech-to-text tool for the terminal. Dictate bash commands and code directly into any terminal emulator using a global push-to-talk hotkey. All processing happens on-device — no data leaves your machine.

## Features

- **Fast** — Turbo model + single-pass decoding for sub-500ms transcription
- **CLI-aware** — Automatically converts spoken words to symbols ("dash" → `-`, "pipe" → `|`, "slash" → `/`)
- **Private** — Runs entirely offline using local Whisper models
- **Universal** — Works with any terminal emulator, IDE, or text field
- **Paste mode** — Clipboard-based injection for instant text delivery (ideal for Claude Code)

## Installation

### System Dependencies

- Python 3.10+
- `ffmpeg` and `libportaudio2`
- Paste mode clipboard tools (optional):
  - **macOS**: `pbcopy`/`pbpaste` (built-in, nothing to install)
  - **Linux/Wayland**: `wl-clipboard` (`sudo apt install wl-clipboard`)
  - **Linux/X11**: `xclip` (`sudo apt install xclip`)

```bash
# Ubuntu/Debian
sudo apt install ffmpeg libportaudio2 wl-clipboard

# macOS
brew install ffmpeg portaudio

# Arch
sudo pacman -S ffmpeg portaudio wl-clipboard
```

### Install TermiTalk

```bash
# Clone and install with uv
git clone https://github.com/yourusername/termitalk.git
cd termitalk
uv sync

# Or install directly
uv pip install .
```

The first run will download the Whisper model (~1.5 GB).

## Usage

### Start the daemon

```bash
uv run termitalk
```

### Push-to-Talk

1. Hold **Ctrl + Shift + Space**
2. Speak your command (e.g., *"git commit dash m fixed the login bug"*)
3. Release the keys

The tool transcribes your speech, converts spoken symbols, and types the result into your active window:

```
git commit -m fixed the login bug
```

### Using with Claude Code

For the best experience with Claude Code, use paste mode:

```bash
# Paste mode — instant text injection via clipboard
uv run termitalk --paste

# With auto-enter to submit your message immediately
uv run termitalk --paste --auto-enter
```

Paste mode uses the clipboard (`Ctrl+Shift+V`) instead of typing character-by-character, making injection instant regardless of text length. Your previous clipboard contents are automatically saved and restored.

### CLI Options

```
termitalk [OPTIONS]

  --model NAME        Whisper model (default: large-v3-turbo)
  --device DEVICE     cpu, cuda, or auto (default: auto)
  --compute-type TYPE int8, float16, float32 (default: int8)
  --paste             Use clipboard paste instead of keystroke typing
  --auto-enter        Press Enter after injecting text
  -v, --verbose       Enable debug logging
```

### Spoken Symbol Reference

| You say | You get | | You say | You get |
|---|---|---|---|---|
| "dash" | `-` | | "pipe" | `\|` |
| "double dash" | `--` | | "slash" | `/` |
| "dot" | `.` | | "backslash" | `\` |
| "tilde" | `~` | | "at" | `@` |
| "dollar" | `$` | | "hash" | `#` |
| "star" | `*` | | "underscore" | `_` |
| "equals" | `=` | | "colon" | `:` |
| "plus" | `+` | | "bang" | `!` |
| "open paren" | `(` | | "close paren" | `)` |
| "open bracket" | `[` | | "close bracket" | `]` |
| "dot slash" | `./` | | "dot dot slash" | `../` |

Filler words ("um", "uh", "like") are automatically removed.

## Configuration

Edit `termitalk/config.py` to customize:

- **Hotkey** — Change the push-to-talk key combination
- **Model** — Switch between `tiny.en`, `base.en`, `large-v3-turbo`, `distil-large-v3`, etc.
- **Symbol mappings** — Add custom spoken-to-symbol rules in `termitalk/formatter.py`
- **Keystroke delay** — Adjust injection speed for your terminal
- **Paste mode** — Default to clipboard paste for faster injection

## Speed Optimizations

TermiTalk is tuned for minimal latency:

| Optimization | Effect |
|---|---|
| `large-v3-turbo` model | Fastest large-class Whisper model |
| `temperature=0.0` | Single-pass decoding, no fallback retries |
| `beam_size=1` | Greedy decoding (2-3x faster than beam=5) |
| `condition_on_previous_text=False` | Skip prompt reuse overhead |
| `int8` quantization | ~4x smaller, faster inference on CPU |
| Silero VAD trimming | Only transcribe actual speech, not silence |
| 16kHz native recording | No resampling overhead |
| Model pre-warming | Eliminates cold-start latency |
| Paste mode (`--paste`) | ~70ms injection vs 8ms/char keystroke |

## Technical Stack

| Component | Library |
|---|---|
| Speech recognition | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3-turbo) |
| Voice activity detection | [silero-vad](https://github.com/snakers4/silero-vad) |
| Audio capture | [sounddevice](https://python-sounddevice.readthedocs.io/) (16kHz, mono) |
| Keyboard hooks | [pynput](https://pynput.readthedocs.io/) |
| Quantization | int8 (CPU) / float16 (GPU) via CTranslate2 |

## Troubleshooting

- **"PortAudio library not found"** — Install `libportaudio2` (Ubuntu) or `portaudio` (macOS)
- **"this platform is not supported"** — Ensure you have an X11/Wayland display (pynput requires it)
- **Permission denied** — On macOS, grant Accessibility permissions to your terminal app
- **Wrong microphone** — Check `python -m sounddevice` to list audio devices
- **Paste not working** — macOS uses `pbcopy`/`pbpaste` (built-in). Linux/Wayland needs `wl-clipboard` (`wl-copy`). Linux/X11 needs `xclip` or `xsel`. Falls back to keystroke mode if none found

## License

MIT
