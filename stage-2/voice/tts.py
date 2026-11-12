"""Backward compatibility shim forwarding to jarvis.tts.

The shared engine defaults to edge-tts neural speech with piper/pyttsx3 as
offline fallbacks; see ``jarvis/voice_models.py`` for the full catalog.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from jarvis.tts import get_engine, speak, synthesize

__all__ = ["speak", "synthesize", "get_engine"]
