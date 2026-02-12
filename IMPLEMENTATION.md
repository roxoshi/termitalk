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
- [x] 4.1 Create `termitalk/transcriber.py` — load faster-whisper model (large-v3-turbo, int8)
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
- [x] 7.5 CLI argument parsing (--model, --device, --compute-type, --auto-enter, --paste, --verbose)

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

## Phase 10: Speed Optimization
- [x] 10.1 Switch default model to `large-v3-turbo` (fastest large-class model)
- [x] 10.2 Set `temperature=0.0` — single-pass decoding, eliminates up to 5 fallback retries
- [x] 10.3 Set `condition_on_previous_text=False` — skip prompt reuse overhead
- [x] 10.4 Set `cpu_threads=4` — explicit CTranslate2 parallelism
- [x] 10.5 beam_size=1 already set (greedy decoding)
- [x] 10.6 without_timestamps=True already set (skip timestamp token generation)
- [x] 10.7 16kHz native recording (no resampling) already set
- [x] 10.8 Silero VAD silence trimming (less audio sent to model) already set

## Phase 11: Claude Code Integration
- [x] 11.1 Add clipboard paste injection mode (`--paste` flag)
  - Copies text to clipboard via `xclip`/`xsel`
  - Simulates Ctrl+Shift+V (terminal paste) — instant for any text length
  - Saves and restores previous clipboard contents
  - Falls back to keystroke typing if no clipboard tool is available
- [x] 11.2 Add `--paste` CLI flag and `PASTE_MODE` config option
- [x] 11.3 Display injection mode in startup config summary

### Usage with Claude Code
```bash
# Start TermiTalk in paste mode for Claude Code
uv run termitalk --paste

# Or with auto-enter to submit immediately
uv run termitalk --paste --auto-enter
```

### Speed Comparison
| Method | 50 chars | 200 chars |
|---|---|---|
| Keystroke typing (8ms/char) | ~400ms | ~1600ms |
| Clipboard paste | ~70ms | ~70ms |

---

## Phase 12: Audio Feedback Cues
**Why:** When dictating into another window (Claude Code, vim, etc.) you can't see TermiTalk's terminal status. Audio cues are the only way to know recording started/stopped.
- [x] 12.1 Play a short sound on recording start (low tone "boop")
- [x] 12.2 Play a different sound on recording stop/processing complete (rising two-tone beep)
- [x] 12.3 Play an error sound on failure (descending tone)
- [x] 12.4 Generate tones programmatically with numpy (no bundled WAV files needed)
- [x] 12.5 Add `--no-sound` flag to disable audio cues
- [x] 12.6 Play "ready" chime at startup
- [x] 12.7 Non-blocking playback via background threads

## Phase 13: Custom Vocabulary & Corrections File
**Why:** Users need project-specific term mappings without editing source code.
- [x] 13.1 TOML format with `[phrases]`, `[symbols]`, and `[replacements]` sections
- [x] 13.2 Load corrections from `~/.config/termitalk/corrections.toml` at startup
- [x] 13.3 Merge user corrections into formatter's PHRASE_MAP and WORD_MAP
- [x] 13.4 Log loaded custom corrections count at startup
- [x] 13.5 Support `TERMITALK_CORRECTIONS` env var to override path

## Phase 14: Command History Log
**Why:** Lets users review past transcriptions, debug accuracy issues, and track what was dictated.
- [x] 14.1 Log each transcription to `~/.local/share/termitalk/history.log`
- [x] 14.2 Format: `[timestamp] (Nms) raw: "..." -> formatted` with processing time
- [x] 14.3 Add `--no-history` flag to disable logging
- [x] 14.4 Add `--history` flag to display recent entries and exit

## Phase 15: Configurable Hotkey via CLI
**Why:** Different keyboards/workflows need different hotkeys. Editing `config.py` is friction.
- [x] 15.1 Add `--hotkey` CLI flag: `--hotkey "ctrl+alt+space"`, `--hotkey "cmd+shift+r"`
- [x] 15.2 Parse human-readable key names (ctrl, shift, alt, cmd, super, f1-f12, etc.)
- [x] 15.3 Validate hotkey format with clear error on invalid input
- [x] 15.4 Support single character keys in combos (e.g., `ctrl+alt+r`)

## Phase 16: Wayland-Native Input Backend (planned)
**Why:** pynput relies on X11 — both the hotkey listener and keyboard injection fail on Wayland.
- [ ] 16.1 Add `evdev`-based global hotkey listener as Wayland fallback
- [ ] 16.2 Add `wtype` injection backend for Wayland keyboard injection
- [ ] 16.3 Add `ydotool` injection backend as fallback
- [ ] 16.4 Auto-detect display server and select backend at startup
- [ ] 16.5 Print clear setup instructions if permissions are missing

## Phase 17: Smart GPU Auto-Detection
**Why:** Users with NVIDIA GPUs get much faster inference with float16 but must manually set it.
- [x] 17.1 When `device=auto`, detect CUDA availability via `torch.cuda.is_available()`
- [x] 17.2 Auto-set `compute_type=float16` when CUDA is detected
- [x] 17.3 Log detected device and compute type upgrade at startup
