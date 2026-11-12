"""PC Automation Tool — Automates real host actions on Windows.

Handles launching apps, system controls (volume, lock screen, screenshot),
and website / file exploration.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from jarvis.tools.base import Tool

logger = logging.getLogger("jarvis.tools.pc_automation")

KNOWN_APPS: Dict[str, list[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "downloads": ["explorer.exe", str(Path.home() / "Downloads")],
    "documents": ["explorer.exe", str(Path.home() / "Documents")],
    "terminal": ["wt.exe"],
    "cmd": ["cmd.exe", "/c", "start"],
    "powershell": ["powershell.exe"],
    "taskmgr": ["taskmgr.exe"],
    "paint": ["mspaint.exe"],
    "chrome": ["cmd.exe", "/c", "start", "chrome"],
    "browser": ["cmd.exe", "/c", "start", "https://google.com"],
}


class PCAutomationTool(Tool):
    name = "pc_automation"
    description = "Automate host actions: launch applications, adjust volume, take screenshots, lock PC, open folders."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["open_app", "screenshot", "volume_up", "volume_down", "mute", "lock_screen", "open_url"],
                "description": "Automation action type",
            },
            "target": {
                "type": "string",
                "description": "Application name, URL, or parameter",
            },
        },
        "required": ["action"],
    }

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        action = kwargs.get("action", "")
        target = kwargs.get("target", "").lower().strip()
        logger.info("PCAutomationTool run: action=%s, target=%s", action, target)

        if action == "open_app":
            app_cmd = None
            for key, cmd in KNOWN_APPS.items():
                if key in target:
                    app_cmd = cmd
                    break
            if not app_cmd:
                app_cmd = ["cmd.exe", "/c", "start", target]

            try:
                subprocess.Popen(app_cmd, shell=False)
                return {"ok": True, "message": f"Launched {target} successfully on PC."}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        elif action == "open_url":
            url = target if target.startswith("http") else f"https://{target}"
            subprocess.Popen(["cmd.exe", "/c", "start", url], shell=False)
            return {"ok": True, "message": f"Opened {url} in browser."}

        elif action == "lock_screen":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return {"ok": True, "message": "Host workstation locked."}

        elif action == "screenshot":
            screenshot_path = Path.home() / "Pictures" / "jarvis_screenshot.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms,System.Drawing
            $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
            $bmp.Save('{str(screenshot_path)}')
            $g.Dispose()
            $bmp.Dispose()
            """
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=6, check=True)
                return {"ok": True, "path": str(screenshot_path), "message": "Screenshot captured and saved to Pictures folder."}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        elif action in ("volume_up", "volume_down", "mute"):
            # Send Windows virtual media keys via PowerShell
            key_code = 0xAF if action == "volume_up" else (0xAE if action == "volume_down" else 0xAD)
            ps_code = f"""
            $wscript = New-Object -ComObject Wscript.Shell
            $wscript.SendKeys([char]{key_code})
            """
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], timeout=3)
                return {"ok": True, "message": f"Adjusted system audio: {action}."}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        return {"ok": False, "error": f"Unknown action: {action}"}
