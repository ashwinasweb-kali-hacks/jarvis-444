"""Claude OAuth Manager — Connect your authentic Claude.ai account via OAuth.

Enables JARVIS to route queries through your authenticated Claude subscription (Claude Pro/Team/Max)
using official PKCE authorization code exchange.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("jarvis.claude_oauth")

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CALLBACK_PORT = 53692
CALLBACK_PATH = "/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"
SCOPES = "org:create_api_key user:profile user:inference user:sessions:claude_code user:mcp_servers user:file_upload"

CONFIG_DIR = Path.home() / ".jarvis"
TOKEN_FILE = CONFIG_DIR / "claude_oauth.json"


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and S256 code_challenge."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Temporary local HTTP listener for the OAuth redirect callback."""
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None
    server_instance: Optional[ThreadingHTTPServer] = None

    def do_GET(self) -> None:
        url = urllib.parse.urlparse(self.path)
        if url.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = urllib.parse.parse_qs(url.query)
        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = "<html><body style='background:#04070b;color:#ff3344;font-family:sans-serif;text-align:center;padding:50px;'><h2>Authentication failed</h2><p>" + OAuthCallbackHandler.error + "</p></body></html>"
            self.wfile.write(html.encode("utf-8"))
            return

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        OAuthCallbackHandler.code = code
        OAuthCallbackHandler.state = state

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            "<html><body style='background:#04070b;color:#3be8ff;font-family:sans-serif;text-align:center;padding:50px;'>"
            "<h2>Claude Authentication Successful!</h2>"
            "<p>Your Claude account is now securely connected to J.A.R.V.I.S.</p>"
            "<p style='color:#6aa9b5;'>You may now close this browser tab and return to the workshop.</p>"
            "</body></html>"
        )
        self.wfile.write(html.encode("utf-8"))


def exchange_code_for_token(code: str, verifier: str, state: str) -> Dict[str, Any]:
    """Exchanges authorization code for access and refresh tokens."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "state": state,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    }

    req = urllib.request.Request(
        TOKEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    token_info = {
        "type": "oauth",
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_at": time.time() + data.get("expires_in", 3600) - 300,
        "created_at": time.time(),
    }

    save_claude_token(token_info)
    return token_info


def refresh_token(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refreshes expired OAuth access token using refresh_token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": token_data.get("refresh_token"),
    }

    req = urllib.request.Request(
        TOKEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    token_info = {
        "type": "oauth",
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token") or token_data.get("refresh_token"),
        "expires_at": time.time() + data.get("expires_in", 3600) - 300,
        "created_at": time.time(),
    }

    save_claude_token(token_info)
    return token_info


def save_claude_token(token_info: Dict[str, Any]) -> None:
    """Save token to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token_info, indent=2), encoding="utf-8")
    logger.info("Saved Claude OAuth token to %s", TOKEN_FILE)


def load_claude_token() -> Optional[Dict[str, Any]]:
    """Load cached Claude token, refreshing if necessary."""
    if not TOKEN_FILE.exists():
        return None

    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        if not data.get("access_token"):
            return None

        # Check if expired
        expires_at = data.get("expires_at", 0)
        if time.time() >= expires_at:
            if data.get("refresh_token"):
                logger.info("Claude OAuth access token expired. Refreshing...")
                return refresh_token(data)
            return None

        return data
    except Exception as e:
        logger.debug("Failed to read Claude token: %s", e)
        return None


def get_claude_auth_url(verifier: str, challenge: str) -> str:
    """Build the authorization URL for user login."""
    params = {
        "code": "true",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": verifier,
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def start_oauth_flow(open_browser: bool = True) -> str:
    """Starts the OAuth login flow, spinning up the local callback server."""
    verifier, challenge = generate_pkce()
    auth_url = get_claude_auth_url(verifier, challenge)

    OAuthCallbackHandler.code = None
    OAuthCallbackHandler.state = None
    OAuthCallbackHandler.error = None

    server = ThreadingHTTPServer(("127.0.0.1", CALLBACK_PORT), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    logger.info("Claude OAuth listener started on %s", REDIRECT_URI)

    if open_browser:
        print("\nOpening your browser to connect your Claude account...")
        print(f"If it doesn't open automatically, visit this URL:\n\n{auth_url}\n")
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

    # Wait in background thread for callback completion
    def _wait_and_exchange():
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 min timeout
            if OAuthCallbackHandler.code:
                try:
                    exchange_code_for_token(OAuthCallbackHandler.code, verifier, OAuthCallbackHandler.state)
                    print("\n[SUCCESS] Connected to your Claude account via OAuth!")
                except Exception as e:
                    logger.exception("Failed to exchange Claude token: %s", e)
                break
            if OAuthCallbackHandler.error:
                print(f"\n[ERROR] Claude login failed: {OAuthCallbackHandler.error}")
                break
            time.sleep(1)

        server.shutdown()
        server.server_close()

    exchange_thread = threading.Thread(target=_wait_and_exchange, daemon=True)
    exchange_thread.start()

    return auth_url


def query_claude(prompt: str, model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
    """Query Anthropic Messages API using stored Claude OAuth access token."""
    token_data = load_claude_token()
    if not token_data or not token_data.get("access_token"):
        return None

    access_token = token_data["access_token"]
    url = "https://api.anthropic.com/v1/messages"

    payload = {
        "model": model,
        "max_tokens": 120,
        "messages": [
            {
                "role": "user",
                "content": f"You are JARVIS, Tony Stark's calm, dry British AI butler. In 1 concise spoken sentence, answer: {prompt}"
            }
        ]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-01-20",
            "Content-Type": "application/json",
            "User-Agent": "ClaudeCode/2.1.251 (JARVIS-OS)",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("content", [])
            for block in content:
                if block.get("type") == "text":
                    return block.get("text", "").strip()
    except Exception as e:
        logger.debug("Claude API query error: %s", e)

    return None


if __name__ == "__main__":
    url = start_oauth_flow(open_browser=True)
    print("Waiting for authentication callback on port 53692...")
    print("Press Ctrl+C to cancel.")
    try:
        while not load_claude_token():
            time.sleep(1)
        print("Claude OAuth setup complete!")
    except KeyboardInterrupt:
        print("Cancelled.")
