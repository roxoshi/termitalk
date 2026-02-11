"""Whisper-based transcription engine."""

import logging
import time

import numpy as np
from faster_whisper import WhisperModel

from termitalk import config

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def load_model() -> WhisperModel:
    """Load and cache the Whisper model."""
    global _model
    if _model is not None:
        return _model

    logger.info("Loading Whisper model '%s' (device=%s, compute=%s)...",
                config.MODEL_NAME, config.DEVICE, config.COMPUTE_TYPE)
    t0 = time.perf_counter()
    _model = WhisperModel(
        config.MODEL_NAME,
        device=config.DEVICE,
        compute_type=config.COMPUTE_TYPE,
        cpu_threads=config.CPU_THREADS,
    )
    logger.info("Model loaded in %.2fs", time.perf_counter() - t0)
    return _model


def warm_up():
    """Run a dummy transcription to prime the model and eliminate cold-start latency."""
    model = load_model()
    logger.info("Warming up model...")
    t0 = time.perf_counter()
    dummy = np.zeros(config.SAMPLE_RATE, dtype=np.float32)  # 1 second of silence
    segments, _ = model.transcribe(
        dummy,
        beam_size=config.BEAM_SIZE,
        language=config.LANGUAGE,
        temperature=config.TEMPERATURE,
        condition_on_previous_text=config.CONDITION_ON_PREVIOUS_TEXT,
        without_timestamps=True,
    )
    # Consume the generator to actually run inference
    for _ in segments:
        pass
    logger.info("Warm-up complete in %.2fs", time.perf_counter() - t0)


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio buffer to text.

    Args:
        audio: 1-D float32 numpy array at 16kHz.

    Returns:
        Transcribed text string, or empty string if nothing was recognized.
    """
    model = load_model()

    if len(audio) < config.SAMPLE_RATE * 0.1:  # Less than 100ms
        logger.debug("Audio too short (%.0fms), skipping", len(audio) / config.SAMPLE_RATE * 1000)
        return ""

    t0 = time.perf_counter()
    segments, info = model.transcribe(
        audio,
        beam_size=config.BEAM_SIZE,
        language=config.LANGUAGE,
        initial_prompt=config.INITIAL_PROMPT,
        temperature=config.TEMPERATURE,
        condition_on_previous_text=config.CONDITION_ON_PREVIOUS_TEXT,
        vad_filter=False,  # We handle VAD ourselves for tighter control
        without_timestamps=True,
    )

    text = "".join(seg.text for seg in segments).strip()
    elapsed = time.perf_counter() - t0
    logger.debug("Transcribed in %.3fs: %r", elapsed, text)
    return text
