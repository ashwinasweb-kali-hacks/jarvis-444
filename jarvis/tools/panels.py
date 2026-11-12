"""Panel and HUD UI window management tools."""
from typing import Any, Dict
from jarvis.tools.base import Tool


class OpenPanelTool(Tool):
    name = "open_panel"
    description = "Open or focus a HUD panel (stats, hologram, network, notes)."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["stats", "hologram", "network", "notes"],
            },
            "model": {"type": "string"},
        },
        "required": ["type"],
    }

    def run(self, type: str = "stats", model: str = "mark42", **kwargs: Any) -> Dict[str, Any]:
        return {
            "action": "open",
            "panel": type,
            "model": model,
            "state": "active",
        }


class ClosePanelTool(Tool):
    name = "close_panel"
    description = "Close or minimize active HUD panels."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
        },
    }

    def run(self, type: str = "all", **kwargs: Any) -> Dict[str, Any]:
        return {
            "action": "close",
            "panel": type,
            "state": "dismissed",
        }
