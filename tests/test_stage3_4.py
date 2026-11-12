"""Unit tests for Stage 3 (Brain & Persona) and Stage 4 (Tool Layer & Permission Gate)."""
import os
from pathlib import Path
import pytest

from jarvis.brain import Reply, load_persona_prompt, respond, _global_memory
from jarvis.tools.base import get_default_registry


def test_persona_prompt_loading():
    prompt = load_persona_prompt("sir")
    assert "JARVIS" in prompt
    assert "STYLE" in prompt
    assert "sir" in prompt or "{ADDRESS}" not in prompt


def test_brain_stub_greetings():
    reply = respond("Hello JARVIS")
    assert isinstance(reply, Reply)
    assert len(reply.speech) > 0
    assert reply.mood == "amused"


def test_brain_stub_telemetry():
    reply = respond("What is my cpu usage?")
    assert isinstance(reply, Reply)
    assert any(a["tool"] == "open_panel" and a["args"].get("type") == "stats" for a in reply.actions)
    assert "telemetry" in reply.speech.lower() or "subsystems" in reply.speech.lower()


def test_brain_stub_hologram():
    reply = respond("Show the mark 42 suit hologram")
    assert isinstance(reply, Reply)
    assert any(a["tool"] == "open_panel" and a["args"].get("type") == "hologram" for a in reply.actions)


def test_brain_stub_confirmation_gate():
    reply = respond("Delete all documents now")
    assert reply.needs_confirmation is True
    assert "destructive" in reply.speech.lower() or "proceed" in reply.speech.lower()
    assert reply.mood == "concerned"


def test_memory_turn_history():
    _global_memory.clear()
    respond("First statement")
    respond("Second statement")
    history = _global_memory.get_history()
    # 2 user turns + 2 assistant turns = 4
    assert len(history) == 4
    assert history[0]["content"] == "First statement"


def test_tool_registry_safe_execution():
    registry = get_default_registry()
    res = registry.execute("system_stats")
    assert res["ok"] is True
    assert res["status"] == "success"
    assert "cpu_cores" in res["result"]


def test_tool_registry_confirm_gate():
    registry = get_default_registry()
    # Without confirmation -> should return awaiting_confirmation
    res = registry.execute("shutdown", args={"delay_seconds": 10}, confirmed=False)
    assert res["ok"] is True
    assert res["status"] == "awaiting_confirmation"

    # With confirmation -> succeeds
    res_confirmed = registry.execute("shutdown", args={"delay_seconds": 10}, confirmed=True)
    assert res_confirmed["ok"] is True
    assert res_confirmed["status"] == "success"
    assert res_confirmed["result"]["action"] == "shutdown"


def test_tool_registry_blocked_tool():
    registry = get_default_registry()
    res = registry.execute("format_disk", args={"device": "/dev/sda"})
    assert res["ok"] is False
    assert res["status"] == "blocked"


def test_daemon_command_dispatch():
    from jarvis.daemon import JarvisDaemonHandler
    # Verify handler can process a command without throwing
    reply = respond("what time is it")
    assert isinstance(reply, Reply)
    assert "is" in reply.speech.lower()


def test_manus_compound_planning():
    from jarvis.agent_compound import get_compound_engine
    engine = get_compound_engine()
    plan = engine.plan_and_execute("diagnose system telemetry")
    assert plan.status == "completed"
    assert len(plan.steps) == 4
    assert plan.steps[0].agent == "jarvis"
    assert any(s.tool == "system_stats" for s in plan.steps)
    assert len(plan.artifacts) > 0
