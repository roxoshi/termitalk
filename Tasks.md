# Implementation Plan: Local Terminal STT

### Phase 1: Environment & Audio Capture

1. **Dependency Setup**: Install `ffmpeg`, `faster-whisper`, `pynput`, `sounddevice`, and `silero-vad` in a dedicated Python virtual environment.
2. **Microphone Stream**: Create a script using `sounddevice` to capture raw audio from the default system mic and store it in a NumPy array buffer.
3. **VAD Integration**: Implement `Silero VAD` to monitor the audio stream and identify the exact timestamps where speech begins and ends.

### Phase 2: Inference Engine

4. **Model Loading**: Initialize `Faster-Whisper` using the `distil-large-v3` model with `int8` quantization to ensure low memory usage and fast CPU/GPU inference.
5. **Basic Transcription**: Build a function that passes the VAD-trimmed audio buffer to the model and returns a raw string of text.
6. **Technical Prompting**: Implement "Initial Prompting" in the transcription call to bias the model toward recognizing CLI terms like `sudo`, `ls`, `grep`, and `git`.

### Phase 3: System Integration

7. **Global Hotkey Listener**: Use `pynput.keyboard.Listener` to create a "Push-to-Talk" trigger (e.g., `Ctrl+Shift+Space`) that works regardless of which window is focused.
8. **Text Sanitizer**: Create a simple mapping utility to convert spoken phrases (e.g., "dot slash", "dash help", "pipe") into their character equivalents (`./`, `--help`, `|`).
9. **Keyboard Injection**: Use `pynput.keyboard.Controller` to simulate keystrokes, "typing" the final sanitized string into the active terminal cursor.

### Phase 4: Optimization

10. **Warm-up & Daemon**: Wrap the logic into a background process (daemon) so the model stays loaded in VRAM/RAM, preventing a "cold start" delay for every command.
11. **Final Polish**: Add a small CLI flag to toggle between "Auto-Enter" (executes command immediately) and "Type-Only" (allows review before hitting enter).
