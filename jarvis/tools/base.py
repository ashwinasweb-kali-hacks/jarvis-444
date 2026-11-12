"""JARVIS Tool Layer — Safe, structured action execution with permission gating.

Declares risk levels: 'safe', 'confirm', 'blocked'.
Logs all executed actions to an append-only log file.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jarvis.tools")

_ACTION_LOG_PATH = Path.home() / ".jarvis" / "actions.log"


class Tool(ABC):
    name: str = ""
    description: str = ""
    risk: str = "safe"  # safe | confirm | blocked
    schema: Dict[str, Any] = {}

    @abstractmethod
    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool safely with validated kwargs."""
        pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        _ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk": t.risk,
                "schema": t.schema,
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, args: Optional[Dict[str, Any]] = None, confirmed: bool = False, **kwargs: Any) -> Dict[str, Any]:
        """Execute a tool through the permission gate."""
        tool = self.get(name)
        if not tool:
            return {"ok": False, "error": f"Tool '{name}' not found."}

        args = dict(args or {})
        if kwargs:
            args.update(kwargs)

        # Permission Gate
        if tool.risk == "blocked":
            self._log_action(name, args, "declined", "Operation is blocked by system security.")
            return {"ok": False, "status": "blocked", "message": "Operation is strictly prohibited."}

        if tool.risk == "confirm" and not confirmed:
            self._log_action(name, args, "pending_confirmation", "Awaiting user confirmation.")
            return {
                "ok": True,
                "status": "awaiting_confirmation",
                "message": f"Confirmation required before executing {name}.",
            }

        try:
            result = tool.run(**args)
            self._log_action(name, args, "executed", "Success", result)
            return {"ok": True, "status": "success", "result": result}
        except Exception as e:
            logger.exception("Failed executing tool %s: %s", name, e)
            self._log_action(name, args, "failed", str(e))
            return {"ok": False, "status": "error", "error": str(e)}

    def _log_action(
        self,
        tool_name: str,
        args: Dict[str, Any],
        status: str,
        note: str,
        result: Optional[Any] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "args": args,
            "status": status,
            "note": note,
            "result": result,
        }
        try:
            with open(_ACTION_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.debug("Failed writing action log: %s", e)


_default_registry = ToolRegistry()


def get_default_registry() -> ToolRegistry:
    return _default_registry
