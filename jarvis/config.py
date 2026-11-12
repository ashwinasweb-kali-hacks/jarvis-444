"""Configuration dataclass and logging setup for JARVIS-OS."""
import os
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import sounddevice as sd

from jarvis import voice_models


@dataclass
class JarvisConfig:
    # Model (defaults are the best free models, see jarvis/voice_models.py)
    model_size: str = voice_models.whisper_size()
    compute_type: str = "int8"
    device: str = "cpu"
    language: str = "en"
    stt_model: str = voice_models.default_stt_id()
    tts_model: str = voice_models.default_tts_id()

    # Audio input
    sample_rate: int = 16000
    input_device: Optional[int] = None
    silence_threshold: float = 0.015
    silence_duration: float = 0.8
    min_speech_duration: float = 0.3
    max_duration: float = 15.0

    # STT Filter
    max_no_speech_prob: float = 0.6
    min_avg_logprob: float = -1.5

    # Voice Output
    sound_category: str = "task.acknowledge"
    log_level: str = "INFO"

    # Stage 3 Brain & Persona
    brain_provider: str = "oauth"  # oauth | local | stub
    address: str = "sir"
    daemon_host: str = "0.0.0.0"
    daemon_port: int = 8765

    @classmethod
    def from_env(cls) -> "JarvisConfig":
        """Instantiate config overridden with environment variables if present."""
        cfg = cls()

        if "JARVIS_MODEL" in os.environ:
            cfg.model_size = os.environ["JARVIS_MODEL"]
        if "JARVIS_STT_MODEL" in os.environ:
            cfg.stt_model = os.environ["JARVIS_STT_MODEL"]
        if "JARVIS_TTS_MODEL" in os.environ:
            cfg.tts_model = os.environ["JARVIS_TTS_MODEL"]
        if "JARVIS_COMPUTE_TYPE" in os.environ:
            cfg.compute_type = os.environ["JARVIS_COMPUTE_TYPE"]
        if "JARVIS_DEVICE" in os.environ:
            cfg.device = os.environ["JARVIS_DEVICE"]
        if "JARVIS_INPUT_DEVICE" in os.environ:
            try:
                cfg.input_device = int(os.environ["JARVIS_INPUT_DEVICE"])
            except ValueError:
                pass
        if "JARVIS_SILENCE_THRESHOLD" in os.environ:
            try:
                cfg.silence_threshold = float(os.environ["JARVIS_SILENCE_THRESHOLD"])
            except ValueError:
                pass
        if "JARVIS_SILENCE_MS" in os.environ:
            try:
                cfg.silence_duration = float(os.environ["JARVIS_SILENCE_MS"]) / 1000.0
            except ValueError:
                pass
        if "JARVIS_LOG_LEVEL" in os.environ:
            cfg.log_level = os.environ["JARVIS_LOG_LEVEL"].upper()
        if "JARVIS_BRAIN_PROVIDER" in os.environ:
            cfg.brain_provider = os.environ["JARVIS_BRAIN_PROVIDER"]
        if "JARVIS_ADDRESS" in os.environ:
            cfg.address = os.environ["JARVIS_ADDRESS"]
        if "JARVIS_DAEMON_PORT" in os.environ:
            try:
                cfg.daemon_port = int(os.environ["JARVIS_DAEMON_PORT"])
            except ValueError:
                pass
        if "JARVIS_DAEMON_HOST" in os.environ:
            cfg.daemon_host = os.environ["JARVIS_DAEMON_HOST"]

        return cfg

        return cfg


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure standard logging format and return the root jarvis logger."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=numeric_level,
    )
    return logging.getLogger("jarvis")


def list_audio_devices() -> List[Dict[str, Any]]:
    """Return all available audio input and output devices."""
    try:
        devices = sd.query_devices()
        return list(devices)
    except Exception as e:
        logging.getLogger("jarvis").warning("Failed to query audio devices: %s", e)
        return []


def print_audio_devices() -> None:
    """Friendly display of audio devices for CLI --list-devices."""
    devices = list_audio_devices()
    if not devices:
        print("No audio devices detected.")
        return
    print("\n--- Audio Devices ---")
    for i, dev in enumerate(devices):
        in_ch = dev.get("max_input_channels", 0)
        out_ch = dev.get("max_output_channels", 0)
        marker = ""
        if in_ch > 0 and out_ch > 0:
            marker = "[Input/Output]"
        elif in_ch > 0:
            marker = "[Input]"
        elif out_ch > 0:
            marker = "[Output]"
        print(f"[{i:2d}] {dev.get('name', 'Unknown')} {marker}")
    print("---------------------\n")
