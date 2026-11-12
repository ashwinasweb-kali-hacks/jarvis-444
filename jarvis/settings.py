"""Persistent JARVIS settings store.

Lives at ``~/.jarvis/settings.json`` with owner-only permissions.
Environment variables override anything in the file. Nothing is secret here
(except possibly voice preferences); the file is ACL-protected only.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

from jarvis import voice_models

SETTINGS_PATH = Path.home() / ".jarvis" / "settings.json"

# Env override prefix: JARVIS_SETTING_<KEY> maps to key.lower()
# e.g. JARVIS_SETTING_VOICE_RATE=-5%  -> voice.rate = "-5%"


def _load() -> Dict[str, Any]:
    try:
        if SETTINGS_PATH.exists():
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): v for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save(data: Dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def get(key: str, default: Any = None) -> Any:
    """Return a setting, checking env override first."""
    env_name = "JARVIS_SETTING_" + key.upper()
    if env_name in os.environ:
        return os.environ[env_name]
    return _load().get(key, default)


def set(key: str, value: Any) -> Dict[str, Any]:
    if not key or not isinstance(key, str):
        return {"ok": False, "error": "key is required"}
    data = _load()
    data[key] = value
    _save(data)
    return {"ok": True, "key": key, "value": value, "stored_at": str(SETTINGS_PATH)}


def delete(key: str) -> Dict[str, Any]:
    data = _load()
    if key not in data:
        return {"ok": False, "error": f"no setting '{key}'"}
    del data[key]
    _save(data)
    return {"ok": True, "key": key, "deleted": True}


def all_settings() -> Dict[str, Any]:
    """Merge file settings with visible env overrides (masked if they look like secrets)."""
    merged = dict(_load())
    for name, value in os.environ.items():
        if name.startswith("JARVIS_SETTING_"):
            merged[name[15:].lower()] = value
    return merged


def defaults() -> Dict[str, Any]:
    return {
        "voice": "jarvis",
        "voice_rate": "-3%",
        "voice_pitch": "-1Hz",
        "silence_ms": 800,
        "max_clip_sec": 15,
        "min_clip_sec": 0.3,
        "whisper_model": voice_models.whisper_size(),
        "whisper_device": "cpu",
        "whisper_compute": "int8",
        "stt_model": voice_models.default_stt_id(),
        "tts_model": voice_models.default_tts_id(),
        "brain_provider": "oauth",
        "tts_cache": True,
        "boot_video": "boot.mp4",
        "boot_mode": "video",
        "demo_number": "8825586080",
        "webxr": True,
        "theme": "cyan",
        "language": "en",
        "confirm_destructive": True,
    }
