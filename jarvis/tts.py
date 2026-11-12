"""Unified free text-to-speech with the engines from ``jarvis.voice_models``.

Default is ``edge-tts`` (free Microsoft neural voices, no key, needs internet).
Offline fallbacks, in order: ``piper`` (when its voice file is present), then
``pyttsx3``. Every entry point returns a dict instead of raising, so the daemon
and MCP callers can report the real reason an engine failed.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from jarvis import voice_models

logger = logging.getLogger("jarvis.tts")

_CACHE: Dict[str, Tuple[bytes, str]] = {}
_CACHE_LIMIT = 128
_pyttsx3_engine = None
_pyttsx3_lock = threading.Lock()

# Players we know how to drive without a Python audio library.
_PLAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("ffplay", ("-nodisp", "-autoexit", "-loglevel", "quiet")),
    ("mpv", ("--really-quiet", "--no-video")),
    ("mpg123", ("-q",)),
    ("paplay", ()),
    ("aplay", ("-q",)),
    ("afplay", ()),
)


def piper_voice_path(voice: Optional[str]) -> Optional[Path]:
    """Resolve a Piper ``.onnx`` voice file, or None when it is missing."""
    override = os.environ.get("JARVIS_PIPER_VOICE")
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    if not voice:
        return None
    candidate = Path.home() / ".jarvis" / "voices" / f"{voice}.onnx"
    return candidate if candidate.is_file() else None


def _run_async(coro) -> Any:
    """Run a coroutine from sync code, even inside a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box: Dict[str, Any] = {}

    def worker() -> None:
        try:
            box["value"] = asyncio.run(coro)
        except BaseException as exc:  # surfaced by the caller below
            box["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box.get("value")


# --------------------------------------------------------------- engines
async def _edge_bytes(text: str, voice: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate="-3%", pitch="-1Hz")
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("edge-tts returned no audio (offline?)")
    return bytes(audio)


def _piper_bytes(text: str, voice: Optional[str]) -> bytes:
    binary = shutil.which("piper")
    if not binary:
        raise RuntimeError("piper binary not on PATH (pip install piper-tts)")
    model_path = piper_voice_path(voice)
    if model_path is None:
        raise RuntimeError(
            "Piper voice file missing; set JARVIS_PIPER_VOICE to a .onnx file "
            "or download one into ~/.jarvis/voices/"
        )
    with tempfile.TemporaryDirectory(prefix="jarvis-piper-") as tmp:
        out = Path(tmp) / "line.wav"
        proc = subprocess.run(
            [binary, "--model", str(model_path), "--output_file", str(out)],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=60,
        )
        if proc.returncode != 0 or not out.is_file():
            raise RuntimeError(
                "piper failed: " + (proc.stderr.decode("utf-8", "replace")[:200] or "no output")
            )
        return out.read_bytes()


def _kokoro_bytes(text: str, voice: Optional[str]) -> bytes:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="b" if (voice or "").startswith(("b", "a")) else "a")
    chunks = [audio for _, _, audio in pipeline(text, voice=voice or "bm_george")]
    if not chunks:
        raise RuntimeError("kokoro returned no audio")
    samples = np.concatenate([np.asarray(c) for c in chunks]).astype("float32")
    buf = io.BytesIO()
    sf.write(buf, samples, 24000, format="WAV")
    return buf.getvalue()


def get_engine():
    """Lazily initialise the shared pyttsx3 engine (last-resort fallback)."""
    global _pyttsx3_engine
    if _pyttsx3_engine is None:
        import pyttsx3

        _pyttsx3_engine = pyttsx3.init()
        _pyttsx3_engine.setProperty("rate", 170)
    return _pyttsx3_engine


def _pyttsx3_bytes(text: str, voice: Optional[str]) -> bytes:
    engine = get_engine()
    with tempfile.TemporaryDirectory(prefix="jarvis-tts-") as tmp:
        out = Path(tmp) / "line.wav"
        with _pyttsx3_lock:
            engine.save_to_file(text, str(out))
            engine.runAndWait()
        if not out.is_file() or out.stat().st_size == 0:
            raise RuntimeError("pyttsx3 produced no audio")
        return out.read_bytes()


_ENGINES = {
    "edge_tts": (_edge_bytes, "audio/mpeg"),
    "piper": (_piper_bytes, "audio/wav"),
    "kokoro": (_kokoro_bytes, "audio/wav"),
    "pyttsx3": (_pyttsx3_bytes, "audio/wav"),
}


def _synthesize_one(
    text: str, voice: Optional[str], model_id: str, agent: Optional[str] = None
) -> Tuple[bytes, str]:
    entry = voice_models.get_tts(model_id)
    engine_id = entry.get("engine") or model_id
    if engine_id not in _ENGINES:
        raise ValueError(f"TTS engine '{engine_id}' is not wired up yet")
    engine, mime = _ENGINES[engine_id]
    resolved = voice or (voice_models.voice_for(agent or "jarvis", model_id) if agent else None)
    if engine_id == "edge_tts":
        resolved = resolved or "en-GB-RyanNeural"
        return _run_async(_edge_bytes(text, resolved)), mime
    return engine(text, resolved), mime


def _fallback_chain(model_id: str) -> list:
    chain = [model_id]
    for candidate in ("piper", "pyttsx3"):
        if candidate not in chain:
            chain.append(candidate)
    return chain


def synthesize(
    text: str,
    voice: Optional[str] = None,
    model: Optional[str] = None,
    agent: Optional[str] = None,
    fallback: bool = True,
) -> Dict[str, Any]:
    """Render speech to audio bytes.

    Returns ``{"ok", "model", "mime", "audio"}`` or ``{"ok": False, "error"}``.
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "text is required"}

    model_id = (model or voice_models.tts_model()).strip()
    chain = _fallback_chain(model_id) if fallback else [model_id]
    errors = []

    for candidate in chain:
        key = f"{candidate}::{voice or ''}::{agent or ''}::{text}"
        if key in _CACHE:
            audio, mime = _CACHE[key]
            return {"ok": True, "model": candidate, "mime": mime, "audio": audio, "cached": True}
        try:
            audio, mime = _synthesize_one(text, voice, candidate, agent=agent)
        except Exception as exc:
            logger.warning("TTS engine %s failed: %s", candidate, exc)
            errors.append(f"{candidate}: {exc}")
            continue
        if len(_CACHE) >= _CACHE_LIMIT:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (audio, mime)
        return {"ok": True, "model": candidate, "mime": mime, "audio": audio}

    return {"ok": False, "model": model_id, "error": "; ".join(errors) or "no TTS engine available"}


# ----------------------------------------------------------------- playback
def _play_audio(audio: bytes, mime: str) -> bool:
    suffix = ".mp3" if mime == "audio/mpeg" else ".wav"
    tmp_dir = Path(tempfile.mkdtemp(prefix="jarvis-play-"))
    path = tmp_dir / f"line{suffix}"
    path.write_bytes(audio)
    try:
        for name, extra in _PLAYERS:
            binary = shutil.which(name)
            if not binary:
                continue
            try:
                subprocess.run([binary, *extra, str(path)], capture_output=True, timeout=120)
                return True
            except Exception as exc:
                logger.debug("%s playback failed: %s", name, exc)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return False


def speak(text: str, voice: Optional[str] = None, model: Optional[str] = None) -> bool:
    """Speak text out loud. Returns True only when audio actually played."""
    outcome = synthesize(text, voice=voice, model=model)
    if outcome.get("ok") and _play_audio(outcome["audio"], outcome.get("mime", "audio/wav")):
        return True
    # pyttsx3 can speak through its own backend when no player was found.
    try:
        engine = get_engine()
        with _pyttsx3_lock:
            engine.say(text)
            engine.runAndWait()
        return True
    except Exception as exc:
        logger.error("TTS playback failed: %s", exc)
        return False
