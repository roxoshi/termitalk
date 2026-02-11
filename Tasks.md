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


### Phase 5: Max Optimization
To ensure the transcription feels "instant" (sub-200ms), implement the following optimizations:

1. Memory & Inference Optimization

Model Quantization: Always use compute_type="int8" on CPU or float16 on GPU. This reduces the model size by ~4x and speeds up math operations significantly with almost zero loss in command-level accuracy.

Pre-warming: Load the WhisperModel once at startup and run a "dummy" transcription of 1 second of silence. This ensures the model weights are moved to the cache and the execution graph is initialized before you actually start talking.

Beam Size: Set beam_size=1 for the fastest results. While higher beam sizes (like 5) are better for complex prose, 1 is perfectly sufficient for short, clear bash commands and improves speed by 2-3x.

2. Audio Handling (The "VAD" Trick)

Trim the Fat: Do not send silence to the Whisper model. Use Silero VAD to cut the audio buffer at the exact millisecond speech stops. Sending even 1 second of extra silence can double the processing time.

Sampling Rate: Record at exactly 16kHz. Whisper models are native to 16kHz; recording at 44.1kHz or 48kHz forces the CPU to waste cycles downsampling the audio before processing.

3. Concurrency & System Logic

Threading: Use a dedicated thread for the pynput listener. Heavy processing (like transcription) should happen in a separate Process or Thread so the hotkey listener doesn't "lag" or drop keystroke events.

Keystroke Delay: When using keyboard.type(), set a very small interval (e.g., 0.01s) or no interval at all. Some terminals struggle if 50 characters are "injected" at the exact same microsecond.

Process Priority: On Linux/macOS, consider setting the process niceness or priority higher so that even if the CPU is busy compiling code, the STT tool gets first dibs on the processor when the hotkey is pressed.
