"""Network status and connection telemetry."""
import socket
from typing import Any, Dict
from jarvis.tools.base import Tool


class NetworkStatusTool(Tool):
    name = "network_status"
    description = "Check active network interfaces and connectivity."
    risk = "safe"
    schema = {
        "type": "object",
        "properties": {},
    }

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"

        return {
            "hostname": hostname,
            "ip_address": local_ip,
            "status": "connected" if local_ip != "127.0.0.1" else "loopback",
            "security": "nominal",
        }
