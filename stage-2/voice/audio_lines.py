"""Play a random bundled sound from a category using an installed audio player.

Features safe non-blocking Popen playback, single-warning player checks,
and recording collision prevention.
"""
import logging
import random
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("jarvis.audio_out")
LINES_DIR = Path(__file__).resolve().parent / "lines"

_warned_no_player = False
_current_process: Optional[subprocess.Popen] = None


def is_playing() -> bool:
    """Return True if an audio playback subprocess is currently active."""
    global _current_process
    if _current_process is None:
        return False
    poll_result = _current_process.poll()
    if poll_result is None:
        return True
    _current_process = None
    return False


def wait_playback() -> None:
    """Wait for any currently playing audio track to finish."""
    global _current_process
    if _current_process is not None:
        try:
            _current_process.wait()
        except Exception:
            pass
        _current_process = None


def find_audio_player() -> Optional[List[str]]:
    """Determine available system audio command for MP3 playback.

    Order: mpg123 -> ffplay -> afplay
    """
    p = shutil.which("mpg123")
    if p:
        return [p, "-q"]
    p = shutil.which("ffplay")
    if p:
        return [p, "-nodisp", "-autoexit", "-loglevel", "error"]
    p = shutil.which("afplay")
    if p:
        return [p]
    return None


def speak_line(category: str, block: bool = False) -> bool:
    """Play a random line from the given category using non-blocking Popen.

    If no player is available, logs a friendly warning once and returns False (never crashes).
    """
    global _warned_no_player, _current_process

    folder = LINES_DIR / category
    if not folder.exists():
        logger.debug("Sound folder not found: %s", folder)
        return False

    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in {".wav", ".mp3", ".ogg"})
    if not files:
        logger.debug("No audio files in category %s", category)
        return False

    player_cmd = find_audio_player()
    if not player_cmd:
        if not _warned_no_player:
            logger.warning(
                "No audio player found (mpg123, ffplay, or afplay). "
                "Sound playback disabled. Install mpg123 or ffmpeg to enable."
            )
            _warned_no_player = True
        return False

    selected_file = random.choice(files)
    logger.info("Playing line (%s): %s", category, selected_file.name)

    try:
        cmd = player_cmd + [str(selected_file)]
        _current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if block:
            wait_playback()
        return True
    except Exception as e:
        logger.error("Failed to start audio playback: %s", e)
        return False
