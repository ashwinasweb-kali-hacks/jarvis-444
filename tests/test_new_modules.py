"""Tests for settings, webrtc signaling, wake word, and filesystem tools."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from jarvis import settings as settings_mod
from jarvis.brain import respond
from jarvis.mcp_server import handle_tools_call
from jarvis.tools.filesystem import ReadFileTool, ListDirTool, WriteFileTool, ProcessListTool
from jarvis.wake_word import WakeWordDetector, quick_test


# ------------------------------------------------------------------ settings
@pytest.fixture()
def clean_settings(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_PATH", path)
    monkeypatch.delenv("JARVIS_SETTING_VOICE", raising=False)
    return path


def test_settings_roundtrip(clean_settings):
    assert settings_mod.set("voice", "friday")["ok"] is True
    assert settings_mod.get("voice") == "friday"
    assert settings_mod.get("nonexistent", "fallback") == "fallback"
    assert settings_mod.delete("voice")["ok"] is True
    assert settings_mod.delete("voice")["ok"] is False


def test_env_override_beats_file(clean_settings, monkeypatch):
    settings_mod.set("brain_provider", "from-file")
    monkeypatch.setenv("JARVIS_SETTING_BRAIN_PROVIDER", "from-env")
    assert settings_mod.get("brain_provider") == "from-env"


def test_settings_defaults(clean_settings):
    defaults = settings_mod.defaults()
    assert defaults["voice"] == "jarvis"
    assert defaults["demo_number"] == "8825586080"
    assert defaults["brain_provider"] == "oauth"


def test_settings_mcp_roundtrip(clean_settings):
    resp = handle_tools_call(1, {"name": "set_setting", "arguments": {"key": "demo_number", "value": "8825586080"}})
    assert resp["result"]["content"][0]["text"]
    resp2 = handle_tools_call(2, {"name": "get_settings", "arguments": {}})
    payload = json.loads(resp2["result"]["content"][0]["text"])
    assert payload["settings"]["demo_number"] == "8825586080"


# --------------------------------------------------------------- webrtc
def test_webrtc_signal_roundtrip(monkeypatch):
    import jarvis.webrtc as w
    # Fresh module state
    w._ROOMS.clear()
    out = w.signal_room("demo", "pc", sdp={"type": "offer", "sdp": "v=0"})
    assert out["peers"]["pc"]["sdp"]["type"] == "offer"
    state = w.signal_room("demo", "glasses", get_state=True)
    assert state["peers"]["pc"]["sdp"]["type"] == "offer"
    rooms = w.list_rooms()
    assert any(r["room"] == "demo" for r in rooms["rooms"])


# --------------------------------------------------------------- wake word
def test_wake_word_self_test():
    quick_test()


def test_wake_word_threshold():
    import numpy as np
    det = WakeWordDetector(sample_rate=16000, rms_threshold=0.05)
    silence = np.zeros(1600, dtype=np.float32)
    assert not det.check(silence)
    tone = 0.2 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, 1600, dtype=np.float32))
    assert det.check(tone)


# ---------------------------------------------------------- filesystem tools
def test_read_write_list_tmp(tmp_path, monkeypatch):
    import jarvis.tools.filesystem as fs
    # Override allowed roots to include tmp_path
    monkeypatch.setattr(fs, "_ALLOWED_ROOTS", [tmp_path.resolve()])

    f = tmp_path / "note.txt"
    f.write_text("hello jarvis")

    res = ReadFileTool().run(path=str(f))
    assert res["ok"] is True
    assert res["content"] == "hello jarvis"

    res = WriteFileTool().run(path=str(tmp_path / "new.txt"), content="created by jarvis")
    assert res["ok"] is True
    assert (tmp_path / "new.txt").read_text() == "created by jarvis"

    res = ListDirTool().run(path=str(tmp_path))
    assert res["ok"] is True
    names = [e["name"] for e in res["entries"]]
    assert "note.txt" in names and "new.txt" in names

    # Path outside root is blocked
    res = ReadFileTool().run(path="/etc/passwd")
    assert res["ok"] is False
    assert res["status"] == "blocked"


def test_process_list_shape(monkeypatch):
    try:
        import psutil  # noqa
    except ImportError:
        pytest.skip("psutil not installed")
    res = ProcessListTool().run()
    assert res["ok"] is True
    assert isinstance(res["processes"], list)
    if res["processes"]:
        assert "pid" in res["processes"][0]
        assert "name" in res["processes"][0]


# --------------------------------------------------------------- brain intents
def test_command_index_intent_zero_tokens():
    reply = respond("commands")
    assert reply.tokens_used == 0
    assert reply.actions[0]["tool"] == "ui"
    assert reply.actions[0]["args"]["action"] == "show_help"

    reply = respond("hide help")
    assert reply.actions[0]["args"]["action"] == "hide_help"
