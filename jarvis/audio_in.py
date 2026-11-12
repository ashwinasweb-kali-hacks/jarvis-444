"""Microphone recording utilities returning in-memory float32 numpy arrays.

Supports both fixed-length recording and smart silence-detection (RMS-based)
recording that stops after a configurable silence window.
"""
import time
from typing import Optional, Callable
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024  # ~64 ms per block at 16 kHz


def calculate_rms(chunk: np.ndarray) -> float:
    """Compute Root Mean Square (RMS) energy of a 1D float32 audio slice."""
    if len(chunk) == 0:
        return 0.0
    return float(np.sqrt(np.mean(chunk**2)))


def record_fixed(seconds: float = 3.0, sample_rate: int = SAMPLE_RATE, device: Optional[int] = None) -> np.ndarray:
    """Record a fixed duration of audio and return a 1D float32 numpy array normalized to [-1.0, 1.0]."""
    total_frames = int(seconds * sample_rate)
    audio = sd.rec(
        total_frames,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()
    return audio.flatten()


def record_smart(
    sample_rate: int = SAMPLE_RATE,
    silence_threshold: float = 0.015,
    silence_duration: float = 0.8,
    min_speech_duration: float = 0.3,
    max_duration: float = 15.0,
    device: Optional[int] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> Optional[np.ndarray]:
    """Record until `silence_duration` seconds of quiet is detected after speech begins.

    Returns:
        1D float32 numpy array if speech above `min_speech_duration` was recorded;
        None if silence timed out or the recording was under `min_speech_duration`.
    """
    chunks = []
    has_spoken = False
    silence_start: Optional[float] = None
    start_time = time.time()
    speech_start_time: Optional[float] = None

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", blocksize=BLOCK_SIZE, device=device) as stream:
        while True:
            if should_stop and should_stop():
                break

            data, overflowed = stream.read(BLOCK_SIZE)
            chunk = data.flatten()
            rms = calculate_rms(chunk)
            now = time.time()

            # Hard upper cap
            if now - start_time >= max_duration:
                break

            if not has_spoken:
                # Waiting for initial speech to begin
                if rms > silence_threshold:
                    has_spoken = True
                    speech_start_time = now
                    chunks.append(chunk)
                    silence_start = None
                else:
                    # Rolling buffer before speech starts (keep last ~0.3s for speech onset)
                    max_preload = int(0.3 * sample_rate / BLOCK_SIZE)
                    chunks.append(chunk)
                    if len(chunks) > max_preload:
                        chunks.pop(0)
            else:
                chunks.append(chunk)
                if rms < silence_threshold:
                    if silence_start is None:
                        silence_start = now
                    elif now - silence_start >= silence_duration:
                        # Required silence achieved after speaking
                        break
                else:
                    silence_start = None

    if not has_spoken or not chunks:
        return None

    audio = np.concatenate(chunks)
    duration = len(audio) / sample_rate
    if duration < min_speech_duration:
        return None

    return audio
