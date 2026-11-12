"""Local speech-to-text using faster-whisper.

The size comes from ``jarvis.voice_models``: by default the best free local
model (``small.en``), overridable with ``JARVIS_STT_MODEL`` or the raw
``JARVIS_MODEL`` size. Includes hallucination/noise filtering, high
``no_speech_prob`` suppression and low ``avg_logprob`` filtering (Stage 2.4).
"""
from typing import Dict, Optional, Set, Tuple, Union
import io
import wave

import numpy as np

from jarvis import voice_models

_models: Dict[Tuple[str, str, str], object] = {}

# Known hallucination phrases emitted by Whisper on background noise / silence
DEFAULT_HALLUCINATION_BLOCKLIST: Set[str] = {
    "thank you.",
    "thank you",
    "you",
    "you.",
    "thanks for watching.",
    "thanks for watching!",
    "subtitles by",
    "subtitle by",
    "subscribe",
    "watching",
    "bye.",
    "bye",
    ".",
    "...",
}


def resolve_model_size(model_size: Optional[str] = None) -> str:
    """Whisper size for a given model id/size (default: best free model)."""
    return voice_models.whisper_size(model_size)


def get_model(
    model_size: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8",
):
    """Lazy-load and cache the WhisperModel instance."""
    return preload_model(model_size=model_size, device=device, compute_type=compute_type)


def preload_model(
    model_size: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8",
):
    """Preload and warm up the Whisper model, printing status messages."""
    size = resolve_model_size(model_size)
    key = (size, device, compute_type)
    if key not in _models:
        from faster_whisper import WhisperModel

        print(f"Loading speech model ({size})...", flush=True)
        _models[key] = WhisperModel(size, device=device, compute_type=compute_type)
        print("Model ready.", flush=True)
    return _models[key]


def filter_text(
    text: str,
    no_speech_prob: float = 0.0,
    avg_logprob: float = 0.0,
    max_no_speech_prob: float = 0.6,
    min_avg_logprob: float = -1.5,
    blocklist: Optional[Set[str]] = None,
) -> str:
    """Filter candidate transcript against hallucination blocklists and confidence bounds.

    Returns sanitized transcript string or empty string if filtered.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""

    # Confidence check
    if no_speech_prob > max_no_speech_prob:
        return ""
    if avg_logprob < min_avg_logprob:
        return ""

    # Hallucination blocklist check
    bl = blocklist if blocklist is not None else DEFAULT_HALLUCINATION_BLOCKLIST
    if cleaned.lower() in bl:
        return ""

    return cleaned


def transcribe(
    audio: Union[str, np.ndarray],
    language: str = "en",
    condition_on_previous_text: bool = False,
    max_no_speech_prob: float = 0.6,
    min_avg_logprob: float = -1.5,
    model_size: Optional[str] = None,
) -> str:
    """Transcribe audio (file path or 16 kHz float32 numpy array) to filtered text.

    Args:
        audio: Path to audio file or 1D float32 numpy array.
        language: Language code ("en" forced as per spec).
        condition_on_previous_text: False to prevent loop hallucinations.
        max_no_speech_prob: Maximum allowed no_speech_prob threshold.
        min_avg_logprob: Minimum allowed avg_logprob threshold.
        model_size: Whisper size or STT model id (default: best free model).
    """
    model = get_model(model_size=model_size)
    segments, _ = model.transcribe(
        audio,
        language=language,
        condition_on_previous_text=condition_on_previous_text,
        vad_filter=True,
    )

    valid_parts = []
    for seg in segments:
        part = filter_text(
            seg.text,
            no_speech_prob=getattr(seg, "no_speech_prob", 0.0),
            avg_logprob=getattr(seg, "avg_logprob", 0.0),
            max_no_speech_prob=max_no_speech_prob,
            min_avg_logprob=min_avg_logprob,
        )
        if part:
            valid_parts.append(part)

    return " ".join(valid_parts).strip()


def wav_bytes_to_float32(data: bytes, target_rate: int = 16000) -> np.ndarray:
    """Decode mono 16-bit PCM WAV bytes (what the browser sends) to float32."""
    with wave.open(io.BytesIO(data), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if width != 2:
        raise ValueError(f"expected 16-bit PCM, got {width * 8}-bit")

    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if rate != target_rate and len(samples):
        # Cheap linear resample: the browser sends 16 kHz already, this is a guard.
        count = int(round(len(samples) * target_rate / rate))
        samples = np.interp(
            np.linspace(0.0, len(samples) - 1, count, dtype=np.float32),
            np.arange(len(samples), dtype=np.float32),
            samples,
        ).astype(np.float32)
    return samples


def transcribe_wav_bytes(
    data: bytes,
    language: str = "en",
    model_size: Optional[str] = None,
) -> str:
    """Transcribe recorded WAV bytes locally (no cloud, no API key)."""
    audio = wav_bytes_to_float32(data)
    return transcribe(audio, language=language, model_size=model_size)
