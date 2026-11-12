"""JARVIS Daemon — Headless background service and IPC communication bridge.

Accepts commands over HTTP / JSON socket from the shell UI or test runners.
Dispatches queries to jarvis.brain and provides studio-quality neural TTS and STT.
Serves the master workshop UI over http://127.0.0.1:8765/ with secure audio/video origin.
"""
from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from jarvis.brain import Reply, respond
from jarvis.config import JarvisConfig
from jarvis import tts as voice_out
from jarvis import voice_models

logger = logging.getLogger("jarvis.daemon")
_STARTED_AT = time.time()
_SHELL_DIR = Path(__file__).resolve().parent.parent / "shell"

# Agent -> Edge voice, kept for the shell UI's /api/tts?agent= calls.
VOICE_MAP = dict(voice_models.get_tts("edge-tts")["voices"])


async def _synthesize_edge_tts(text: str, voice: str) -> bytes:
    """Backwards-compatible wrapper around the shared TTS engine."""
    outcome = voice_out.synthesize(text, voice=voice, model="edge-tts", fallback=False)
    if not outcome.get("ok"):
        raise RuntimeError(outcome.get("error", "edge-tts failed"))
    return outcome["audio"]


class JarvisDaemonHandler(BaseHTTPRequestHandler):
    """HTTP/JSON RPC and Media Streaming handler for JARVIS."""

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/status", "/api/status"):
            config = JarvisConfig.from_env()
            self._send_json(200, {
                "status": "online",
                "service": "jarvis-daemon",
                "provider": config.brain_provider,
                "address": config.address,
                "stt_model": config.stt_model,
                "tts_model": config.tts_model,
            })
            return

        if path in ("/api/health", "/health"):
            from jarvis import keyvault
            from jarvis.tools.base import get_default_registry

            config = JarvisConfig.from_env()
            registry = get_default_registry()
            tls_on = os.environ.get("JARVIS_TLS", "").strip().lower() in ("1", "true", "yes", "on")
            configured = [k["provider"] for k in keyvault.list_keys() if k["configured"]]
            self._send_json(200, {
                "status": "online",
                "uptime_seconds": int(time.time() - _STARTED_AT),
                "scheme": "https" if tls_on else "http",
                "brain_provider": config.brain_provider,
                "address": config.address,
                "tools": len(registry.list_tools()),
                "tool_names": [t["name"] for t in registry.list_tools()],
                "keys_configured": configured,
                "vr": {
                    "webxr_needs_https": True,
                    "https_enabled": tls_on,
                    "note": "Headset browsers only expose WebXR on a secure context.",
                },
            })
            return

        if path in ("/api/settings", "/settings"):
            from jarvis.settings import all_settings
            self._send_json(200, {"ok": True, "settings": all_settings()})
            return

        if path in ("/api/auth/claude", "/auth/claude"):
            try:
                from jarvis.claude_oauth import start_oauth_flow
                auth_url = start_oauth_flow(open_browser=True)
                self._send_json(200, {
                    "ok": True,
                    "auth_url": auth_url,
                    "message": "Opening Claude authentication in your browser."
                })
                return
            except Exception as e:
                logger.exception("Claude OAuth flow initialization error: %s", e)
                self._send_json(500, {"error": str(e)})
                return

        if path in ("/api/tts", "/tts"):
            query = urllib.parse.parse_qs(parsed_url.query)
            text = query.get("text", [""])[0].strip()
            agent = query.get("agent", ["jarvis"])[0].lower().strip()
            model = query.get("model", [None])[0] or voice_models.tts_model()

            if not text:
                self._send_json(400, {"error": "Missing 'text' parameter"})
                return

            outcome = voice_out.synthesize(text, agent=agent, model=model)
            if not outcome.get("ok"):
                logger.error("Error synthesizing speech: %s", outcome.get("error"))
                self._send_json(500, {"error": outcome.get("error", "TTS failed")})
                return

            audio_bytes = outcome["audio"]
            self.send_response(200)
            self.send_header("Content-Type", outcome.get("mime", "audio/mpeg"))
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.send_header("X-Jarvis-TTS-Model", str(outcome.get("model", model)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(audio_bytes)
            return

        if path in ("/api/voice/models", "/voice/models"):
            self._send_json(200, {"ok": True, **voice_models.list_voice_models(live=True)})
            return

        # Serve Workshop HUD static files
        req_path = path.lstrip("/")
        if not req_path or req_path in ("index.html", "shell", "shell/index.html"):
            target_file = _SHELL_DIR / "index.html"
        else:
            clean_name = req_path.replace("shell/", "")
            target_file = _SHELL_DIR / clean_name

        if target_file.exists() and target_file.is_file():
            content = target_file.read_bytes()
            mime = "text/html"
            if target_file.suffix == ".js":
                mime = "application/javascript"
            elif target_file.suffix == ".css":
                mime = "text/css"
            elif target_file.suffix == ".mp3":
                mime = "audio/mpeg"
            elif target_file.suffix == ".mp4":
                mime = "video/mp4"
            elif target_file.suffix in (".png", ".jpg", ".jpeg"):
                mime = "image/png"

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
            return

        self._send_json(404, {"error": f"Endpoint not found: {path}"})

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        logger.debug("do_POST path='%s' (raw='%s')", path, self.path)

        if path in ("/api/command", "/command", "/chat"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                req = json.loads(body) if body else {}
                text = req.get("text", "").strip()

                if not text:
                    self._send_json(400, {"error": "Missing 'text' field"})
                    return

                reply: Reply = respond(text)

                # Execute automation tool actions directly on host PC
                from jarvis.tools.base import get_default_registry
                reg = get_default_registry()
                executed_actions = []
                for act in reply.actions:
                    t_name = act.get("tool")
                    t_args = act.get("args", {})
                    if t_name and reg.get(t_name):
                        res = reg.execute(t_name, args=t_args)
                        executed_actions.append(res)

                resp_data = reply.to_dict()
                if executed_actions:
                    resp_data["executed_actions"] = executed_actions

                self._send_json(200, {
                    "ok": True,
                    "reply": resp_data,
                })
            except Exception as e:
                logger.exception("Error processing command: %s", e)
                self._send_json(500, {"error": str(e)})

        elif path in ("/api/stt", "/stt"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                audio_bytes = self.rfile.read(length)

                from jarvis import stt as voice_in
                model_id = voice_models.stt_model()
                text = ""
                error = None
                try:
                    text = voice_in.transcribe_wav_bytes(audio_bytes)
                except Exception as ex:
                    error = str(ex)
                    logger.debug("Local speech recognition failed: %s", ex)

                payload = {"ok": True, "text": text, "model": model_id}
                if error:
                    payload["error"] = error
                self._send_json(200, payload)
            except Exception as e:
                logger.exception("Error processing STT: %s", e)
                self._send_json(500, {"error": str(e)})

        elif path in ("/api/call", "/call"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                req = json.loads(body) if body else {}
                target = req.get("target", "Friend")
                from jarvis.tools.call import CallTool
                res = CallTool().run(target=target)
                self._send_json(200, {"ok": True, "call": res})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path in ("/api/settings", "/settings"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                req = json.loads(body) if body else {}
                key = req.get("key")
                value = req.get("value")
                if key is None:
                    self._send_json(400, {"error": "Missing 'key' field"})
                    return
                from jarvis.settings import set as set_setting, get as get_setting

                set_setting(str(key), value)
                self._send_json(200, {"ok": True, "key": key, "value": get_setting(str(key))})
            except Exception as e:
                logger.exception("Error saving setting: %s", e)
                self._send_json(500, {"error": str(e)})

        elif path in ("/api/webrtc/signal", "/webrtc/signal"):
            try:
                from jarvis.webrtc import signal_room
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                req = json.loads(body) if body else {}
                room = str(req.get("room", "default"))
                peer = str(req.get("peer", "unknown"))
                sdp = req.get("sdp")
                candidate = req.get("candidate")
                out = signal_room(room, peer, sdp=sdp, candidate=candidate)
                self._send_json(200, {"ok": True, "signal": out})
            except Exception as e:
                logger.exception("WebRTC signaling error: %s", e)
                self._send_json(500, {"error": str(e)})

        elif path in ("/api/mic/record_host", "/mic/record_host"):
            try:
                import io
                import wave
                import numpy as np
                import sounddevice as sd
                from jarvis import stt as voice_in
                fs = 16000
                rec = sd.rec(int(3.0 * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()
                buf = io.BytesIO()
                with wave.open(buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(fs)
                    wf.writeframes(rec.tobytes())
                text = voice_in.transcribe_wav_bytes(buf.getvalue())
                self._send_json(200, {"ok": True, "text": text, "model": voice_models.stt_model()})
            except Exception as e:
                self._send_json(200, {"ok": False, "text": "", "error": str(e)})

        elif path in ("/api/config", "/config"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                cfg = json.loads(body) if body else {}

                if "provider" in cfg and cfg["provider"]:
                    os.environ["JARVIS_BRAIN_PROVIDER"] = cfg["provider"].strip()

                self._send_json(200, {"ok": True, "message": "Configuration updated successfully."})
            except Exception as e:
                logger.exception("Error updating config: %s", e)
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Unknown POST endpoint"})

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)


class JarvisDaemon:
    """Long-running JARVIS daemon thread / process."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        config = JarvisConfig.from_env()
        self.host = host or config.daemon_host
        self.port = port or config.daemon_port
        self.server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False) -> None:
        self.server = ThreadingHTTPServer((self.host, self.port), JarvisDaemonHandler)

        wants_tls = os.environ.get("JARVIS_TLS", "").strip().lower() in ("1", "true", "yes", "on")
        self.scheme = "http"
        if wants_tls:
            from jarvis.tls import ensure_certificate, wrap_server_socket

            pair = ensure_certificate()
            if pair:
                cert_file, key_file = pair
                try:
                    wrap_server_socket(self.server, cert_file, key_file)
                    self.scheme = "https"
                    logger.info("TLS enabled (self-signed certificate will warn once)")
                except Exception as exc:
                    logger.warning("TLS setup failed, continuing on plain http: %s", exc)
            else:
                logger.warning("TLS requested but unavailable; serving plain http")

        logger.info("JARVIS Daemon listening on %s://%s:%d", self.scheme, self.host, self.port)

        if blocking:
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        if self.server:
            logger.info("Shutting down JARVIS Daemon...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None


def main() -> None:
    from jarvis.config import setup_logging
    setup_logging()
    daemon = JarvisDaemon()
    print(f"JARVIS Daemon starting on {daemon.host}:{daemon.port} (Press Ctrl+C to stop)")
    daemon.start(blocking=True)


if __name__ == "__main__":
    main()
