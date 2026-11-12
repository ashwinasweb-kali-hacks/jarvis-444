"""JARVIS key vault — one place for provider API keys.

Keys live in ``~/.jarvis/keys.json`` with owner-only permissions. Environment
variables always win over the file, so a key can be exported for one session
without touching disk.

Honest note on security: the file is **not encrypted at rest**. It is protected
by file permissions only. On Windows that means the ACL of your user profile.
If a key matters, keep it in an environment variable instead and never write it
here.

Secrets are never returned in full. ``list_keys`` and the MCP surface only ever
see a masked preview such as ``sk-a…9f2c``.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

KEYS_PATH = Path.home() / ".jarvis" / "keys.json"

# provider -> environment variable that overrides the stored value
ENV_VARS: Dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "opencode": "OPENCODE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "globalfone": "JARVIS_GLOBALFONE_TOKEN",
    "twilio_sid": "TWILIO_ACCOUNT_SID",
    "twilio_token": "TWILIO_AUTH_TOKEN",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "nine_router": "NINE_ROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "github": "GITHUB_TOKEN",
}


def _load() -> Dict[str, str]:
    try:
        if KEYS_PATH.exists():
            data = json.loads(KEYS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save(data: Dict[str, str]) -> None:
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(KEYS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        # Windows honours the profile ACL; this is best-effort only.
        pass


def mask(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}\u2026{value[-keep:]}"


def set_key(provider: str, key: str) -> Dict[str, Any]:
    provider = (provider or "").strip().lower()
    key = (key or "").strip()
    if not provider:
        return {"ok": False, "error": "provider is required"}
    if len(key) < 8:
        return {"ok": False, "error": "key looks too short to be real"}

    data = _load()
    data[provider] = key
    _save(data)
    return {
        "ok": True,
        "provider": provider,
        "masked": mask(key),
        "stored_at": str(KEYS_PATH),
        "env_override": ENV_VARS.get(provider, ""),
    }


def get_key(provider: str) -> Optional[str]:
    provider = (provider or "").strip().lower()
    env_name = ENV_VARS.get(provider)
    if env_name:
        from_env = os.environ.get(env_name)
        if from_env:
            return from_env
    return _load().get(provider)


def delete_key(provider: str) -> Dict[str, Any]:
    provider = (provider or "").strip().lower()
    data = _load()
    if provider not in data:
        return {"ok": False, "error": f"no stored key for '{provider}'"}
    del data[provider]
    _save(data)
    return {"ok": True, "provider": provider, "deleted": True}


def list_keys() -> List[Dict[str, Any]]:
    stored = _load()
    rows: List[Dict[str, Any]] = []
    for provider in sorted(set(stored) | set(ENV_VARS)):
        env_name = ENV_VARS.get(provider, "")
        from_env = bool(env_name and os.environ.get(env_name))
        value = os.environ.get(env_name, "") if from_env else stored.get(provider, "")
        rows.append(
            {
                "provider": provider,
                "configured": bool(value),
                "source": "env" if from_env else ("file" if value else "none"),
                "masked": mask(value),
                "env_var": env_name,
            }
        )
    return rows
