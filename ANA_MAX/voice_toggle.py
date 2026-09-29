"""
ANA MAX - Voice Auto-Start Script with Persistent Agent Integration

Starts the local voice helper and keeps the process alive.
Integrates with persistent agent mode for deterministic behavior.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from tools.edge_tts_voice import EdgeTTSVoice

# Persistent agent logging
_ANA_ROOT = Path(__file__).resolve().parent
_LOG_DIR = Path("C:/ANA_MAX/logs")  # Absolute path for consistency
_PERSISTENT_LOG = _LOG_DIR / "persistent_agent_live.log"

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def _log_persistent(message: str, level: str = "INFO") -> None:
    """Write to persistent agent live log."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        # Windows-compatible timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        milliseconds = int(time.time() * 1000) % 1000
        timestamp = f"{timestamp}.{milliseconds:03d}"
        log_entry = f"[{timestamp}] [{level}] VOICE: {message}"
        with open(_PERSISTENT_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
        print(f"[LOG] {log_entry}")  # Debug: print to console
    except Exception as exc:
        logger.error("Failed to write persistent log: %s", exc)
        print(f"[ERROR] Failed to write persistent log: {exc}")


def main() -> int:
    print("\n" + "=" * 70)
    print("ANA MAX - JARVIS VOICE AUTO-START (PERSISTENT AGENT MODE)")
    print("=" * 70 + "\n")
    print("Starting voice engine...")
    
    _log_persistent("Voice system initialization started", "INFO")

    try:
        voice = EdgeTTSVoice(rate=150, volume=0.7)
    except Exception as exc:
        logger.error("Voice startup failed: %s", exc)
        _log_persistent(f"Voice startup failed: {exc}", "ERROR")
        print(f"Fatal voice error: {exc}")
        return 1

    if not voice.enabled:
        print("ERROR: Voice engine failed to initialize.")
        print("Check pyttsx3, the audio output device, and speaker volume.")
        _log_persistent("Voice engine failed to initialize", "ERROR")
        return 1

    print("Voice engine ready.")
    print("   - Voice: Microsoft Zira if available")
    print("   - Rate: 150")
    print("   - Volume: 0.7")
    print()
    
    _log_persistent("Voice engine initialized successfully", "SUCCESS")

    try:
        voice.execute(
            "speak",
            text="ANA MAX Agent Online. Voice system activated in persistent mode.",
        **{"async": False},
        )
        _log_persistent("Voice greeting executed", "SUCCESS")
    except Exception as exc:
        logger.warning("Greeting failed: %s", exc)
        _log_persistent(f"Voice greeting failed: {exc}", "WARN")
        print(f"Warning: Greeting failed - {exc}")

    print("=" * 70)
    print("VOICE IS ON - PERSISTENT AGENT MODE")
    print("=" * 70)
    print()
    print("How it works:")
    print("  - Voice operates in persistent agent mode")
    print("  - All voice operations logged to persistent_agent_live.log")
    print("  - Deterministic behavior across all backends")
    print("  - Close this window or press Ctrl+C to disable voice.")
    print("=" * 70)
    print()
    
    _log_persistent("Voice system active - awaiting commands", "INFO")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        try:
            voice.execute("speak", text="Voice deactivated. Awaiting next instruction.")
            _log_persistent("Voice system deactivated by user", "INFO")
        except Exception as exc:
            logger.debug("Shutdown message failed: %s", exc)
            _log_persistent(f"Voice shutdown message failed: {exc}", "WARN")
        print("\nVoice deactivated.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
