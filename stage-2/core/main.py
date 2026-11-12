"""Stage 2: local transcription plus a random JARVIS acknowledgement sound."""
import sys
import time
from pathlib import Path

# Add project root to sys.path so jarvis core package is resolvable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from jarvis.audio_in import record_fixed
from jarvis.stt import transcribe
from voice.audio_lines import speak_line

DURATION_SECONDS = 3.0


def record_once() -> str:
    print(f"Listening for {int(DURATION_SECONDS)} seconds...")
    audio = record_fixed(seconds=DURATION_SECONDS)
    return transcribe(audio)


def main() -> None:
    print("JARVIS Stage 2 initializing...")
    from jarvis.stt import preload_model
    preload_model()
    print("JARVIS Stage 2 ready. Press Ctrl-C to exit.")
    try:
        while True:
            text = record_once()
            if text:
                print(f"You: {text}")
                speak_line("task.acknowledge")
            else:
                print("(No speech detected)")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nJARVIS stopped.")


if __name__ == "__main__":
    main()
