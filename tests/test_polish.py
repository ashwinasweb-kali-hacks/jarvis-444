"""Tests for the polish pass: TLS helper, command index intents, health payload shape."""
from __future__ import annotations

import pytest

from jarvis import brain, tls
from jarvis.brain import respond


# ------------------------------------------------------------------- TLS
def test_local_addresses_always_include_loopback():
    assert "127.0.0.1" in tls.local_ipv4_addresses()


def test_certificate_generation(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setattr(tls, "CERT_PATH", tmp_path / "cert.pem")
    monkeypatch.setattr(tls, "KEY_PATH", tmp_path / "key.pem")

    pair = tls.ensure_certificate(force=True)

    assert pair is not None
    cert_file, key_file = pair
    assert (tmp_path / "cert.pem").exists()
    assert (tmp_path / "key.pem").exists()
    assert "BEGIN CERTIFICATE" in (tmp_path / "cert.pem").read_text()
    assert "BEGIN" in (tmp_path / "key.pem").read_text()


def test_certificate_is_reused_not_regenerated(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setattr(tls, "CERT_PATH", tmp_path / "cert.pem")
    monkeypatch.setattr(tls, "KEY_PATH", tmp_path / "key.pem")

    tls.ensure_certificate()
    first = (tmp_path / "cert.pem").read_text()
    tls.ensure_certificate()
    assert (tmp_path / "cert.pem").read_text() == first


# --------------------------------------------------------- command index
def test_help_intent_opens_index():
    reply = respond("help")
    assert reply.tokens_used == 0
    assert reply.actions[0]["tool"] == "ui"
    assert reply.actions[0]["args"]["action"] == "show_help"


def test_close_help_intent():
    reply = respond("close help")
    assert reply.actions[0]["args"]["action"] == "hide_help"


def test_help_word_inside_sentence_is_not_hijacked():
    """'help' as a substring must not swallow a real question."""
    assert brain._stub_respond("can you help me understand quantum tunnelling").actions[0]["tool"] != "ui"
