"""Tests for the free-model gateway client and its MCP surface (no network)."""
from __future__ import annotations

import json

from jarvis import free_models
from jarvis.mcp_server import handle_tools_call, handle_tools_list


def test_catalog_is_small_and_verified():
    ids = [m["id"] for m in free_models.FREE_MODEL_CATALOG]
    assert len(ids) == 6
    assert len(set(ids)) == 6
    assert free_models.FREE_MODEL_CATALOG[0]["id"] == "free-auto"
    assert free_models.DEFAULT_MODEL == "free-auto"


def test_api_key_env_wins(monkeypatch):
    monkeypatch.setenv("NINE_ROUTER_API_KEY", "sk-from-env")
    monkeypatch.setattr(free_models.keyvault, "get_key", lambda _p: "sk-from-vault")
    assert free_models.api_key() == "sk-from-env"


def test_api_key_falls_back_to_vault(monkeypatch):
    monkeypatch.delenv("NINE_ROUTER_API_KEY", raising=False)
    monkeypatch.setattr(free_models.keyvault, "get_key", lambda _p: "sk-from-vault")
    assert free_models.api_key() == "sk-from-vault"


def test_ask_without_key_is_a_clean_error(monkeypatch):
    monkeypatch.delenv("NINE_ROUTER_API_KEY", raising=False)
    monkeypatch.setattr(free_models, "api_key", lambda: None)
    out = free_models.ask_free_model("hello")
    assert out["ok"] is False
    assert "No gateway key" in out["error"]


def test_ask_success_builds_messages(monkeypatch):
    monkeypatch.setattr(free_models, "api_key", lambda: "sk-test")
    captured = {}

    def fake_request(method, path, payload=None, timeout=60.0):
        captured.update(method=method, path=path, payload=payload)
        return {
            "model": "free-auto",
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"total_tokens": 3},
        }

    monkeypatch.setattr(free_models, "_request_json", fake_request)
    out = free_models.ask_free_model("hello", system="be brief")

    assert out["ok"] is True
    assert out["content"] == "OK"
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "be brief"}
    assert captured["payload"]["messages"][-1] == {"role": "user", "content": "hello"}
    assert captured["payload"]["stream"] is False


def test_ask_http_error_is_reported(monkeypatch):
    monkeypatch.setattr(free_models, "api_key", lambda: "sk-test")
    monkeypatch.setattr(
        free_models,
        "_request_json",
        lambda *_a, **_k: {"__http_error__": 401, "__body__": "unauthorized"},
    )
    out = free_models.ask_free_model("hello")
    assert out["ok"] is False
    assert out["status"] == 401


def test_ask_empty_completion_is_an_error(monkeypatch):
    monkeypatch.setattr(free_models, "api_key", lambda: "sk-test")
    monkeypatch.setattr(
        free_models,
        "_request_json",
        lambda *_a, **_k: {"choices": [{"message": {"content": ""}}]},
    )
    out = free_models.ask_free_model("hello")
    assert out["ok"] is False
    assert "empty completion" in out["error"]


def test_ask_rejects_empty_prompt(monkeypatch):
    monkeypatch.setattr(free_models, "api_key", lambda: "sk-test")
    out = free_models.ask_free_model("   ")
    assert out["ok"] is False
    assert out["error"] == "prompt is required"


def test_list_free_models_marks_live_availability(monkeypatch):
    monkeypatch.setattr(
        free_models,
        "available_ids",
        lambda: ["free-auto", "oc/deepseek-v4.1-flash-free"],
    )
    monkeypatch.setattr(free_models, "gateway_status", lambda: {"online": True})
    out = free_models.list_free_models(live=True)
    by_id = {m["id"]: m for m in out["models"]}
    assert out["count"] == 6
    assert by_id["free-auto"]["advertised"] is True
    assert by_id["oc/big-pickle"]["advertised"] is False


def test_health_probe_counts_passes(monkeypatch):
    monkeypatch.setattr(free_models, "gateway_status", lambda: {"online": True})
    monkeypatch.setattr(
        free_models,
        "ask_free_model",
        lambda *_a, **_k: {"ok": True, "ms": 1, "content": "OK"},
    )
    out = free_models.health(probe=True)
    assert out["probed"] is True
    assert out["passed"] == out["total"] == 6


def test_mcp_exposes_free_model_tools():
    response = handle_tools_list(1)
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {"list_free_models", "free_models_health", "ask_free_model"} <= names


def test_mcp_call_list_free_models(monkeypatch):
    monkeypatch.setattr(
        free_models,
        "list_free_models",
        lambda live=True: {"count": 6, "default_model": "free-auto", "live": live},
    )
    response = handle_tools_call(
        2, {"name": "list_free_models", "arguments": {"live": False}}
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["count"] == 6
    assert payload["live"] is False


def test_mcp_call_ask_free_model(monkeypatch):
    monkeypatch.setattr(
        free_models,
        "ask_free_model",
        lambda prompt, **kwargs: {"ok": True, "content": prompt, "model": kwargs.get("model")},
    )
    response = handle_tools_call(
        3,
        {
            "name": "ask_free_model",
            "arguments": {"prompt": "ping", "model": "oc/glm-5.3-flash-free"},
        },
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["model"] == "oc/glm-5.3-flash-free"
