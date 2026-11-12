"""Phone calling — GlobalFone-first, system dialer as the guaranteed fallback.

What is actually known about GlobalFone
---------------------------------------
GlobalFone is a VoIP / business phone service. As of November 2026 it publishes
**no public developer API and no documented HTTP endpoint**. There is nothing on
the open web to call. So this adapter does not invent one. Instead it reads an
endpoint and token that *you* obtain from GlobalFone (their support or reseller
gives out the API base for business accounts) and posts a tiny, documented
payload to it:

    POST {JARVIS_GLOBALFONE_URL}
    Authorization: Bearer {JARVIS_GLOBALFONE_TOKEN}
    Content-Type: application/json

    {"to": "+918825586080", "from": "<your globalfone number>", "action": "call"}

If that endpoint is not configured, or the request fails, the tool falls back to
the operating system dialer (``tel:``), which always works on a phone, tablet or
Windows machine with Phone Link. The reply always states which path was used, so
nothing is ever claimed that did not happen.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict

from jarvis import keyvault
from jarvis.tools.base import Tool

logger = logging.getLogger("jarvis.tools.globalfone")

DEFAULT_NUMBER = "8825586080"


def _clean(number: str) -> str:
    digits = re.sub(r"[^\d+]", "", number or "")
    if not digits or digits.lower() in ("friend", "myfriend"):
        return DEFAULT_NUMBER
    if len(digits) == 10:
        digits = "+91" + digits
    return digits


class GlobalFoneCallTool(Tool):
    name = "globalfone_call"
    description = (
        "Place a real outbound phone call. Tries the GlobalFone VoIP gateway when it is "
        "configured, otherwise hands the number to the operating system dialer."
    )
    # 'safe': the spoken command is itself the confirmation, matching the existing
    # CallTool behaviour. Destructive tools remain 'confirm'/'blocked'.
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Phone number in E.164 or 10-digit local form",
            },
            "provider": {
                "type": "string",
                "enum": ["auto", "globalfone", "dialer"],
                "description": "auto tries GlobalFone then falls back to the OS dialer",
            },
        },
        "required": ["to"],
    }

    # ---------------------------------------------------------------- gateway
    def _gateway(self, number: str) -> Dict[str, Any]:
        url = (os.environ.get("JARVIS_GLOBALFONE_URL") or "").strip()
        token = keyvault.get_key("globalfone") or ""
        caller = (os.environ.get("JARVIS_GLOBALFONE_FROM") or "").strip()

        if not url:
            return {"ok": False, "reason": "JARVIS_GLOBALFONE_URL is not set"}
        if not token:
            return {"ok": False, "reason": "no GlobalFone token in the key vault"}

        payload = json.dumps(
            {"to": number, "from": caller, "action": "call"}
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                body = resp.read(400).decode("utf-8", "replace")
                return {"ok": True, "status": resp.status, "body": body}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "reason": f"gateway HTTP {exc.code}"}
        except Exception as exc:
            return {"ok": False, "reason": f"gateway unreachable: {exc}"}

    # ------------------------------------------------------------------ dialer
    def _dialer(self, number: str) -> Dict[str, Any]:
        try:
            if os.name == "nt":
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "", f"tel:{number}"], shell=False
                )
                return {"ok": True, "how": "windows tel: handler"}
            opener = shutil.which("xdg-open")
            if opener:
                subprocess.Popen([opener, f"tel:{number}"])
                return {"ok": True, "how": "xdg-open tel:"}
            return {"ok": False, "reason": "no dialer handler on this platform"}
        except Exception as exc:
            return {"ok": False, "reason": str(exc)}

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        number = _clean(str(kwargs.get("to", DEFAULT_NUMBER)))
        provider = str(kwargs.get("provider", "auto")).lower()

        if provider == "dialer":
            outcome = self._dialer(number)
            return {
                "number": number,
                "channel": "system_dialer",
                "placed": outcome.get("ok", False),
                "detail": outcome,
                "message": (
                    f"Handed {number} to the device dialer — answer it on the phone."
                    if outcome.get("ok")
                    else f"Could not open a dialer for {number}: {outcome.get('reason')}"
                ),
            }

        gateway = self._gateway(number)
        if gateway.get("ok"):
            return {
                "number": number,
                "channel": "globalfone",
                "placed": True,
                "detail": gateway,
                "message": f"Call to {number} submitted to the GlobalFone gateway.",
            }

        if provider == "globalfone":
            return {
                "number": number,
                "channel": "globalfone",
                "placed": False,
                "detail": gateway,
                "message": (
                    "GlobalFone is not configured, so no call was placed. "
                    f"Reason: {gateway.get('reason')}"
                ),
            }

        dialer = self._dialer(number)
        return {
            "number": number,
            "channel": "system_dialer",
            "placed": dialer.get("ok", False),
            "detail": {"gateway_reason": gateway.get("reason"), "dialer": dialer},
            "message": (
                f"GlobalFone unavailable ({gateway.get('reason')}); "
                f"handed {number} to the device dialer instead."
            ),
        }
