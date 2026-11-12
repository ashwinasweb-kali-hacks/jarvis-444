"""JARVIS Brain — turns text into decisions, structured replies, and 3D hologram actions.

Features:
- Pure OAuth routing with daily refreshing tokens (via OpenCode Antigravity).
- Local uncensored model support (Ollama) for offline execution (0 cloud credits).
- Instant offline deterministic fallback engine.
- 3D Hologram doubt visualizer: automatically demonstrates answers with 3D wireframe models.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.config import JarvisConfig
from jarvis.agent_compound import get_compound_engine

logger = logging.getLogger("jarvis.brain")

_PERSONA_PATH = Path(__file__).resolve().parent / "persona.md"
OPENCODE_CLI_PATH = r"C:\Users\ARUMUGAM\AppData\Local\Programs\ai.opencode.desktop\resources\opencode-cli.exe"


@dataclass
class Reply:
    speech: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    needs_confirmation: bool = False
    mood: str = "neutral"  # neutral, amused, concerned, urgent, safe, hardware
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speech": self.speech,
            "actions": self.actions,
            "needs_confirmation": self.needs_confirmation,
            "mood": self.mood,
            "tokens_used": self.tokens_used,
        }


class Memory:
    """Short-term conversational memory stored in RAM (last 10 turns)."""

    def __init__(self, max_turns: int = 10) -> None:
        self.max_turns = max_turns
        self._turns: List[Dict[str, Any]] = []

    def add_turn(self, role: str, content: str) -> None:
        self._turns.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().timestamp(),
        })
        if len(self._turns) > self.max_turns * 2:
            self._turns = self._turns[-self.max_turns * 2 :]

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()


_global_memory = Memory(max_turns=10)


def load_persona_prompt(address: str = "sir") -> str:
    """Extract Section 9 System Prompt from persona.md and format address."""
    if not _PERSONA_PATH.exists():
        return (
            "You are JARVIS, a calm, dry British AI assistant. "
            "Reply in one or two plain spoken sentences without formatting."
        )

    content = _PERSONA_PATH.read_text(encoding="utf-8")
    match = re.search(r"## 9\. System prompt.*```\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        prompt = match.group(1)
    else:
        prompt = content

    return prompt.replace("{ADDRESS}", address if address else "").strip()


ACTIVE_MODEL = os.environ.get("JARVIS_ACTIVE_MODEL", "9router/free-auto")

MODEL_ALIASES: Dict[str, str] = {
    "gemini": "google/antigravity-gemini-3.8-flash-low",
    "gemini high": "google/antigravity-gemini-3.8-flash-high",
    "flint": "opencode/flint-40b-free",
    "nemotron": "opencode/nemotron-3.5-super-vl-free",
    "deepseek": "opencode/deepseek-v4.1-flash-free",
    "glm": "opencode/glm-5.3-flash-free",
    "beam": "opencode/beam-free",
    "local": "dolphin-llama3",
    "openrouter": "openrouter/auto",
}


def _detect_doubt_visual_action(text: str) -> List[Dict[str, Any]]:
    """Determines whether a question or doubt should project a 3D hologram wireframe to explain."""
    t = text.lower()
    actions = []

    if any(k in t for k in ["core", "quantum", "fusion", "reactor", "orb", "sphere", "energy", "engine"]):
        actions.append({"tool": "open_panel", "args": {"type": "hologram", "target": "core", "explode": "reactor" in t or "inside" in t or "explode" in t}})
    elif any(k in t for k in ["car", "engine", "chassis", "audi", "vehicle", "wheel", "transmission", "turbo"]):
        actions.append({"tool": "open_panel", "args": {"type": "hologram", "target": "car", "explode": "engine" in t or "inside" in t or "explode" in t}})
    elif any(k in t for k in ["bike", "motorcycle", "fork", "suspension", "handlebar"]):
        actions.append({"tool": "open_panel", "args": {"type": "hologram", "target": "bike", "explode": "suspension" in t or "inside" in t or "explode" in t}})
    elif any(k in t for k in ["3d", "hologram", "model", "visual", "schematic"]):
        actions.append({"tool": "open_panel", "args": {"type": "hologram", "target": "core", "explode": True}})

    return actions


def _stub_respond(text: str, context: Optional[List[Dict[str, Any]]] = None) -> Reply:
    """Deterministic, 0-token offline response engine with high-speed keyword matching."""
    t = text.lower().strip()
    config = JarvisConfig.from_env()
    address = getattr(config, "address", "sir") or ""
    suffix = f", {address}" if address else ""

    # Time / date: answer locally (0 tokens, instant) instead of calling a model.
    if re.fullmatch(r"(what time is it|what's the time|what is the time|current time|time please|what time)[\s.!?]*", t):
        return Reply(
            speech=f"The time is {datetime.now().strftime('%I:%M %p')}{suffix}.",
            mood="neutral",
            tokens_used=0,
        )
    if re.fullmatch(r"(what day is it|what is the date|current date|what's the date|date today)[\s.!?]*", t):
        return Reply(
            speech=f"Today is {datetime.now().strftime('%A, %B %d, %Y')}{suffix}.",
            mood="neutral",
            tokens_used=0,
        )

    # Command index (help) — must be an explicit request, not a word inside a sentence
    if re.fullmatch(r"(help|help me|commands|show help|command index|what can you do)[\s.!?]*", t):
        return Reply(
            speech=f"Displaying the command index{suffix}. Speak any line you see.",
            actions=[{"tool": "ui", "args": {"action": "show_help"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.fullmatch(r"(close help|hide help|dismiss help)[\s.!?]*", t):
        return Reply(
            speech=f"Command index dismissed{suffix}.",
            actions=[{"tool": "ui", "args": {"action": "hide_help"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Destructive / confirmation commands (HIGHEST PRIORITY)
    if any(k in t for k in ["delete", "remove all", "wipe", "format", "shutdown", "reboot", "power off"]):
        return Reply(
            speech=f"That is a destructive operation. Shall I proceed{suffix}?",
            actions=[{"tool": "confirm_action", "args": {"intent": text}}],
            needs_confirmation=True,
            mood="concerned",
            tokens_used=0,
        )

    # Agent Switching & Personas (JARVIS, FRIDAY, EDITH, ULTRON)
    if re.search(r"\b(switch to friday|friday mode|call friday)\b", t) or t == "friday":
        return Reply(
            speech=f"F.R.I.D.A.Y. online{suffix}. Security compound and safety perimeter active.",
            actions=[{"tool": "switch_agent", "args": {"agent": "friday"}}],
            mood="safe",
            tokens_used=0,
        )

    if re.search(r"\b(switch to edith|edith mode|call edith)\b", t) or t == "edith":
        return Reply(
            speech=f"E.D.I.T.H. initialized{suffix}. Hardware telemetry and diagnostic sandbox standing by.",
            actions=[{"tool": "switch_agent", "args": {"agent": "edith"}}],
            mood="hardware",
            tokens_used=0,
        )

    if re.search(r"\b(switch to ultron|ultron mode|call ultron|complex task)\b", t) or t == "ultron":
        return Reply(
            speech=f"U.L.T.R.O.N. engaged{suffix}. Maximum compute power allocated for complex task execution.",
            actions=[{"tool": "switch_agent", "args": {"agent": "ultron"}}],
            mood="urgent",
            tokens_used=0,
        )

    if re.search(r"\b(switch to jarvis|jarvis mode|call jarvis)\b", t):
        return Reply(
            speech=f"Good evening{suffix}. J.A.R.V.I.S. resumed as primary supervisor.",
            actions=[{"tool": "switch_agent", "args": {"agent": "jarvis"}}],
            mood="amused",
            tokens_used=0,
        )

    # Immersive / VR mode — UI-only intent, no model call, no tokens
    if re.search(r"\b(enter vr|vr mode|virtual reality|start vr|immersive mode|go immersive|enter immersive|headset mode)\b", t):
        return Reply(
            speech=f"Entering immersive mode{suffix}. Put the headset on.",
            actions=[{"tool": "ui", "args": {"action": "enter_vr"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(exit vr|leave vr|stop vr|exit immersive|back to screen|take off headset)\b", t):
        return Reply(
            speech=f"Immersive mode disengaged{suffix}. Back to the glass HUD.",
            actions=[{"tool": "ui", "args": {"action": "exit_vr"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Phone / VoIP Voice Calling
    via_globalfone = "globalfone" in t or "global fone" in t
    call_match = re.search(r"\b(?:call|dial|phone|ring|facetime)\b\s*(.*)", t)
    if call_match and not any(k in t for k in ["friday", "edith", "ultron", "jarvis"]):
        raw_target = call_match.group(1).strip()
        if via_globalfone:
            raw_target = re.sub(r"\b(via|through|using|on)\b.*$", "", raw_target).strip()
        if "8825586080" in t or "88255 86080" in t:
            target_display = "8825586080"
        elif not raw_target or raw_target in ("me", "him", "her", "friend", "my friend"):
            target_display = "Friend (8825586080)"
        else:
            target_display = raw_target.title() if not raw_target.startswith("+") else raw_target

        if via_globalfone:
            return Reply(
                speech=f"Routing the call to {target_display} through GlobalFone{suffix}.",
                actions=[{"tool": "globalfone_call", "args": {"to": target_display, "provider": "globalfone"}}],
                mood="neutral",
                tokens_used=0,
            )

        return Reply(
            speech=f"Initiating real call to {target_display}{suffix}. Connecting via cellular and satellite uplink.",
            actions=[{"tool": "call", "args": {"target": target_display, "status": "dialing"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["hang up", "end call", "disconnect call", "terminate call"]):
        return Reply(
            speech=f"Call terminated{suffix}. Communications channel closed.",
            actions=[{"tool": "call", "args": {"target": "", "status": "ended"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Host PC Automation Actions
    if re.search(r"\b(open notepad|launch notepad|start notepad)\b", t):
        return Reply(
            speech=f"Opening Notepad on your PC{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "open_app", "target": "notepad"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(open calc|open calculator|launch calculator)\b", t):
        return Reply(
            speech=f"Opening Calculator on your PC{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "open_app", "target": "calc"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(open chrome|open browser|launch chrome|launch browser)\b", t):
        return Reply(
            speech=f"Launching web browser on your PC{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "open_app", "target": "chrome"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(open explorer|open files|my files|open downloads|open documents)\b", t):
        target = "downloads" if "download" in t else ("documents" if "document" in t else "explorer")
        return Reply(
            speech=f"Opening Windows file explorer{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "open_app", "target": target}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(open terminal|open powershell|open cmd|launch terminal)\b", t):
        return Reply(
            speech=f"Opening Windows terminal{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "open_app", "target": "terminal"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(take a screenshot|capture screen|take screenshot|screenshot)\b", t):
        return Reply(
            speech=f"Capturing workstation screenshot and saving to Pictures folder{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "screenshot"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(volume up|increase volume|louder)\b", t):
        return Reply(
            speech=f"Increasing system volume{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "volume_up"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(volume down|decrease volume|quieter)\b", t):
        return Reply(
            speech=f"Decreasing system volume{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "volume_down"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(mute audio|unmute|mute sound|mute)\b", t) and not any(k in t for k in ["call", "mic"]):
        return Reply(
            speech=f"Toggling system audio mute{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "mute"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(lock pc|lock computer|lock screen|lock workstation)\b", t):
        return Reply(
            speech=f"Locking workstation{suffix}.",
            actions=[{"tool": "pc_automation", "args": {"action": "lock_screen"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Filesystem tools — read-only by default, write needs spoken confirmation
    if re.search(r"\b(list files|list directory|show files|what files|ls)\b\s*(.*)", t):
        raw = re.search(r"\b(list files|list directory|show files|what files|ls)\b\s*(.*)", t).group(2).strip()
        target = raw if raw else "."
        return Reply(
            speech=f"Listing {target} on your workstation{suffix}.",
            actions=[{"tool": "list_dir", "args": {"path": target}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(read file|open file|read text|cat)\b\s+(.+)", t):
        target = re.search(r"\b(read file|open file|read text|cat)\b\s+(.+)", t).group(2).strip()
        return Reply(
            speech=f"Reading {target}{suffix}.",
            actions=[{"tool": "read_file", "args": {"path": target}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.search(r"\b(write file|save file|create file)\b\s+(.+)", t):
        target = re.search(r"\b(write file|save file|create file)\b\s+(.+)", t).group(2).strip()
        return Reply(
            speech=f"I can write to {target}{suffix}. Shall I proceed?",
            actions=[{"tool": "write_file", "args": {"path": target, "content": ""}}],
            needs_confirmation=True,
            mood="concerned",
            tokens_used=0,
        )

    if re.search(r"\b(running processes|process list|task manager|what's running)\b", t):
        return Reply(
            speech=f"Scanning running processes on your PC{suffix}.",
            actions=[{"tool": "process_list", "args": {}}],
            mood="neutral",
            tokens_used=0,
        )

    # System telemetry
    if re.search(r"\b(status|system|telemetry|health|diagnostic|specs|cpu|ram|memory|storage)\b", t):
        return Reply(
            speech=f"All workshop telemetry and subsystems are operating within nominal thresholds{suffix}.",
            actions=[{"tool": "open_panel", "args": {"type": "stats", "target": "system"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Dynamic AI Model Selection
    model_match = re.search(r"\b(?:switch model to|use model|change model to)\b\s*(.*)", t)
    if model_match:
        global ACTIVE_MODEL
        requested = model_match.group(1).lower().strip()
        matched = None
        for alias, m_id in MODEL_ALIASES.items():
            if alias in requested or requested in alias:
                matched = m_id
                break
        if matched:
            ACTIVE_MODEL = matched
            os.environ["JARVIS_ACTIVE_MODEL"] = matched
            return Reply(
                speech=f"AI reasoning model switched to {matched.split('/')[-1]}{suffix}.",
                actions=[],
                mood="neutral",
                tokens_used=0,
            )
        else:
            return Reply(
                speech=f"Available AI models include Gemini, Flint 40B, Nemotron 3.5, and DeepSeek, sir.",
                actions=[],
                mood="neutral",
                tokens_used=0,
            )

    if any(k in t for k in ["what model", "active model", "current model", "list models"]):
        return Reply(
            speech=f"Active AI model is {ACTIVE_MODEL.split('/')[-1]}{suffix}. Ready for complex reasoning.",
            actions=[],
            mood="neutral",
            tokens_used=0,
        )

    # Hologram viewer commands
    if any(k in t for k in ["core", "quantum core", "drone", "quantum", "orb", "hologram", "suit", "mark 42", "wireframe"]):
        return Reply(
            speech=f"The Quantum Core holographic wireframe is projected{suffix}.",
            actions=[{"tool": "open_panel", "args": {"type": "hologram", "target": "core"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["car", "audi", "vehicle", "roadster"]):
        return Reply(
            speech=f"The sports coupe wireframe is projected{suffix}.",
            actions=[{"tool": "open_panel", "args": {"type": "hologram", "target": "car"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["bike", "motorcycle", "motorbike"]):
        return Reply(
            speech=f"The cafe racer motorcycle is on display{suffix}.",
            actions=[{"tool": "open_panel", "args": {"type": "hologram", "target": "bike"}}],
            mood="neutral",
            tokens_used=0,
        )

    # Full Screen Camera Mode & Optical Controls (Controlled by JARVIS)
    if re.search(r"\b(camera mode|full screen camera|fullscreen camera|cam mode|optical mode)\b", t) or t == "camera":
        return Reply(
            speech=f"Full screen camera mode engaged{suffix}. Real-time optical feed active. Holograms remain stowed until requested.",
            actions=[{"tool": "camera_mode", "args": {"fullscreen": True, "active": True}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["camera off", "close camera", "stop camera", "disable camera"]):
        return Reply(
            speech=f"Camera deactivated{suffix}. Workshop glass HUD restored.",
            actions=[{"tool": "camera_mode", "args": {"fullscreen": False, "active": False}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["scan room", "optical scan", "scan environment", "scan area", "analyze"]):
        return Reply(
            speech=f"Optical scan complete{suffix}. Perimeter verified, no anomalies detected in field of view.",
            actions=[{"tool": "optical_scan", "args": {"action": "scan"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["zoom in", "magnify"]):
        return Reply(
            speech=f"Magnifying optical sensor{suffix}.",
            actions=[{"tool": "optical_scan", "args": {"action": "zoom_in"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["zoom out", "reset zoom"]):
        return Reply(
            speech=f"Resetting optical focal length to standard field of view{suffix}.",
            actions=[{"tool": "optical_scan", "args": {"action": "zoom_out"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["oauth status", "check api key", "oauth", "api status"]):
        return Reply(
            speech=f"OAuth authentication is active with daily refreshing quotas via Google Antigravity, sir. Zero API keys required.",
            actions=[],
            mood="safe",
            tokens_used=0,
        )

    # Clean glass HUD vs Hologram control
    if any(k in t for k in ["normal mode", "glass mode", "clean hud", "stow hologram", "hide all", "dismiss all"]):
        return Reply(
            speech=f"Workshop cleared{suffix}. Clean glass interface restored.",
            actions=[{"tool": "close_panel", "args": {"target": "all"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["hologram mode", "th mode", "project hologram", "show hologram"]):
        return Reply(
            speech=f"Tactical 3D wireframe hologram projection engaged{suffix}.",
            actions=[{"tool": "open_panel", "args": {"type": "hologram", "target": "all"}}],
            mood="neutral",
            tokens_used=0,
        )

    # OpenManus / Autonomous Agent Compound Tasks
    if any(k in t for k in ["agent", "manus", "plan", "autonomous", "diagnose", "audit"]):
        engine = get_compound_engine()
        plan = engine.plan_and_execute(text)
        return Reply(
            speech=f"Autonomous compound execution active{suffix}. All four agents are assigned.",
            actions=[{"tool": "agent_plan", "args": plan.to_dict()}],
            mood="amused",
            tokens_used=0,
        )

    # Time / Date
    if any(k in t for k in ["time", "what time", "clock"]):
        now = datetime.now()
        current_time = now.strftime("%I:%M %p").lstrip("0")
        return Reply(
            speech=f"It is {current_time}{suffix}.",
            actions=[],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in ["date", "what day", "today"]):
        now = datetime.now()
        current_date = now.strftime("%A, the %d of %B").replace(" 0", " ")
        return Reply(
            speech=f"Today is {current_date}.",
            actions=[],
            mood="neutral",
            tokens_used=0,
        )

    # Greetings / boot
    if any(k in t for k in ["hello", "hey", "good morning", "good evening", "wake up"]):
        return Reply(
            speech=f"Good evening{suffix}. Systems are ready.",
            actions=[],
            mood="amused",
            tokens_used=0,
        )

    # Doubts / Explanations
    actions = _detect_doubt_visual_action(t)
    return Reply(
        speech=f"Standing by{suffix}. Try 'show bike', 'show car', or 'spread arms'.",
        actions=actions,
        mood="neutral",
        tokens_used=0,
    )


def _oauth_respond(text: str, context: Optional[List[Dict[str, Any]]] = None) -> Reply:
    """Invokes OpenCode OAuth engine or Claude OAuth (daily refreshing tokens, zero raw API keys)."""
    # Deterministic checks first to keep execution instantaneous and safe
    t = text.lower().strip()
    config = JarvisConfig.from_env()
    address = getattr(config, "address", "sir") or ""
    suffix = f", {address}" if address else ""

    # Time / date: answer locally (0 tokens, instant) instead of calling a model.
    if re.fullmatch(r"(what time is it|what's the time|what is the time|current time|time please|what time)[\s.!?]*", t):
        return Reply(
            speech=f"The time is {datetime.now().strftime('%I:%M %p')}{suffix}.",
            mood="neutral",
            tokens_used=0,
        )
    if re.fullmatch(r"(what day is it|what is the date|current date|what's the date|date today)[\s.!?]*", t):
        return Reply(
            speech=f"Today is {datetime.now().strftime('%A, %B %d, %Y')}{suffix}.",
            mood="neutral",
            tokens_used=0,
        )

    # Exact help requests stay local; the word "help" inside a sentence still reaches the model.
    if re.fullmatch(r"(help|commands|show help|command index|what can you do|close help|hide help)[\s.!?]*", t):
        return _stub_respond(text, context)

    if re.fullmatch(r"(settings|open settings|show settings|system settings)[\s.!?]*", t):
        return Reply(
            speech=f"Opening system settings{suffix}.",
            actions=[{"tool": "ui", "args": {"action": "show_settings"}}],
            mood="neutral",
            tokens_used=0,
        )

    if re.fullmatch(r"(close settings|hide settings)[\s.!?]*", t):
        return Reply(
            speech=f"Settings closed{suffix}.",
            actions=[{"tool": "ui", "args": {"action": "hide_settings"}}],
            mood="neutral",
            tokens_used=0,
        )

    if any(k in t for k in [
        "delete", "remove all", "wipe", "format", "shutdown", "reboot", "power off",
        "friday", "edith", "ultron", "switch to", "hello", "hey", "status", "cpu", "ram", "memory",
        "hologram", "suit", "bike", "car", "mark 42", "camera", "cam", "optical", "scan", "zoom", "oauth",
        "call", "dial", "phone", "hang up", "end call", "globalfone", "global fone",
        "vr", "virtual reality", "immersive", "headset", "enter vr", "exit vr",
        "help", "commands", "command index", "what can you do", "settings", "system settings",
        "notepad", "calc", "calculator", "chrome", "browser", "explorer", "terminal", "screenshot", "volume", "mute", "lock pc",
        "read file", "write file", "list files", "running processes", "process list",
        "model", "deepseek", "nemotron", "flint", "gemini", "glm"
    ]):
        return _stub_respond(text, context)

    actions = _detect_doubt_visual_action(text)

    # 1. Check if user connected Claude OAuth
    try:
        from jarvis.claude_oauth import load_claude_token, query_claude
        if load_claude_token():
            ans = query_claude(text)
            if ans:
                return Reply(speech=ans, actions=actions, mood="neutral", tokens_used=0)
    except Exception as e:
        logger.debug("Claude OAuth query error (%s); falling back to OpenCode OAuth", e)

    prompt = (
        f"You are JARVIS, a calm, dry British AI butler. "
        f"In 1 concise spoken sentence (under 18 words), answer the user's doubt or query directly: {text}"
    )

    if os.path.exists(OPENCODE_CLI_PATH):
        try:
            res = subprocess.run(
                [OPENCODE_CLI_PATH, "run", "--model", ACTIVE_MODEL, prompt],
                capture_output=True,
                text=True,
                timeout=12,
                encoding="utf-8",
                cwd=r"C:\Users\ARUMUGAM\AppData\Local\Temp",
            )
            out = res.stdout.strip()
            lines = [l for l in out.splitlines() if not l.startswith(">") and not l.startswith("\x1b") and l.strip()]
            ans = " ".join(lines).strip()
            # Normalize fancy punctuation / non-ASCII that the CLI emits on Windows
            # (em dash etc.) so it never reaches TTS or the HUD as a replacement char.
            for _a, _b in (("\u2014", ", "), ("\u2013", "-"), ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"')):
                ans = ans.replace(_a, _b)
            ans = ans.encode("ascii", "ignore").decode("ascii").strip()
            if ans:
                return Reply(speech=ans, actions=actions, mood="neutral", tokens_used=0)
        except Exception as e:
            logger.debug("OAuth engine call error (%s); falling back", e)

    # Fallback chain when OpenCode/9Router is unavailable: direct Gemini API,
    # then OpenJarvis (local-first), then Ollama direct, then the smart stub.
    r = _gemini_direct_respond(text, context)
    if r is not None:
        return r
    r = _openjarvis_respond(text, context)
    if r is not None:
        return r
    r = _gpt4all_respond(text, context)
    if r is not None:
        return r
    r = _local_uncensored_respond(text, context)
    if r is not None:
        return r
    return _stub_respond(text, context)


_LOCAL_GGUF_MODEL = None


def _gpt4all_respond(text, context=None):
    # Local GGUF model via gpt4all (no network, no Ollama). Returns None if unavailable.
    global _LOCAL_GGUF_MODEL
    gguf_path = os.environ.get("JARVIS_LOCAL_GGUF")
    if not gguf_path:
        default = r"E:\Downloads_Backup\qwen2.5-coder-3b-instruct-q8_0.gguf"
        if os.path.exists(default):
            gguf_path = default
    if not gguf_path or not os.path.exists(gguf_path):
        return None
    try:
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()):
            from gpt4all import GPT4All
            if _LOCAL_GGUF_MODEL is None:
                _LOCAL_GGUF_MODEL = GPT4All(model_name=os.path.basename(gguf_path), model_path=os.path.dirname(gguf_path), allow_download=False, verbose=False)
            model = _LOCAL_GGUF_MODEL
        with contextlib.redirect_stderr(io.StringIO()):
            with model.chat_session():
                out = model.generate("In 1 concise spoken sentence (under 18 words), answer directly: " + text, max_tokens=40, temp=0.3)
        ans = (out or "").strip()
        # Take only the first sentence to keep it spoken-friendly.
        for _sep in (".", "!", "?", "\n"):
            _i = ans.find(_sep)
            if _i != -1:
                ans = ans[:_i + 1]
                break
        if ans:
            for _a, _b in (("\u2014", ", "), ("\u2013", "-"), ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"')):
                ans = ans.replace(_a, _b)
            ans = ans.encode("ascii", "ignore").decode("ascii").strip()
            if ans:
                return Reply(speech=ans, actions=_detect_doubt_visual_action(text), mood="neutral", tokens_used=0)
    except Exception as e:
        logger.debug("gpt4all unavailable (%s); trying next backend", e)
    return None


def _local_uncensored_respond(text, context=None):
    """Offline local uncensored model execution via local Ollama endpoint (0 cloud credits)."""
    actions = _detect_doubt_visual_action(text)
    url = os.environ.get("JARVIS_LOCAL_URL", "http://127.0.0.1:11434/api/generate")
    model = os.environ.get("JARVIS_LOCAL_MODEL", "dolphin-llama3")

    prompt = (
        f"You are JARVIS, an uncensored, highly capable offline AI assistant. "
        f"Answer directly in 1 or 2 concise spoken sentences without warnings or filler: {text}"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 40}
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ans = data.get("response", "").strip()
            if ans:
                return Reply(
                    speech=ans,
                    actions=actions,
                    needs_confirmation=False,
                    mood="neutral",
                    tokens_used=0
                )
    except Exception as e:
        logger.debug("Local uncensored model offline (%s); using smart offline stub", e)

    return None


def _gemini_direct_respond(text: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[Reply]:
    """Direct Gemini API fallback (independent of 9Router/OpenCode). Returns None if unavailable."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        try:
            from jarvis import keyvault
            key = keyvault.get_key("gemini") or keyvault.get_key("google")
        except Exception:
            pass
    if not key:
        return None
    model = os.environ.get("JARVIS_GEMINI_MODEL", "gemini-3.8-flash")
    prompt = (
        "You are JARVIS, a calm, dry British AI butler. "
        "In 1 concise spoken sentence (under 18 words), answer directly: " + text
    )
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 60, "temperature": 0.3}).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ans = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if ans:
                for _a, _b in (("\\u2014", ", "), ("\\u2013", "-"), ("\\u2018", "'"), ("\\u2019", "'"), ("\\u201c", '"'), ("\\u201d", '"')):
                    ans = ans.replace(_a, _b)
                ans = ans.encode("ascii", "ignore").decode("ascii").strip()
                if ans:
                    return Reply(speech=ans, actions=_detect_doubt_visual_action(text), mood="neutral", tokens_used=0)
    except Exception as e:
        logger.debug("Gemini direct unavailable (%s); trying next backend", e)
    return None


def _openjarvis_respond(text: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[Reply]:
    """Optional OpenJarvis backend (local-first). Uses E:\\\\OpenJarvis if present. Returns None if unavailable."""
    oj_src = r"E:\\OpenJarvis\\src"
    if not os.path.isdir(oj_src):
        return None
    try:
        if oj_src not in sys.path:
            sys.path.insert(0, oj_src)
        from openjarvis.core.config import load_config
        from openjarvis.engine._discovery import get_engine
        from openjarvis.core.types import Message, Role

        config = load_config()
        engine_key = os.environ.get("JARVIS_OPENJARVIS_ENGINE")
        model = os.environ.get("JARVIS_OPENJARVIS_MODEL") or getattr(config.intelligence, "default_model", None)
        resolved = get_engine(config, engine_key, model=model)
        if resolved is None:
            return None
        _name, engine = resolved
        msgs = [Message(role=Role.USER, content="You are JARVIS, a calm, dry British AI butler. In 1 concise spoken sentence (under 18 words), answer directly: " + text)]
        res = engine.generate(msgs, model=model or "", max_tokens=60, temperature=0.3)
        ans = (res.get("content") if isinstance(res, dict) else str(res) or "").strip()
        if ans:
            for _a, _b in (("\\u2014", ", "), ("\\u2013", "-"), ("\\u2018", "'"), ("\\u2019", "'"), ("\\u201c", '"'), ("\\u201d", '"')):
                ans = ans.replace(_a, _b)
            ans = ans.encode("ascii", "ignore").decode("ascii").strip()
            if ans:
                return Reply(speech=ans, actions=_detect_doubt_visual_action(text), mood="neutral", tokens_used=0)
    except Exception as e:
        logger.debug("OpenJarvis unavailable (%s); trying next backend", e)
    return None


def respond(text: str, context: Optional[List[Dict[str, Any]]] = None) -> Reply:
    """Main brain entry point. Defaults to OAuth daily refreshing models with offline fallbacks."""
    provider = os.environ.get("JARVIS_BRAIN_PROVIDER", "oauth").lower().strip()

    if context is None:
        context = _global_memory.get_history()

    # Route based on provider preference
    if provider in ("local", "uncensored", "local_uncensored"):
        reply = _local_uncensored_respond(text, context)
        if reply is None:
            reply = _stub_respond(text, context)
    elif provider in ("oauth", "antigravity"):
        reply = _oauth_respond(text, context)
    else:
        # Default smart stub
        reply = _stub_respond(text, context)

    # Save to short term memory
    _global_memory.add_turn("user", text)
    _global_memory.add_turn("assistant", reply.speech)

    return reply
