"""Tests for the free TTS/STT catalog and the shared voice engines (no network)."""
from __future__ import annotations

import asyncio
import io
import json
import wave

import numpy as np
import pytest

from jarvis import stt, tts, voice_models
from jarvis.mcp_server import handle_tools_call, handle_tools_list


def _boom(*_args, **_kwargs):
    raise RuntimeError("offline")


def _wav_bytes(samples: np.ndarray, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes((samples * 32767).astype("<i2").tobytes())
    return buf.getvalue()


# ------------------------------------------------------------------ catalog
def test_catalog_has_exactly_one_default_each():
    for catalog in (voice_models.TTS_CATALOG, voice_models.STT_CATALOG):
        assert len(catalog) >= 3
        assert len([m for m in catalog if m.get("default")]) == 1
        assert len({m["id"] for m in catalog}) == len(catalog)


def test_best_free_defaults_are_chosen():
    assert voice_models.default_tts_id() == "edge-tts"
    assert voice_models.default_stt_id() == "faster-whisper-small.en"
    assert voice_models.whisper_size() == "small.en"


def test_env_overrides_pick_other_models(monkeypatch):
    monkeypatch.setenv("JARVIS_TTS_MODEL", "piper")
    monkeypatch.setenv("JARVIS_STT_MODEL", "faster-whisper-tiny.en")
    assert voice_models.tts_model() == "piper"
    assert voice_models.stt_model() == "faster-whisper-tiny.en"
    assert voice_models.whisper_size() == "tiny.en"


def test_raw_whisper_size_still_works(monkeypatch):
    monkeypatch.setenv("JARVIS_MODEL", "base.en")
    assert voice_models.whisper_size() == "base.en"
    assert stt.resolve_model_size("tiny") == "tiny"


def test_unknown_model_is_a_clear_error():
    with pytest.raises(ValueError) as err:
        voice_models.get_tts("nope")
    assert "unknown TTS model" in str(err.value)
    with pytest.raises(ValueError):
        voice_models.get_stt("nope")


def test_voice_for_agent_uses_engine_native_ids():
    assert voice_models.voice_for("friday") == "en-GB-SoniaNeural"
    assert voice_models.voice_for("jarvis", "piper").startswith("en_GB-")


def test_list_voice_models_shape():
    out = voice_models.list_voice_models(live=False)
    assert out["default_tts"] == "edge-tts"
    assert out["tts"]["count"] == len(voice_models.TTS_CATALOG)
    assert out["stt"]["count"] == len(voice_models.STT_CATALOG)
    assert all("installed" not in m for m in out["tts"]["models"])
    live = voice_models.list_voice_models(live=True)
    assert all("installed" in m for m in live["stt"]["models"])


def test_config_uses_catalog_defaults(monkeypatch):
    pytest.importorskip("sounddevice")
    from jarvis.config import JarvisConfig

    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    monkeypatch.delenv("JARVIS_TTS_MODEL", raising=False)
    monkeypatch.delenv("JARVIS_STT_MODEL", raising=False)
    cfg = JarvisConfig()
    assert cfg.tts_model == "edge-tts"
    assert cfg.stt_model == "faster-whisper-small.en"
    assert cfg.model_size == "small.en"

    monkeypatch.setenv("JARVIS_TTS_MODEL", "pyttsx3")
    monkeypatch.setenv("JARVIS_STT_MODEL", "faster-whisper-tiny.en")
    env_cfg = JarvisConfig.from_env()
    assert env_cfg.tts_model == "pyttsx3"
    assert env_cfg.stt_model == "faster-whisper-tiny.en"


# ---------------------------------------------------------------------- TTS
def test_synthesize_rejects_empty_text():
    out = tts.synthesize("   ")
    assert out["ok"] is False
    assert out["error"] == "text is required"


def test_synthesize_falls_back_to_offline_engine(monkeypatch):
    calls = []

    def fake(text, voice, model_id, agent=None):
        calls.append(model_id)
        if model_id != "pyttsx3":
            raise RuntimeError("no internet")
        return b"RIFF", "audio/wav"

    monkeypatch.setattr(tts, "_synthesize_one", fake)
    tts._CACHE.clear()
    out = tts.synthesize("hello sir", model="edge-tts", agent="jarvis")
    assert out["ok"] is True
    assert out["model"] == "pyttsx3"
    assert out["mime"] == "audio/wav"
    assert calls == ["edge-tts", "piper", "pyttsx3"]


def test_synthesize_without_fallback_reports_the_error(monkeypatch):
    monkeypatch.setattr(tts, "_synthesize_one", _boom)
    tts._CACHE.clear()
    out = tts.synthesize("hello", model="edge-tts", fallback=False)
    assert out["ok"] is False
    assert "offline" in out["error"]


def test_synthesize_caches_repeated_lines(monkeypatch):
    hits = []

    def fake(text, voice, model_id, agent=None):
        hits.append(model_id)
        return b"ID3", "audio/mpeg"

    monkeypatch.setattr(tts, "_synthesize_one", fake)
    tts._CACHE.clear()
    assert tts.synthesize("same line", model="edge-tts")["ok"] is True
    second = tts.synthesize("same line", model="edge-tts")
    assert second["cached"] is True
    assert hits == ["edge-tts"]


def test_daemon_edge_wrapper_uses_shared_engine(monkeypatch):
    pytest.importorskip("sounddevice")
    from jarvis import daemon

    monkeypatch.setattr(
        daemon.voice_out, "synthesize", lambda *a, **k: {"ok": True, "audio": b"ID3"}
    )
    assert asyncio.run(daemon._synthesize_edge_tts("hi", "en-GB-RyanNeural")) == b"ID3"


# ---------------------------------------------------------------------- STT
def test_wav_bytes_roundtrip_to_float32():
    tone = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, 1600, dtype=np.float32))
    audio = stt.wav_bytes_to_float32(_wav_bytes(tone))
    assert audio.dtype == np.float32
    assert len(audio) == 1600
    assert np.isclose(float(np.max(audio)), 0.5, atol=0.01)


def test_transcribe_wav_bytes_uses_the_local_model(monkeypatch):
    class Segment:
        text = " Open the blast doors "
        no_speech_prob = 0.01
        avg_logprob = -0.2

    class FakeModel:
        def transcribe(self, audio, **kwargs):
            assert kwargs["vad_filter"] is True
            return [Segment()], {}

    monkeypatch.setattr(stt, "get_model", lambda **kwargs: FakeModel())
    text = stt.transcribe_wav_bytes(_wav_bytes(np.zeros(1600, dtype=np.float32)))
    assert text == "Open the blast doors"


def test_transcribe_wav_bytes_filters_noise(monkeypatch):
    class Segment:
        text = "Thanks for watching!"
        no_speech_prob = 0.9
        avg_logprob = -2.0

    class FakeModel:
        def transcribe(self, audio, **kwargs):
            return [Segment()], {}

    monkeypatch.setattr(stt, "get_model", lambda **kwargs: FakeModel())
    assert stt.transcribe_wav_bytes(_wav_bytes(np.zeros(1600, dtype=np.float32))) == ""


# ---------------------------------------------------------------------- MCP
def test_mcp_exposes_voice_tools():
    names = {tool["name"] for tool in handle_tools_list(1)["result"]["tools"]}
    assert {"list_voice_models", "speak_text"} <= names


def test_mcp_call_list_voice_models():
    response = handle_tools_call(
        2, {"name": "list_voice_models", "arguments": {"live": False}}
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["default_tts"] == "edge-tts"
    assert payload["default_stt"] == "faster-whisper-small.en"


def test_mcp_speak_text_reports_spoken(monkeypatch):
    monkeypatch.setattr(tts, "_synthesize_one", lambda *a, **k: (b"ID3", "audio/mpeg"))
    monkeypatch.setattr(tts, "speak", lambda *a, **k: True)
    tts._CACHE.clear()
    response = handle_tools_call(
        3, {"name": "speak_text", "arguments": {"text": "Good evening, sir.", "agent": "jarvis"}}
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["spoken"] is True
    assert payload["model"] == "edge-tts"
