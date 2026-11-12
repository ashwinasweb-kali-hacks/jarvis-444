"""Unit tests for Stage 2 hardening tasks (headless, no hardware required)."""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jarvis.audio_in import calculate_rms
from jarvis.config import JarvisConfig
from jarvis.stt import filter_text


# 1. Silence detector RMS calculation
def test_calculate_rms_silence():
    zeros = np.zeros(1600, dtype=np.float32)
    assert calculate_rms(zeros) == 0.0


def test_calculate_rms_tone():
    tone = np.ones(1600, dtype=np.float32) * 0.5
    assert np.isclose(calculate_rms(tone), 0.5)


# 2. Hallucination and noise filter
def test_filter_text_valid():
    assert filter_text("Open the blast doors", no_speech_prob=0.1, avg_logprob=-0.2) == "Open the blast doors"


def test_filter_text_high_no_speech_prob():
    assert filter_text("Some phrase", no_speech_prob=0.8) == ""


def test_filter_text_low_logprob():
    assert filter_text("Some phrase", avg_logprob=-2.5) == ""


def test_filter_text_hallucination_blocklist():
    assert filter_text("Thank you.") == ""
    assert filter_text("Thanks for watching!") == ""
    assert filter_text("you") == ""


# 3. Config environment variable overrides
def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("JARVIS_MODEL", "base.en")
    monkeypatch.setenv("JARVIS_SILENCE_MS", "1200")
    monkeypatch.setenv("JARVIS_LOG_LEVEL", "DEBUG")

    cfg = JarvisConfig.from_env()
    assert cfg.model_size == "base.en"
    assert cfg.silence_duration == 1.2
    assert cfg.log_level == "DEBUG"


# 4. Safe audio output without crashes when no player is found
def test_speak_line_no_player():
    sys.path.insert(0, str(REPO_ROOT / "stage-2"))
    from voice.audio_lines import speak_line

    with patch("shutil.which", return_value=None):
        # Should gracefully return False without raising RuntimeError or crashing
        result = speak_line("task.acknowledge")
        assert result is False
