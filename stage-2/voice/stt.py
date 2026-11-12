"""Backward compatibility shim forwarding to jarvis.stt."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from jarvis.stt import transcribe, get_model

__all__ = ["transcribe", "get_model"]
