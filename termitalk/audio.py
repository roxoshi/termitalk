"""Audio capture and VAD-based silence trimming."""

import logging
import threading

import numpy as np
import sounddevice as sd
import torch
from silero_vad import get_speech_timestamps, load_silero_vad, collect_chunks

from termitalk import config

logger = logging.getLogger(__name__)

_vad_model = None
_vad_lock = threading.Lock()


def _get_vad_model():
    """Load Silero VAD model (singleton, thread-safe)."""
    global _vad_model
    if _vad_model is None:
        with _vad_lock:
            if _vad_model is None:
                logger.info("Loading Silero VAD model...")
                _vad_model = load_silero_vad(onnx=True)
    return _vad_model


class Recorder:
    """Push-to-talk audio recorder using sounddevice."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def start(self):
        """Start capturing audio from the default microphone."""
        with self._lock:
            self._chunks.clear()
            self._stream = sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=config.CHANNELS,
                dtype=config.DTYPE,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.debug("Recording started")

    def stop(self) -> np.ndarray | None:
        """Stop recording and return the captured audio as a 1-D float32 numpy array.

        Returns None if no audio was captured.
        """
        with self._lock:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0).flatten()
            self._chunks.clear()
            logger.debug("Recording stopped — %d samples (%.2fs)", len(audio), len(audio) / config.SAMPLE_RATE)
            return audio

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("Audio callback status: %s", status)
        with self._lock:
            self._chunks.append(indata.copy())


def trim_silence(audio: np.ndarray) -> np.ndarray | None:
    """Use Silero VAD to trim silence from audio.

    Returns the speech-only audio, or None if no speech was detected.
    """
    model = _get_vad_model()
    audio_tensor = torch.from_numpy(audio).float()

    # Ensure 1-D
    if audio_tensor.ndim > 1:
        audio_tensor = audio_tensor.squeeze()

    timestamps = get_speech_timestamps(
        audio_tensor,
        model,
        threshold=config.VAD_THRESHOLD,
        sampling_rate=config.SAMPLE_RATE,
        min_speech_duration_ms=config.VAD_MIN_SPEECH_MS,
        min_silence_duration_ms=config.VAD_MIN_SILENCE_MS,
    )

    if not timestamps:
        logger.debug("VAD: no speech detected")
        return None

    speech_audio = collect_chunks(timestamps, audio_tensor)
    result = speech_audio.numpy()
    logger.debug(
        "VAD: trimmed %.2fs → %.2fs",
        len(audio) / config.SAMPLE_RATE,
        len(result) / config.SAMPLE_RATE,
    )
    return result
