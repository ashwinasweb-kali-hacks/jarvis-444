"""Wake-word detector — local, offline, zero cloud.

Simple energy-based detector on PCM float32 arrays. Not a neural wake-word
engine (Porcupine / openWakeWord) because those need model files and licences;
this is a reasonable fallback that works on any microphone without extra
dependencies.

Usage::

    from jarvis.wake_word import WakeWordDetector
    det = WakeWordDetector(sample_rate=16000)
    if det.check(samples):  # samples: float32 numpy array, 16 kHz mono
        ...   # user said something loud enough; start full STT
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("jarvis.wake_word")


class WakeWordDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        rms_threshold: float = 0.025,
        min_duration_sec: float = 0.4,
        cooldown_sec: float = 1.2,
    ) -> None:
        self.sample_rate = sample_rate
        self.rms_threshold = rms_threshold
        self.min_samples = int(min_duration_sec * sample_rate)
        self.cooldown_samples = int(cooldown_sec * sample_rate)
        self._last_trigger = -self.cooldown_samples
        self._frames = 0

    def reset(self) -> None:
        self._last_trigger = -self.cooldown_samples
        self._frames = 0

    def check(self, samples: np.ndarray) -> bool:
        """Return True when a loud-enough sustained sound is detected."""
        if samples is None or len(samples) == 0:
            return False
        arr = np.asarray(samples, dtype=np.float32).ravel()
        rms = float(np.sqrt(np.mean(arr ** 2))) if arr.size else 0.0
        self._frames += len(arr)
        if (
            rms >= self.rms_threshold
            and self._frames - self._last_trigger >= self.cooldown_samples
        ):
            self._last_trigger = self._frames
            logger.info("Wake-word energy detected (rms=%.4f)", rms)
            return True
        return False

    def set_threshold(self, rms_threshold: float) -> None:
        self.rms_threshold = float(rms_threshold)


def quick_test() -> None:
    """Self-test: silence should not trigger; a tone should."""
    sr = 16000
    det = WakeWordDetector(sample_rate=sr, rms_threshold=0.01)
    silence = np.zeros(sr // 4, dtype=np.float32)
    assert not det.check(silence)
    t = np.linspace(0, 0.5, sr // 2, dtype=np.float32)
    tone = 0.15 * np.sin(2 * np.pi * 440 * t)
    assert det.check(tone)
    print("wake-word self-test passed")
