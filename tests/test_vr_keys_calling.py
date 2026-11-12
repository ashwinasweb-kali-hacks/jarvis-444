"""Tests for the VR / key vault / GlobalFone additions. No hardware, no network."""
from __future__ import annotations

import json

import pytest

from jarvis import keyvault
from jarvis.brain import respond
from jarvis.mcp_server import handle_tools_call
from jarvis.tools.globalfone import GlobalFoneCallTool


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    monkeypatch.setattr(keyvault, "KEYS_PATH", path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_GLOBALFONE_TOKEN", raising=False)
    return path


# ---------------------------------------------------------------- key vault
def test_set_key_stores_and_masks(vault):
    out = keyvault.set_key("gemini", "AIzaSyTESTKEY1234567890")
    assert out["ok"] is True
    assert "TESTKEY" not in json.dumps(out)
    assert out["masked"].startswith("AIza")
    assert vault.exists()


def test_list_keys_reports_source(vault, monkeypatch):
    keyvault.set_key("openai", "sk-test-abcdefghijklmnop")
    monkeypatch.setenv("GEMINI_API_KEY", "env-provided-key-value")
    rows = {r["provider"]: r for r in keyvault.list_keys()}
    assert rows["openai"]["source"] == "file"
    assert rows["gemini"]["source"] == "env"
    assert rows["gemini"]["masked"] != "env-provided-key-value"


def test_env_beats_file(vault, monkeypatch):
    keyvault.set_key("gemini", "from-file-value-123")
    monkeypatch.setenv("GEMINI_API_KEY", "from-env-value-456")
    assert keyvault.get_key("gemini") == "from-env-value-456"


def test_delete_key(vault):
    keyvault.set_key("anthropic", "sk-ant-1234567890")
    assert keyvault.delete_key("anthropic")["ok"] is True
    assert keyvault.delete_key("anthropic")["ok"] is False


def test_short_key_rejected(vault):
    assert keyvault.set_key("gemini", "abc")["ok"] is False


# ------------------------------------------------------------- globalfone
def test_globalfone_without_config_never_claims_a_call(monkeypatch):
    monkeypatch.delenv("JARVIS_GLOBALFONE_URL", raising=False)
    out = GlobalFoneCallTool().run(to="8825586080", provider="globalfone")
    assert out["placed"] is False
    assert "not configured" in out["message"]


def test_auto_falls_back_to_dialer(monkeypatch):
    monkeypatch.delenv("JARVIS_GLOBALFONE_URL", raising=False)
    monkeypatch.delenv("JARVIS_GLOBALFONE_TOKEN", raising=False)

    calls = []
    monkeypatch.setattr(
        "jarvis.tools.globalfone.subprocess.Popen",
        lambda *a, **k: calls.append(a),
    )
    out = GlobalFoneCallTool().run(to="8825586080", provider="auto")
    assert out["channel"] == "system_dialer"
    assert out["placed"] is True
    assert calls, "dialer was never invoked"


def test_number_normalised_to_e164():
    out = GlobalFoneCallTool().run(to="88255-86080", provider="dialer")
    assert out["number"] == "+918825586080"


# ------------------------------------------------------------------- brain
def test_enter_vr_intent_is_zero_token():
    reply = respond("enter vr mode")
    assert reply.tokens_used == 0
    assert reply.actions[0]["tool"] == "ui"
    assert reply.actions[0]["args"]["action"] == "enter_vr"


def test_exit_vr_intent():
    reply = respond("exit vr")
    assert reply.actions[0]["args"]["action"] == "exit_vr"


def test_globalfone_routing_intent():
    reply = respond("call 8825586080 via globalfone")
    assert reply.actions[0]["tool"] == "globalfone_call"
    assert reply.actions[0]["args"]["provider"] == "globalfone"


# --------------------------------------------------------------- mcp surface
def test_mcp_set_api_key_masks_value(vault):
    resp = handle_tools_call(1, {"name": "set_api_key", "arguments": {"provider": "openai", "key": "sk-live-abcdefghijkl"}})
    text = resp["result"]["content"][0]["text"]
    assert "sk-live-abcdefghijkl" not in text
    assert "masked" in text


def test_mcp_call_phone_reports_channel(monkeypatch):
    monkeypatch.delenv("JARVIS_GLOBALFONE_URL", raising=False)
    monkeypatch.setattr("jarvis.tools.globalfone.subprocess.Popen", lambda *a, **k: None)
    resp = handle_tools_call(2, {"name": "call_phone", "arguments": {"to": "8825586080"}})
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["channel"] == "system_dialer"
