# termitalk 
Building a local, open-source speech-to-text (STT) tool for the terminal. This setup eliminates the friction of typing long bash commands or repetitive boilerplate code while keeping your data entirely private.

The following design document outlines a 100% local architecture using the **Whisper** ecosystem, specifically optimized for the high-speed and technical vocabulary requirements of programming.

---

## Design Document: "TermiTalk" (Local Terminal STT)

### 1. Project Overview

**Objective:** Create a lightweight CLI tool that captures audio, transcribes it locally using an open-source model, and injects the text directly into the terminal prompt.
**Core Requirements:**

* **Latency:** Transcription must be near-instant (<500ms for short phrases).
* **Accuracy:** Must handle technical jargon (e.g., "ls -la", "grep", "repo", "refactor").
* **Locality:** No cloud APIs. Fully offline.

### 2. The Tech Stack

To meet the "Open Source" and "100% Local" requirements, we will use the following:

* **Inference Engine:** `Faster-Whisper` or `whisper.cpp`. (Faster-Whisper is recommended for Python integration; `whisper.cpp` for raw C++ performance on Mac M1/M2/M3 chips).
* **Model:** `distil-whisper/distil-large-v3` or `whisper-turbo`. These models are trained specifically to be fast while maintaining high accuracy for English.
* **Audio Capture:** `PyAudio` or `sounddevice` (Python) to interface with the system microphone.
* **Glue Logic:** A Python wrapper to handle the "Push-to-Talk" logic and terminal injection.

### 3. System Architecture

The tool operates in a "Listen-Process-Type" loop.

#### Key Components:

1. **VAD (Voice Activity Detection):** Using `Silero VAD` (open-source) to detect when you start and stop speaking. This prevents the model from trying to transcribe background noise.
2. **Transcription Engine:** Faster-Whisper running in `int8` quantization to minimize CPU/GPU load.
3. **The "Injection" Layer:** Since you want this to work *inside* other tools (like Claude Code), we use a virtual keyboard library (`pynput` or `xdotool`) to "type" the result into the active terminal window.

---

### 4. Implementation Steps

#### Step 1: Environment Setup

You will need Python 3.10+ and `ffmpeg` installed on your system.

```bash
# Install system dependencies (Example for macOS)
brew install ffmpeg

# Install Python libraries
pip install faster-whisper pynput sounddevice numpy silero-vad

```

#### Step 2: The Logic (MVP Script)

Below is a conceptual breakdown of the script you will write:

```python
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput.keyboard import Controller

# Initialize model (Local)
# Use 'distil-large-v3' for the best speed-to-accuracy ratio
model = WhisperModel("distil-large-v3", device="cpu", compute_type="int8")
keyboard = Controller()

def transcribe_and_type(audio_data):
    segments, _ = model.transcribe(audio_data, beam_size=5)
    text = "".join([segment.text for segment in segments]).strip()
    
    # Simple post-processing for bash commands
    text = text.lower().replace("dash ", "-")
    
    # Inject into terminal
    keyboard.type(text)

# Logic to trigger recording on a Hotkey (e.g., Command + Shift + R)

```

#### Step 3: Improving Code/Bash Accuracy

General-purpose models often struggle with symbols. You can improve this by:

* **Prompting:** Whisper supports a "initial prompt." You can set this to: `"ls, cd, git commit, python, node, bash, sudo, -la, --help"` to bias the model toward technical terms.
* **Normalization:** A simple Python dictionary to swap words like "hyphen" or "dash" with `-`.

---

### 5. Performance Targets

| Feature | Target | Implementation |
| --- | --- | --- |
| **Model Loading** | < 2s | Pre-load model as a background daemon |
| **Inference Time** | < 0.2s | Use `int8` quantization + Distil-Whisper |
| **Accuracy (Code)** | ~95% | Use technical "initial prompts" |
| **Privacy** | 100% | No network calls; `localhost` only |

---

### 6. Challenges & Solutions

* **The "Terminal Focus" Problem:** If the script is running in one window, how does it type into your Claude Code window?
* *Solution:* Use a global hotkey listener. When the hotkey is pressed, the script records; when released, it uses `pynput` to simulate keyboard events into whatever window currently has focus.


* **Latency on CPU:** On older hardware, even `distil-whisper` might take 1-2 seconds.
* *Solution:* Use `whisper.cpp` with CoreML (on Mac) or OpenVINO (on Intel) for hardware acceleration.
