"""
ANA MAX - Voice Auto-Start Script

Starts the local voice helper and keeps the process alive.
"""

from __future__ import annotations

import logging
import sys
import time

from tools.edge_tts_voice import EdgeTTSVoice

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    print("\n" + "=" * 70)
    print("ANA MAX - JARVIS VOICE AUTO-START")
    print("=" * 70 + "\n")
    print("Starting voice engine...")

    try:
        voice = EdgeTTSVoice(rate=150, volume=0.7)
    except Exception as exc:
        logger.error("Voice startup failed: %s", exc)
        print(f"Fatal voice error: {exc}")
        return 1

    if not voice.enabled:
        print("ERROR: Voice engine failed to initialize.")
        print("Check pyttsx3, the audio output device, and speaker volume.")
        return 1

    print("Voice engine ready.")
    print("   - Voice: Microsoft Zira if available")
    print("   - Rate: 150")
    print("   - Volume: 0.7")
    print()

    try:
        voice.execute(
            "speak",
            text="Voice is now on. I will speak Qoder messages while you test demos.",
        **{"async": False},
        )
    except Exception as exc:
        logger.warning("Greeting failed: %s", exc)
        print(f"Warning: Greeting failed - {exc}")

    print("=" * 70)
    print("VOICE IS ON")
    print("=" * 70)
    print()
    print("How it works:")
    print("  - Qoder can be used as voice/demo companion.")
    print("  - Keep code changes in trusted agents only.")
    print("  - Close this window or press Ctrl+C to disable voice.")
    print("=" * 70)
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        try:
            voice.execute("speak", text="Voice deactivated. See you later.")
        except Exception as exc:
            logger.debug("Shutdown message failed: %s", exc)
        print("\nVoice deactivated.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
