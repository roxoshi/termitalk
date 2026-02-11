# TermiTalk — Implementation Task List

## Phase 1: Project Scaffolding
- [x] 1.1 Initialize `uv` project with `pyproject.toml`
- [x] 1.2 Add all dependencies (faster-whisper, pynput, sounddevice, silero-vad, numpy)
- [x] 1.3 Create project directory structure (`termitalk/` package)
- [x] 1.4 Create `.gitignore` for Python/venv/model artifacts

## Phase 2: Configuration
- [x] 2.1 Create `termitalk/config.py` — hotkey, model name, compute type, beam size, sample rate, VAD thresholds, keystroke delay, auto-enter toggle

## Phase 3: Audio Capture
- [x] 3.1 Create `termitalk/audio.py` — microphone stream capture using `sounddevice` at 16kHz mono
- [x] 3.2 Implement numpy array accumulator for audio data
- [x] 3.3 Integrate Silero VAD to trim silence from start/end of captured audio

## Phase 4: Transcription Engine
- [x] 4.1 Create `termitalk/transcriber.py` — load faster-whisper model (distil-large-v3, int8)
- [x] 4.2 Implement warm-up: run dummy transcription at startup to prime model
- [x] 4.3 Implement `transcribe(audio_buffer) -> str` with beam_size=1, initial prompt biasing for CLI terms
- [x] 4.4 Handle edge cases: empty audio, very short audio, no speech detected

## Phase 5: Text Formatting / Sanitizer
- [x] 5.1 Create `termitalk/formatter.py` — spoken-to-symbol mapping with join-behavior system
- [x] 5.2 Implement context-aware join logic (prefix/infix/keep behaviors)
- [x] 5.3 Strip filler words ("um", "uh", "like") from output

## Phase 6: Keyboard Injection
- [x] 6.1 Create `termitalk/injector.py` — pynput keyboard controller
- [x] 6.2 Configurable keystroke delay (default ~0.008s)
- [x] 6.3 Optional auto-enter (simulate Enter key after injection)

## Phase 7: Hotkey Listener & Main Loop
- [x] 7.1 Create `termitalk/hotkey.py` — global push-to-talk listener using `pynput`
- [x] 7.2 Hold-to-record: start on key combo press, stop on release
- [x] 7.3 Hotkey listener in dedicated thread, transcription in separate thread
- [x] 7.4 Create `termitalk/main.py` — daemon entry point
- [x] 7.5 CLI argument parsing (--model, --device, --compute-type, --auto-enter, --verbose)

## Phase 8: Polish & UX
- [x] 8.1 Terminal UI feedback: recording indicator, transcription status, result preview
- [x] 8.2 Config summary display at startup
- [x] 8.3 Logging with --verbose flag
- [x] 8.4 Graceful shutdown on SIGINT/SIGTERM

## Phase 9: Packaging & Distribution
- [x] 9.1 Configure `pyproject.toml` entry point, metadata, classifiers
- [x] 9.2 Write README.md with install instructions (uv-based), usage, config reference
- [x] 9.3 Add MIT LICENSE file
- [ ] 9.4 Test full end-to-end flow (requires display + microphone)
