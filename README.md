# Local Terminal STT

## Project Overview

A 100% local, privacy-focused speech-to-text tool designed for terminal users. This tool allows you to dictate bash commands and programming logic directly into your command line (or Claude Code) using a global Push-to-Talk hotkey.

## Core Features

* **Zero Latency:** Optimized for near-instant transcription.
* **Technical Focus:** Specialized formatting for CLI symbols (pipes, dashes, slashes).
* **Privacy First:** All processing happens on-device; no data leaves the machine.
* **Universal Injection:** Works across any terminal emulator by simulating keyboard input.

---

## Technical Stack

* **Inference:** `faster-whisper` (Model: `distil-large-v3`)
* **VAD:** `silero-vad` (for silence removal)
* **Logic:** Python 3.10+
* **System Hooks:** `pynput` for hotkeys and keyboard simulation

## Installation

### 1. System Requirements

* Python 3.10 or higher
* `ffmpeg` (Required for audio processing)
```bash
# macOS
brew install ffmpeg
# Ubuntu
sudo apt install ffmpeg

```



### 2. Setup Environment

```bash
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install faster-whisper pynput sounddevice silero-vad numpy

```

---

## Usage instructions

1. **Launch the Daemon:**
```bash
python main.py

```


2. **Trigger Transcription:**
* Hold `Ctrl + Shift + Space`.
* Speak your command (e.g., "git commit dash m added new feature").
* Release the keys.


3. **Result:** The tool will transcribe and "type" `git commit -m "added new feature"` into your active terminal.

---

## Configuration & Customization

* **Hotkeys:** Can be adjusted in `config.py`.
* **Technical Mappings:** Add custom shorthand to `formatter.py` to map specific phrases to complex commands.
* **Model Size:** Switch between `tiny`, `base`, or `distil-large-v3` depending on your hardware capabilities.

## Troubleshooting

* **Permission Denied:** Ensure the terminal/IDE has "Accessibility" or "Input Monitoring" permissions (required for `pynput` on macOS/Windows).
* **Audio Input:** Verify the correct microphone index is selected in `sounddevice`.

---
