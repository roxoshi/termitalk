"""Whisper-based transcription engine with backend dispatch."""

import logging
import platform
import time

import numpy as np

from termitalk import config

logger = logging.getLogger(__name__)

_model = None  # faster-whisper WhisperModel or None
_backend: str | None = None  # resolved backend name
_mlx_repo: str | None = None  # HuggingFace repo path for mlx-whisper


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _detect_backend() -> str:
    """Resolve config.BACKEND ("auto"|"faster-whisper"|"mlx-whisper") to a concrete backend."""
    backend = config.BACKEND

    if backend == "mlx-whisper":
        try:
            import mlx_whisper  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "mlx-whisper backend requested but mlx_whisper is not installed.\n"
                "Install it with:  uv pip install 'termitalk[apple]'"
            )
        return "mlx-whisper"

    if backend == "faster-whisper":
        return "faster-whisper"

    # auto: prefer mlx-whisper on Apple Silicon if available
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            return "mlx-whisper"
        except ImportError:
            pass

    return "faster-whisper"


def _mlx_model_repo(model_name: str) -> str:
    """Map a Whisper model name to the corresponding mlx-community HuggingFace repo."""
    known = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "tiny.en": "mlx-community/whisper-tiny.en-mlx",
        "base": "mlx-community/whisper-base-mlx",
        "base.en": "mlx-community/whisper-base.en-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "small.en": "mlx-community/whisper-small.en-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "medium.en": "mlx-community/whisper-medium.en-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    }
    if model_name in known:
        return known[model_name]
    # Fallback: assume mlx-community naming convention
    return f"mlx-community/whisper-{model_name}-mlx"


def get_backend() -> str:
    """Return the resolved backend name (detects on first call)."""
    global _backend
    if _backend is None:
        _backend = _detect_backend()
    return _backend


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model():
    """Load and cache the Whisper model for the active backend."""
    global _model, _mlx_repo

    backend = get_backend()

    if backend == "mlx-whisper":
        if _mlx_repo is not None:
            return
        _mlx_repo = _mlx_model_repo(config.MODEL_NAME)
        logger.info("Using mlx-whisper backend — model repo: %s", _mlx_repo)
        # mlx_whisper downloads/caches on first transcribe; nothing to preload
        return

    # faster-whisper path
    if _model is not None:
        return _model

    from faster_whisper import WhisperModel

    device = config.DEVICE
    compute_type = config.COMPUTE_TYPE

    # Smart GPU auto-detection: if device=auto and CUDA is available,
    # upgrade compute_type to float16 for faster GPU inference
    if device == "auto" and compute_type == "int8":
        try:
            import torch
            if torch.cuda.is_available():
                compute_type = "float16"
                logger.info("CUDA detected — using float16 for GPU acceleration")
        except ImportError:
            pass

    logger.info("Loading Whisper model '%s' (device=%s, compute=%s)...",
                config.MODEL_NAME, device, compute_type)
    t0 = time.perf_counter()
    _model = WhisperModel(
        config.MODEL_NAME,
        device=device,
        compute_type=compute_type,
        cpu_threads=config.CPU_THREADS,
    )
    logger.info("Model loaded in %.2fs", time.perf_counter() - t0)
    return _model


# ---------------------------------------------------------------------------
# Warm-up
# ---------------------------------------------------------------------------

def warm_up():
    """Run a dummy transcription to prime the model and eliminate cold-start latency."""
    load_model()
    backend = get_backend()
    logger.info("Warming up model (%s)...", backend)
    t0 = time.perf_counter()
    dummy = np.zeros(config.SAMPLE_RATE, dtype=np.float32)  # 1 second of silence

    if backend == "mlx-whisper":
        import mlx_whisper
        mlx_whisper.transcribe(
            dummy,
            path_or_hf_repo=_mlx_repo,
            language=config.LANGUAGE,
            word_timestamps=False,
            condition_on_previous_text=False,
        )
    else:
        segments, _ = _model.transcribe(
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


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio buffer to text.

    Args:
        audio: 1-D float32 numpy array at 16kHz.

    Returns:
        Transcribed text string, or empty string if nothing was recognized.
    """
    load_model()
    backend = get_backend()

    if len(audio) < config.SAMPLE_RATE * 0.1:  # Less than 100ms
        logger.debug("Audio too short (%.0fms), skipping", len(audio) / config.SAMPLE_RATE * 1000)
        return ""

    t0 = time.perf_counter()

    if backend == "mlx-whisper":
        import mlx_whisper
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=_mlx_repo,
            language=config.LANGUAGE,
            beam_size=config.BEAM_SIZE,
            temperature=config.TEMPERATURE,
            initial_prompt=config.INITIAL_PROMPT,
            word_timestamps=False,
            condition_on_previous_text=config.CONDITION_ON_PREVIOUS_TEXT,
        )
        text = (result.get("text") or "").strip()
    else:
        segments, info = _model.transcribe(
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
