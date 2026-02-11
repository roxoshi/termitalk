# TermiTalk

A 100% local, privacy-focused speech-to-text tool for the terminal. Dictate bash commands and code directly into any terminal emulator using a global push-to-talk hotkey. All processing happens on-device — no data leaves your machine.

## Features

- **Fast** — Optimized for sub-500ms transcription of short commands
- **CLI-aware** — Automatically converts spoken words to symbols ("dash" → `-`, "pipe" → `|`, "slash" → `/`)
- **Private** — Runs entirely offline using local Whisper models
- **Universal** — Works with any terminal emulator, IDE, or text field via simulated keyboard input

## Installation

### System Dependencies

- Python 3.10+
- `ffmpeg` and `libportaudio2`

```bash
# Ubuntu/Debian
sudo apt install ffmpeg libportaudio2

# macOS
brew install ffmpeg portaudio

# Arch
sudo pacman -S ffmpeg portaudio
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

### CLI Options

```
termitalk [OPTIONS]

  --model NAME        Whisper model (default: distil-large-v3)
  --device DEVICE     cpu, cuda, or auto (default: auto)
  --compute-type TYPE int8, float16, float32 (default: int8)
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
- **Model** — Switch between `tiny`, `base`, `distil-large-v3`, etc.
- **Symbol mappings** — Add custom spoken-to-symbol rules in `termitalk/formatter.py`
- **Keystroke delay** — Adjust injection speed for your terminal

## Technical Stack

| Component | Library |
|---|---|
| Speech recognition | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (distil-large-v3) |
| Voice activity detection | [silero-vad](https://github.com/snakers4/silero-vad) |
| Audio capture | [sounddevice](https://python-sounddevice.readthedocs.io/) (16kHz, mono) |
| Keyboard hooks | [pynput](https://pynput.readthedocs.io/) |
| Quantization | int8 (CPU) / float16 (GPU) via CTranslate2 |

## Troubleshooting

- **"PortAudio library not found"** — Install `libportaudio2` (Ubuntu) or `portaudio` (macOS)
- **"this platform is not supported"** — Ensure you have an X11/Wayland display (pynput requires it)
- **Permission denied** — On macOS, grant Accessibility permissions to your terminal app
- **Wrong microphone** — Check `python -m sounddevice` to list audio devices

## License

MIT
