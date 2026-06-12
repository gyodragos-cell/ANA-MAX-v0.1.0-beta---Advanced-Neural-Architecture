"""
ANA MAX - Voice Commentary Tool (experimental)

Simple Jarvis-style vocal feedback for local tool execution.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.info("pyttsx3 not installed - voice commentary disabled")


class VoiceCommentary:
    """Small wrapper around pyttsx3 for progress commentary."""

    def __init__(self, enabled: bool = True, rate: int = 140, volume: float = 0.8):
        self.enabled = enabled and TTS_AVAILABLE
        self.rate = rate
        self.volume = volume
        self._tts = None

        if self.enabled:
            self._init_tts()

    def _init_tts(self):
        try:
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", self.rate)
            self._tts.setProperty("volume", self.volume)
            logger.info("Voice commentary initialized")
        except Exception as exc:
            logger.warning("TTS init failed: %s", exc)
            self.enabled = False

    def speak(self, text: str, block: bool = True):
        if not self.enabled or not self._tts or not text:
            return

        try:
            self._tts.say(text)
            if block:
                self._tts.runAndWait()
        except Exception as exc:
            logger.warning("TTS speak error: %s", exc)

    def speak_progress(self, step: str, total: Optional[int] = None):
        text = f"Step {step} of {total}" if total else step
        self.speak(text)

    def speak_success(self, message: str):
        self.speak(f"Success. {message}")

    def speak_error(self, message: str):
        self.speak(f"Error. {message}")

    def speak_info(self, message: str):
        self.speak(f"Info. {message}")

    def enable(self):
        self.enabled = True
        if not self._tts:
            self._init_tts()
        logger.info("Voice commentary enabled")

    def disable(self):
        self.enabled = False
        logger.info("Voice commentary disabled")

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled


_commentary = None


def get_commentary(enabled: bool = True) -> VoiceCommentary:
    """Get or create the global voice commentary instance."""
    global _commentary
    if _commentary is None:
        _commentary = VoiceCommentary(enabled=enabled, rate=140, volume=0.8)
    return _commentary
