"""Minimal GitHub REST client for publishing the project.

Uses the GitHub REST API (no external deps). The token is read from, in order:
``GITHUB_TOKEN`` / ``GH_TOKEN`` environment variables, then the JARVIS key vault
(``github``). Nothing is logged and the token is never returned to callers.

Docs: https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

API = "https://api.github.com"


def api_token() -> Optional[str]:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = (os.environ.get(var) or "").strip()
        if val:
            return val
    try:
        from jarvis import keyvault

        stored = keyvault.get_key("github")
        if stored:
            return stored.strip()
    except Exception:
        pass
    return None


def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
    token = api_token()
    if not token:
        return {"__error__": "No GitHub token. Set GITHUB_TOKEN or store one via set_api_key github <token>."}
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "jarvis-os-publisher",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return {"status": resp.status, "body": json.loads(body) if body else {}}
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        return {"__http_error__": exc.code, "__body__": raw}
    except Exception as exc:
        return {"__error__": str(exc)}


def authenticated_user() -> Dict[str, Any]:
    return _request("GET", "/user")


def create_repo(
    name: str,
    description: str = "",
    private: bool = False,
    homepage: str = "",
    topics: Optional[list] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": name,
        "description": description,
        "private": bool(private),
        "auto_init": False,
    }
    if homepage:
        payload["homepage"] = homepage
    if topics:
        payload["topics"] = topics
    result = _request("POST", "/user/repos", payload=payload)
    if "__error__" in result or "__http_error__" in result:
        return result
    body = result.get("body") or {}
    return {
        "ok": result.get("status") in (200, 201),
        "name": body.get("full_name"),
        "url": body.get("html_url"),
        "clone_url": body.get("clone_url"),
        "private": body.get("private"),
        "status": result.get("status"),
    }


def repo_exists(owner: str, repo: str) -> bool:
    result = _request("GET", f"/repos/{owner}/{repo}")
    return result.get("status") == 200
