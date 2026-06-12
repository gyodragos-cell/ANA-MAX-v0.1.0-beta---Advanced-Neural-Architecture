"""
ANA MAX - Live Voice Bridge

Small, low-noise wrapper around pyttsx3 for local voice feedback.
This module is intentionally lazy: importing it must not start speech.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
import atexit
import tempfile
import unicodedata
from pathlib import Path

try:
    import pyttsx3
except Exception:  # pragma: no cover - depends on local voice packages
    pyttsx3 = None

logger = logging.getLogger(__name__)

# comtypes can emit verbose DEBUG messages for optional SAPI events.
logging.getLogger("comtypes").setLevel(logging.WARNING)

_engine = None
_engine_lock = threading.Lock()
_enabled = True
_pyttsx3_broken = False


def _ascii_safe_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _create_engine(rate: int = 150, volume: float = 0.7):
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 is not installed")
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)

    voices = engine.getProperty("voices") or []
    for voice in voices:
        if "Zira" in voice.name:
            engine.setProperty("voice", voice.id)
            break

    return engine


def _speak_with_system_speech(text: str, rate: int = 0, volume: int = 80):
    """Speak through .NET System.Speech when pyttsx3/SAPI COM is unavailable."""
    if not text:
        return

    text = _ascii_safe_text(text)
    voice_dir = Path.cwd() / "voice_temp"
    voice_dir.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8", dir=voice_dir) as handle:
        handle.write(text)
        temp_path = Path(handle.name)

    literal_path = str(temp_path).replace("'", "''")
    command = (
        "Add-Type -AssemblyName System.Speech; "
        f"$path = '{literal_path}'; "
        "$text = Get-Content -Raw -LiteralPath $path; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {int(rate)}; "
        f"$s.Volume = {int(volume)}; "
        "$s.Speak($text); "
        "$s.Dispose(); "
        "Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def get_engine():
    """Return the shared pyttsx3 engine, creating it on first use."""
    global _engine, _pyttsx3_broken
    if _pyttsx3_broken:
        raise RuntimeError("pyttsx3 is unavailable in this session")
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                try:
                    _engine = _create_engine()
                except Exception:
                    _pyttsx3_broken = True
                    raise
        logger.info("Live voice bridge initialized")
        atexit.register(_engine.stop)
    return _engine


class LiveVoiceBridge:
    """Compatibility wrapper used by older callers."""

    def __init__(self, rate: int = 150, volume: float = 0.7):
        self.enabled = True
        self.rate = rate
        self.volume = volume
        try:
            self.engine = _create_engine(rate=rate, volume=volume)
        except Exception as exc:
            logger.warning("pyttsx3 engine unavailable, using System.Speech fallback: %s", exc)
            self.engine = None

    def speak(self, text: str):
        if not self.enabled or not text:
            return
        with _engine_lock:
            if self.engine is not None:
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                _speak_with_system_speech(text, rate=0, volume=int(self.volume * 100))

    def enable(self):
        self.enabled = True
        print("Voice enabled")

    def disable(self):
        self.enabled = False
        print("Voice disabled")

    def stop(self):
        return None


def speak(text: str):
    """Speak text immediately. Errors are logged without noisy tracebacks."""
    if not _enabled or not text:
        return

    global _pyttsx3_broken
    if _pyttsx3_broken:
        _speak_with_system_speech(text)
        return

    try:
        engine = get_engine()
        with _engine_lock:
            engine.say(text)
            engine.runAndWait()
    except Exception as exc:
        _pyttsx3_broken = True
        logger.warning("pyttsx3 voice failed, using System.Speech fallback: %s", exc)
        try:
            _speak_with_system_speech(text)
        except Exception as fallback_exc:
            logger.warning("Voice fallback failed: %s", fallback_exc)
            print(f"Voice error: {fallback_exc}")


def speak_async(text: str):
    """Speak text in a background thread."""
    if not text:
        return
    thread = threading.Thread(target=speak, args=(text,), daemon=True)
    thread.start()


def get_live_voice():
    """Return a compatibility LiveVoiceBridge instance."""
    return LiveVoiceBridge()


def enable():
    global _enabled
    _enabled = True
    print("Voice enabled")


def disable():
    global _enabled
    _enabled = False
    print("Voice disabled")


def cleanup():
    """Placeholder for callers that expect a cleanup hook."""
    logger.info("Voice cleanup complete")


if __name__ == "__main__":
    print("Testing live voice bridge...\n")
    speak("Hello. This is the live voice bridge working.")
    time.sleep(1)
    speak("Test complete. Voice bridge is ready.")
    print("\nTest complete. Voice bridge is working.")
