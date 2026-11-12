"""Filesystem automation tools — read-only and write-allowlisted only.

Every path is resolved and checked to stay inside the allowed roots so the
assistant cannot wander outside the user's own files.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.tools.base import Tool

logger = logging.getLogger("jarvis.tools.filesystem")

# Default allowed roots: home directory and the repo itself.
# Override with JARVIS_FS_ROOTS as a colon-separated list (Windows: semicolon).
_ALLOWED_RAW = os.environ.get(
    "JARVIS_FS_ROOTS", str(Path.home()) + os.pathsep + str(Path.cwd())
)
_ALLOWED_ROOTS = [Path(p).resolve() for p in _ALLOWED_RAW.split(os.pathsep) if p]


def _safe_path(requested: str) -> Optional[Path]:
    """Return a resolved path inside an allowed root, or None if unsafe."""
    try:
        p = Path(requested).expanduser().resolve()
    except Exception:
        return None
    for root in _ALLOWED_ROOTS:
        try:
            p.relative_to(root)
            return p
        except ValueError:
            continue
    return None


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a text file inside the allowed roots (home + repo by default)."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read",
            },
            "max_bytes": {
                "type": "integer",
                "description": "Maximum bytes to read (default 65536)",
            },
        },
        "required": ["path"],
    }

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        target = _safe_path(str(kwargs.get("path", "")))
        if not target:
            return {"ok": False, "status": "blocked", "message": "Path is outside the allowed roots."}
        if not target.is_file():
            return {"ok": False, "error": f"Not a file: {target}"}
        max_bytes = int(kwargs.get("max_bytes", 65536))
        try:
            data = target.read_bytes()[:max_bytes]
            return {
                "ok": True,
                "path": str(target),
                "bytes": len(data),
                "content": data.decode("utf-8", "replace"),
            }
        except Exception as exc:
            logger.exception("read_file failed: %s", exc)
            return {"ok": False, "error": str(exc)}


class ListDirTool(Tool):
    name = "list_dir"
    description = "List entries inside the allowed roots (home + repo by default)."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (default current dir)",
            },
        },
    }

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        target = _safe_path(str(kwargs.get("path", ".")))
        if not target:
            return {"ok": False, "status": "blocked", "message": "Path is outside the allowed roots."}
        if not target.is_dir():
            return {"ok": False, "error": f"Not a directory: {target}"}
        entries: List[Dict[str, Any]] = []
        try:
            for child in sorted(target.iterdir(), key=lambda c: c.name):
                entries.append(
                    {
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else None,
                    }
                )
            return {"ok": True, "path": str(target), "entries": entries}
        except Exception as exc:
            logger.exception("list_dir failed: %s", exc)
            return {"ok": False, "error": str(exc)}


class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Write text to a file inside the allowed roots. Confirm-only: never run "
        "without explicit spoken confirmation."
    )
    risk = "confirm"
    schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write",
            },
            "content": {
                "type": "string",
                "description": "Text content to write",
            },
        },
        "required": ["path", "content"],
    }

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        target = _safe_path(str(kwargs.get("path", "")))
        if not target:
            return {"ok": False, "status": "blocked", "message": "Path is outside the allowed roots."}
        content = kwargs.get("content", "")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
            return {"ok": True, "path": str(target), "bytes": len(content.encode("utf-8"))}
        except Exception as exc:
            logger.exception("write_file failed: %s", exc)
            return {"ok": False, "error": str(exc)}


class ProcessListTool(Tool):
    name = "process_list"
    description = "List running host processes (name, pid, memory MB)."
    risk = "safe"
    schema = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            import psutil  # type: ignore
        except ImportError:
            return {
                "ok": False,
                "error": "psutil not installed; run: pip install psutil",
            }
        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                procs.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "memory_mb": round((info.get("memory_info") or {}).rss / 1024 / 1024, 1)
                        if info.get("memory_info")
                        else None,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: (x.get("memory_mb") or 0), reverse=True)
        return {"ok": True, "processes": procs[:50]}


class NetworkStatusTool2(Tool):
    """Extended network status — interfaces and active connections."""
    name = "network_status"
    description = "List network interfaces and active TCP connections."
    risk = "safe"
    schema = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            import psutil  # type: ignore
        except ImportError:
            return {
                "ok": False,
                "error": "psutil not installed; run: pip install psutil",
            }
        ifaces: Dict[str, Any] = {}
        try:
            for name, addrs in psutil.net_if_addrs().items():
                ifaces[name] = [
                    {
                        "family": str(a.family),
                        "address": a.address,
                        "netmask": a.netmask,
                    }
                    for a in addrs
                ]
        except Exception:
            pass
        conns: List[Dict[str, Any]] = []
        try:
            for c in psutil.net_connections(kind="inet"):
                conns.append(
                    {
                        "family": str(c.family),
                        "type": str(c.type),
                        "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                        "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                        "status": c.status,
                    }
                )
        except Exception:
            pass
        return {"ok": True, "interfaces": ifaces, "connections": conns[:50]}


__all__ = [
    "ReadFileTool",
    "ListDirTool",
    "WriteFileTool",
    "ProcessListTool",
    "NetworkStatusTool2",
]
