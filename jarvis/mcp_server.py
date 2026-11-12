"""JARVIS MCP Server — Model Context Protocol bridge for OpenCode, Cline, and autonomous agents.

Exposes JARVIS tools, agent switching, telemetry, and 3D hologram control.
Compatible with standard MCP JSON-RPC 2.0 protocol over stdio.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from jarvis.brain import Reply, respond
from jarvis import keyvault
from jarvis.tools.globalfone import GlobalFoneCallTool
from jarvis.tools.system_stats import SystemStatsTool


def handle_initialize(req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "jarvis-workshop",
                "version": "2.0.0"
            }
        }
    }


def handle_tools_list(req_id: Any) -> Dict[str, Any]:
    tools = [
        {
            "name": "ask_jarvis",
            "description": "Send a question, doubt, or command to JARVIS. Uses daily refreshing OAuth tokens.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user query or command to evaluate"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "switch_agent",
            "description": "Switch active agent persona and HUD theme (JARVIS cyan, FRIDAY green safety, EDITH orange hardware, ULTRON red compute).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": ["jarvis", "friday", "edith", "ultron"],
                        "description": "Target agent name"
                    }
                },
                "required": ["agent"]
            }
        },
        {
            "name": "hologram_control",
            "description": "Control 3D hologram wireframe models in the workshop (suit, car, bike, explode, reset, clear).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["show_suit", "show_car", "show_bike", "explode", "reset", "clear"],
                        "description": "Hologram visual action"
                    }
                },
                "required": ["action"]
            }
        },
        {
            "name": "get_system_telemetry",
            "description": "Fetch real-time CPU, RAM, storage, and host metrics.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "set_api_key",
            "description": (
                "Store an AI provider API key in the local key vault (~/.jarvis/keys.json). "
                "Keys are never echoed back in full; only a masked preview is returned."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "gemini, openai, anthropic, opencode, globalfone, elevenlabs, twilio_sid, twilio_token"
                    },
                    "key": {
                        "type": "string",
                        "description": "The API key or token itself"
                    }
                },
                "required": ["provider", "key"]
            }
        },
        {
            "name": "list_api_keys",
            "description": "List every known provider with whether a key is configured, its source (env or file), and a masked preview.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "delete_api_key",
            "description": "Remove a stored API key from the local key vault.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "provider": {"type": "string", "description": "Provider name to clear"}
                },
                "required": ["provider"]
            }
        },
        {
            "name": "call_phone",
            "description": (
                "Place a real outbound phone call. Uses the GlobalFone gateway when configured, "
                "otherwise hands the number to the operating system dialer."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Phone number to dial"},
                    "provider": {
                        "type": "string",
                        "enum": ["auto", "globalfone", "dialer"],
                        "description": "auto tries GlobalFone first, then falls back"
                    }
                },
                "required": ["to"]
            }
        },
        {
            "name": "get_settings",
            "description": "Return all JARVIS settings (file + env overrides).",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "set_setting",
            "description": "Persist a JARVIS setting to ~/.jarvis/settings.json.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Setting key (e.g. voice, brain_provider, demo_number)"},
                    "value": {"type": "string", "description": "Setting value"}
                },
                "required": ["key", "value"]
            }
        },
        {
            "name": "webrtc_signal",
            "description": "Exchange WebRTC signaling SDP/ICE for a room so two browsers can peer-connect.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {"type": "string", "description": "Room name (default: 'default')"},
                    "peer": {"type": "string", "description": "Peer identifier"},
                    "sdp": {"type": "object", "description": "Session description to post"},
                    "candidate": {"type": "object", "description": "ICE candidate to post"},
                    "get_state": {"type": "boolean", "description": "Just read room state without posting"}
                },
                "required": ["room", "peer"]
            }
        },
        {
            "name": "webrtc_rooms",
            "description": "List active WebRTC signaling rooms.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "list_free_models",
            "description": (
                "List the verified free AI models served by the local 9Router gateway, "
                "including the default fallback chain and live availability."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "live": {
                        "type": "boolean",
                        "description": "Query the gateway for live availability (default true)"
                    }
                }
            }
        },
        {
            "name": "free_models_health",
            "description": (
                "Check the local AI gateway. With probe=true, send a real completion to "
                "every verified free model and report pass/fail with latency."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "probe": {
                        "type": "boolean",
                        "description": "Send a real completion per model (slower, default false)"
                    }
                }
            }
        },
        {
            "name": "ask_free_model",
            "description": (
                "Answer a prompt with a free model through the local 9Router gateway. "
                "Defaults to the free-auto fallback chain (deepseek -> glm -> mimo)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Question or instruction"},
                    "model": {
                        "type": "string",
                        "description": "Model id from list_free_models (default: free-auto)"
                    },
                    "system": {"type": "string", "description": "Optional system prompt"},
                    "max_tokens": {"type": "integer", "description": "Reply budget (default 512)"},
                    "temperature": {"type": "number", "description": "Sampling temperature (default 0.2)"}
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "list_voice_models",
            "description": (
                "List the free TTS and STT models JARVIS can use, with the default "
                "(best free) pick per direction and, with live=true, whether each "
                "engine's package is installed."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "live": {
                        "type": "boolean",
                        "description": "Check which engines are installed (default true)"
                    }
                }
            }
        },
        {
            "name": "speak_text",
            "description": (
                "Speak text out loud on the host with the free TTS engine "
                "(default edge-tts, offline piper/pyttsx3 fallbacks)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to say"},
                    "agent": {
                        "type": "string",
                        "enum": ["jarvis", "friday", "edith", "ultron"],
                        "description": "Voice persona (default jarvis)"
                    },
                    "model": {
                        "type": "string",
                        "description": "TTS model id from list_voice_models (default: edge-tts)"
                    }
                },
                "required": ["text"]
            }
        },
        {
            "name": "github_status",
            "description": (
                "Check the GitHub connection and show the authenticated account "
                "(token from GITHUB_TOKEN or the key vault 'github' entry)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "github_create_repo",
            "description": (
                "Create a GitHub repository for the authenticated user via the GitHub REST API. "
                "Returns the repo URL on success, or a clear error (e.g. name already exists)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name (e.g. JARVIS-OS)"},
                    "description": {"type": "string", "description": "Repository description"},
                    "private": {"type": "boolean", "description": "Create as private (default false)"},
                    "homepage": {"type": "string", "description": "Project homepage URL"},
                    "topics": {"type": "string", "description": "Comma-separated topic tags"}
                },
                "required": ["name"]
            }
        }
    ]
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": tools
        }
    }


def _text_result(req_id: Any, payload: Any) -> Dict[str, Any]:
    """Wrap any JSON-serialisable payload as a single MCP text content block."""
    if not isinstance(payload, str):
        payload = json.dumps(payload, indent=2, default=str)
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": payload}]},
    }


def handle_tools_call(req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments", {})

    if name == "ask_jarvis":
        query = args.get("query", "")
        reply: Reply = respond(query)
        result_text = reply.speech
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}]
            }
        }

    elif name == "switch_agent":
        agent = args.get("agent", "jarvis").lower()
        reply: Reply = respond(f"switch to {agent}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": reply.speech}]
            }
        }

    elif name == "hologram_control":
        action = args.get("action", "clear")
        action_map = {
            "show_suit": "show suit",
            "show_car": "show car",
            "show_bike": "show bike",
            "explode": "explode",
            "reset": "reset",
            "clear": "clear"
        }
        cmd = action_map.get(action, "clear")
        reply: Reply = respond(cmd)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": reply.speech}]
            }
        }

    elif name == "get_system_telemetry":
        tool = SystemStatsTool()
        stats = tool.run()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(stats, indent=2)}]
            }
        }

    elif name == "set_api_key":
        outcome = keyvault.set_key(str(args.get("provider", "")), str(args.get("key", "")))
        return _text_result(req_id, outcome)

    elif name == "list_api_keys":
        return _text_result(req_id, {"keys": keyvault.list_keys()})

    elif name == "delete_api_key":
        return _text_result(req_id, keyvault.delete_key(str(args.get("provider", ""))))

    elif name == "call_phone":
        outcome = GlobalFoneCallTool().run(
            to=str(args.get("to", "")),
            provider=str(args.get("provider", "auto")),
        )
        return _text_result(req_id, outcome)

    elif name == "get_settings":
        from jarvis.settings import all_settings
        return _text_result(req_id, {"settings": all_settings()})

    elif name == "set_setting":
        from jarvis.settings import set as set_setting, get as get_setting
        outcome = set_setting(str(args.get("key", "")), str(args.get("value", "")))
        if outcome.get("ok"):
            outcome["current"] = get_setting(str(args.get("key", "")))
        return _text_result(req_id, outcome)

    elif name == "webrtc_signal":
        from jarvis.webrtc import signal_room
        outcome = signal_room(
            str(args.get("room", "default")),
            str(args.get("peer", "unknown")),
            sdp=args.get("sdp"),
            candidate=args.get("candidate"),
            get_state=bool(args.get("get_state", False)),
        )
        return _text_result(req_id, outcome)

    elif name == "webrtc_rooms":
        from jarvis.webrtc import list_rooms
        return _text_result(req_id, list_rooms())

    elif name == "list_free_models":
        from jarvis.free_models import list_free_models
        live = args.get("live", True)
        return _text_result(req_id, list_free_models(live=bool(live)))

    elif name == "free_models_health":
        from jarvis.free_models import health
        return _text_result(req_id, health(probe=bool(args.get("probe", False))))

    elif name == "ask_free_model":
        from jarvis.free_models import ask_free_model
        kwargs: Dict[str, Any] = {"prompt": str(args.get("prompt", ""))}
        if args.get("model"):
            kwargs["model"] = str(args["model"])
        if args.get("system"):
            kwargs["system"] = str(args["system"])
        if args.get("max_tokens") is not None:
            kwargs["max_tokens"] = int(args["max_tokens"])
        if args.get("temperature") is not None:
            kwargs["temperature"] = float(args["temperature"])
        return _text_result(req_id, ask_free_model(**kwargs))

    elif name == "list_voice_models":
        from jarvis.voice_models import list_voice_models
        return _text_result(req_id, list_voice_models(live=bool(args.get("live", True))))

    elif name == "speak_text":
        from jarvis import tts
        from jarvis.voice_models import get_tts, voice_for

        text = str(args.get("text", "")).strip()
        if not text:
            return _text_result(req_id, {"ok": False, "error": "text is required"})
        model = str(args.get("model") or "")
        agent = str(args.get("agent", "jarvis")).lower()
        try:
            voice = voice_for(agent, model or None)
        except ValueError as exc:
            return _text_result(req_id, {"ok": False, "error": str(exc)})
        outcome = tts.synthesize(text, voice=voice, model=model or None, agent=agent)
        if not outcome.get("ok"):
            return _text_result(req_id, {"ok": False, "error": outcome.get("error")})
        played = tts.speak(text, voice=voice, model=outcome.get("model"))
        return _text_result(req_id, {
            "ok": True,
            "spoken": played,
            "model": outcome.get("model"),
            "mime": outcome.get("mime"),
            "bytes": len(outcome.get("audio") or b""),
            "voice": voice or get_tts(outcome.get("model")).get("voices", {}).get(agent),
        })

    elif name == "github_status":
        from jarvis import github
        user = github.authenticated_user()
        if "__error__" in user or "__http_error__" in user:
            return _text_result(req_id, {"ok": False, "error": user.get("__error__") or user.get("__body__") or "GitHub API error"})
        body = user.get("body") or {}
        return _text_result(req_id, {
            "ok": True,
            "login": body.get("login"),
            "name": body.get("name"),
            "public_repos": body.get("public_repos"),
        })

    elif name == "github_create_repo":
        from jarvis import github
        name = str(args.get("name", "")).strip()
        if not name:
            return _text_result(req_id, {"ok": False, "error": "name is required"})
        topics = None
        if args.get("topics"):
            topics = [t.strip() for t in str(args["topics"]).split(",") if t.strip()]
        result = github.create_repo(
            name=name,
            description=str(args.get("description", "")),
            private=bool(args.get("private", False)),
            homepage=str(args.get("homepage", "")),
            topics=topics,
        )
        return _text_result(req_id, result)

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {name}"
        }
    }


def run_stdio() -> None:
    """Run JSON-RPC loop over stdin / stdout."""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            method = req.get("method")
            req_id = req.get("id")
            params = req.get("params", {})

            if method == "initialize":
                resp = handle_initialize(req_id, params)
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                resp = handle_tools_list(req_id)
            elif method == "tools/call":
                resp = handle_tools_call(req_id, params)
            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not supported: {method}"
                    }
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()
