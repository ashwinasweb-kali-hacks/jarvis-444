"""Power management and destructive operations gated by permissions."""
from typing import Any, Dict
from jarvis.tools.base import Tool


class ShutdownTool(Tool):
    name = "shutdown"
    description = "Safely power down the system. Requires confirmation."
    risk = "confirm"
    schema = {
        "type": "object",
        "properties": {
            "delay_seconds": {"type": "integer", "default": 0},
        },
    }

    def run(self, delay_seconds: int = 0, **kwargs: Any) -> Dict[str, Any]:
        return {
            "scheduled": True,
            "action": "shutdown",
            "delay": delay_seconds,
            "message": "System shutdown sequence initiated.",
        }


class FormatDiskTool(Tool):
    name = "format_disk"
    description = "Wipe and format a disk or partition. Blocked for system safety."
    risk = "blocked"
    schema = {
        "type": "object",
        "properties": {
            "device": {"type": "string"},
        },
        "required": ["device"],
    }

    def run(self, device: str, **kwargs: Any) -> Dict[str, Any]:
        # Blocked by default in permission gate; should never execute
        raise PermissionError(f"Direct disk format of '{device}' is permanently blocked.")
