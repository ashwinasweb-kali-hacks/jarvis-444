"""Free-model access for JARVIS and MCP clients.

Only models that were actually verified against the local 9Router gateway are
listed here. The catalog is deliberately small: the gateway advertises hundreds
of model IDs, but every provider except the OpenCode Free lane needs an account,
so declaring them would just produce authentication errors.

Configuration (environment wins):

- ``JARVIS_GATEWAY_URL``   default ``http://127.0.0.1:20128``
- ``NINE_ROUTER_API_KEY``  local gateway key (also read from the key vault)
- ``JARVIS_GATEWAY_KEY_FILE`` optional path to the key file

Nothing here writes secrets to disk or returns a key to the caller.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis import keyvault

DEFAULT_BASE = "http://127.0.0.1:20128"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY_FILE = REPO_ROOT / "gateway" / ".9router-key"

# Verified with gateway/probe-free.js (max_tokens 64). ``default`` marks the
# model a client should pick when it has no preference.
FREE_MODEL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "free-auto",
        "label": "Free Auto",
        "kind": "combo",
        "default": True,
        "chain": [
            "oc/deepseek-v4.1-flash-free",
            "oc/glm-5.3-flash-free",
            "oc/mimo-v2.6-flash-free",
        ],
        "notes": "Falls through deepseek -> glm -> mimo on failure.",
    },
    {
        "id": "oc/deepseek-v4.1-flash-free",
        "label": "DeepSeek V4.1 Flash",
        "kind": "model",
        "default": False,
        "notes": "Fastest verified model (~1.3 s).",
    },
    {
        "id": "oc/glm-5.3-flash-free",
        "label": "GLM 5.3 Flash",
        "kind": "model",
        "default": False,
        "notes": "Verified (~1.4 s).",
    },
    {
        "id": "oc/mimo-v2.6-flash-free",
        "label": "MiMo v2.6 Flash",
        "kind": "model",
        "default": False,
        "notes": "Verified (~2.7 s); needs a normal token budget.",
    },
    {
        "id": "oc/big-pickle",
        "label": "Big Pickle",
        "kind": "model",
        "default": False,
        "notes": "Passes but ~39 s cold start; not in the default chain.",
    },
    {
        "id": "groq/openai/gpt-oss-120b",
        "label": "GPT-OSS 120B (Groq)",
        "kind": "model",
        "default": False,
        "notes": "Verified working via Groq free tier; reasoning model, needs max_tokens>=128.",
    },
]

DEFAULT_MODEL = next(m["id"] for m in FREE_MODEL_CATALOG if m.get("default"))


def gateway_url() -> str:
    return (os.environ.get("JARVIS_GATEWAY_URL") or DEFAULT_BASE).rstrip("/")


def _key_file() -> Path:
    override = os.environ.get("JARVIS_GATEWAY_KEY_FILE")
    return Path(override) if override else DEFAULT_KEY_FILE


def api_key() -> Optional[str]:
    """Resolve the gateway key without ever logging it."""
    from_env = os.environ.get("NINE_ROUTER_API_KEY")
    if from_env:
        return from_env.strip()
    stored = keyvault.get_key("nine_router")
    if stored:
        return stored.strip()
    try:
        path = _key_file()
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


def _request_json(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Single HTTP entry point so tests can patch it."""
    url = gateway_url() + path
    headers = {"Content-Type": "application/json"}
    key = api_key()
    if key:
        headers["Authorization"] = "Bearer " + key
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        return {"__http_error__": exc.code, "__body__": body}
    except Exception as exc:  # connection refused, timeout, bad JSON
        return {"__error__": str(exc)}


def gateway_status() -> Dict[str, Any]:
    """Cheap reachability check plus the live model count."""
    key = api_key()
    result = _request_json("GET", "/v1/models", timeout=10.0)
    if "__http_error__" in result or "__error__" in result:
        return {
            "online": False,
            "url": gateway_url(),
            "key_configured": bool(key),
            "error": result.get("__body__") or result.get("__error__"),
        }
    data = result.get("data") or []
    return {
        "online": True,
        "url": gateway_url(),
        "key_configured": bool(key),
        "models_advertised": len(data),
    }


def available_ids() -> List[str]:
    result = _request_json("GET", "/v1/models", timeout=10.0)
    if "__http_error__" in result or "__error__" in result:
        return []
    return [str(m.get("id")) for m in result.get("data") or [] if m.get("id")]


def list_free_models(live: bool = True) -> Dict[str, Any]:
    """Return the verified catalog, annotated with live availability."""
    advertised = set(available_ids()) if live else set()
    models = []
    for entry in FREE_MODEL_CATALOG:
        row = dict(entry)
        if live:
            row["advertised"] = entry["id"] in advertised
        models.append(row)
    return {
        "count": len(models),
        "default_model": DEFAULT_MODEL,
        "gateway": gateway_status() if live else {"url": gateway_url()},
        "models": models,
        "note": (
            "Only the OpenCode Free lane works without an account. Other catalog "
            "IDs need an OAuth login or API key and will return 404."
        ),
    }


def ask_free_model(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.2,
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """Send one chat completion through the local gateway."""
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "model": model, "error": "prompt is required"}
    if not api_key():
        return {
            "ok": False,
            "model": model,
            "error": (
                "No gateway key. Set NINE_ROUTER_API_KEY or place the key in "
                f"{_key_file()}."
            ),
        }

    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    started = time.time()
    result = _request_json(
        "POST",
        "/v1/chat/completions",
        payload={
            "model": model,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "stream": False,
        },
        timeout=timeout,
    )
    elapsed_ms = int((time.time() - started) * 1000)

    if "__error__" in result:
        return {"ok": False, "model": model, "ms": elapsed_ms, "error": result["__error__"]}
    if "__http_error__" in result:
        return {
            "ok": False,
            "model": model,
            "ms": elapsed_ms,
            "status": result["__http_error__"],
            "error": (result.get("__body__") or "").strip() or "gateway returned an error",
        }

    choice = (result.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    if not content:
        return {
            "ok": False,
            "model": model,
            "ms": elapsed_ms,
            "error": "empty completion (increase max_tokens for reasoning models)",
        }
    return {
        "ok": True,
        "model": result.get("model") or model,
        "ms": elapsed_ms,
        "content": content,
        "usage": result.get("usage"),
    }


def health(probe: bool = False) -> Dict[str, Any]:
    """Report reachability, and optionally send a real completion per model."""
    status = gateway_status()
    if not probe:
        return {"gateway": status, "probed": False}

    rows = []
    for entry in FREE_MODEL_CATALOG:
        outcome = ask_free_model("Reply with the single word: OK", model=entry["id"], max_tokens=64)
        rows.append(
            {
                "id": entry["id"],
                "ok": bool(outcome.get("ok")),
                "ms": outcome.get("ms"),
                "content": outcome.get("content"),
                "error": outcome.get("error"),
            }
        )
    passed = sum(1 for row in rows if row["ok"])
    return {
        "gateway": status,
        "probed": True,
        "passed": passed,
        "total": len(rows),
        "models": rows,
    }
