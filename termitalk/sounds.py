"""Audio feedback cues — short tones for recording start/stop/error."""

import logging
import threading

import numpy as np
import sounddevice as sd

from termitalk import config

logger = logging.getLogger(__name__)

# Tone definitions: (frequency_hz, duration_ms, volume 0-1)
_TONES = {
    "start": [(600, 80, 0.3)],                          # Short low boop
    "stop": [(800, 60, 0.25), (1200, 80, 0.25)],        # Rising two-tone beep
    "error": [(300, 120, 0.3), (200, 150, 0.3)],         # Descending error tone
    "ready": [(800, 50, 0.15), (1000, 50, 0.15), (1200, 60, 0.15)],  # Cheerful triple
}

_OUTPUT_RATE = 44100  # Playback sample rate (separate from recording rate)


def play(name: str):
    """Play a named sound cue in a background thread.

    Does nothing if config.SOUND_ENABLED is False.
    """
    if not config.SOUND_ENABLED:
        return
    if name not in _TONES:
        logger.warning("Unknown sound cue: %s", name)
        return
    threading.Thread(target=_play_tones, args=(_TONES[name],), daemon=True).start()


def _play_tones(tones: list[tuple[int, int, float]]):
    """Generate and play a sequence of sine wave tones."""
    try:
        segments = []
        for freq, duration_ms, volume in tones:
            t = np.linspace(0, duration_ms / 1000, int(_OUTPUT_RATE * duration_ms / 1000), dtype=np.float32)
            # Sine wave with quick fade-in/fade-out to avoid clicks
            wave = np.sin(2 * np.pi * freq * t) * volume
            fade_samples = min(int(_OUTPUT_RATE * 0.005), len(wave) // 4)  # 5ms fade
            if fade_samples > 0:
                wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
                wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            segments.append(wave)
            # Tiny gap between tones in a sequence
            if len(tones) > 1:
                segments.append(np.zeros(int(_OUTPUT_RATE * 0.02), dtype=np.float32))

        audio = np.concatenate(segments)
        sd.play(audio, samplerate=_OUTPUT_RATE, blocking=True)
    except Exception as e:
        logger.debug("Could not play sound: %s", e)
