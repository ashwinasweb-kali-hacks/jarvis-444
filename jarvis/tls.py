"""Self-signed TLS for the JARVIS daemon.

Why this exists: headset browsers (Meta Quest, Vision Pro, Pico) only expose
``navigator.xr`` in a **secure context**. ``http://127.0.0.1`` counts as secure,
``http://192.168.x.x`` does not. Without TLS the VR button can never light up on
a headset, no matter what the JavaScript does.

This module mints a local self-signed certificate covering localhost and every
LAN address of this machine, so the daemon can be started with::

    JARVIS_TLS=1 python -m jarvis.daemon

The browser will show a certificate warning once. Accept it and the page becomes
a secure context. That is the only way to get WebXR without a public domain.
"""
from __future__ import annotations

import datetime
import ipaddress
import logging
import os
import socket
import stat
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("jarvis.tls")

TLS_DIR = Path.home() / ".jarvis" / "tls"
CERT_PATH = TLS_DIR / "cert.pem"
KEY_PATH = TLS_DIR / "key.pem"


def local_ipv4_addresses() -> list[str]:
    """Best-effort list of this machine's IPv4 addresses, never raised."""
    found: set[str] = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            found.add(info[4][0])
    except Exception:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        found.add(probe.getsockname()[0])
        probe.close()
    except Exception:
        pass
    return sorted(found)


def _generate(cert_path: Path, key_path: Path) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS-OS"),
            x509.NameAttribute(NameOID.COMMON_NAME, "jarvis.local"),
        ]
    )

    san = [x509.DNSName("localhost"), x509.DNSName("jarvis.local")]
    for addr in local_ipv4_addresses():
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(addr)))
        except ValueError:
            continue

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    try:
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def ensure_certificate(force: bool = False) -> Optional[Tuple[str, str]]:
    """Return ``(cert_path, key_path)`` or ``None`` if TLS cannot be prepared."""
    try:
        if force or not (CERT_PATH.exists() and KEY_PATH.exists()):
            _generate(CERT_PATH, KEY_PATH)
        return str(CERT_PATH), str(KEY_PATH)
    except ImportError:
        logger.warning(
            "TLS requested but the 'cryptography' package is missing. "
            "Install it with: pip install cryptography"
        )
    except Exception as exc:  # pragma: no cover - platform dependent
        logger.warning("Could not create a self-signed certificate: %s", exc)
    return None


def wrap_server_socket(server, cert_file: str, key_file: str):
    """Wrap an HTTPServer's socket in TLS and return the server."""
    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
