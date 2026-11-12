"""Local notes and workspace memos tool."""
import os
from pathlib import Path
from typing import Any, Dict
from jarvis.tools.base import Tool

_NOTES_DIR = Path.home() / ".jarvis" / "notes"


class ReadNoteTool(Tool):
    name = "read_note"
    description = "Read a note or list existing notes."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
    }

    def run(self, title: str = "default", **kwargs: Any) -> Dict[str, Any]:
        _NOTES_DIR.mkdir(parents=True, exist_ok=True)
        note_path = _NOTES_DIR / f"{title}.txt"
        if not note_path.exists():
            return {"exists": False, "title": title, "content": "No content found."}
        return {"exists": True, "title": title, "content": note_path.read_text(encoding="utf-8")}


class WriteNoteTool(Tool):
    name = "write_note"
    description = "Create or append to a local note."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["content"],
    }

    def run(self, content: str, title: str = "default", **kwargs: Any) -> Dict[str, Any]:
        _NOTES_DIR.mkdir(parents=True, exist_ok=True)
        note_path = _NOTES_DIR / f"{title}.txt"
        with open(note_path, "a", encoding="utf-8") as f:
            f.write(content + "\n")
        return {"saved": True, "title": title, "bytes": len(content)}
