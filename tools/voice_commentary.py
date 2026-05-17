"""
ANA MAX - Voice Commentary Tool (EXPERIMENTAL)
Jarvis-style vocal feedback for tool execution

Ana comentează vocal ce face Qoder în timp real.
Folosit DOAR în ana_dev pentru teste!
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import pyttsx3
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.info("pyttsx3 not installed - voice commentary disabled. Run: pip install pyttsx3")


class VoiceCommentary:
    """
    Ana comentează vocal progresul execuției.
    
    Usage:
        commentary = VoiceCommentary()
        commentary.speak("Am început repararea...")
        commentary.speak("Testez acum...")
        commentary.speak("Gata! Succes!")
    """
    
    def __init__(self, enabled: bool = True, rate: int = 140, volume: float = 0.8):
        """
        Initialize voice commentary.
        
        Args:
            enabled: Enable/disable voice
            rate: Speech rate (words per minute) - 140 = JARVIS-like, calm & friendly
            volume: Volume (0.0 to 1.0)
        """
        self.enabled = enabled and TTS_AVAILABLE
        self.rate = rate
        self.volume = volume
        self._tts = None
        
        if self.enabled:
            self._init_tts()
    
    def _init_tts(self):
        """Initialize TTS engine."""
        try:
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", self.rate)
            self._tts.setProperty("volume", self.volume)
            logger.info(f"Voice commentary initialized (rate={self.rate}, volume={self.volume})")
        except Exception as e:
            logger.warning(f"TTS init failed: {e}")
            self.enabled = False
    
    def speak(self, text: str, block: bool = False):
        """
        Speak commentary text.
        
        Args:
            text: Text to speak
            block: If True, wait until speech finishes
        """
        if not self.enabled or not self._tts:
            return
        
        try:
            self._tts.say(text)
            if block:
                self._tts.runAndWait()
            else:
                # Non-blocking - let it speak in background
                import threading
                thread = threading.Thread(target=self._tts.runAndWait)
                thread.daemon = True
                thread.start()
        except Exception as e:
            logger.warning(f"TTS error: {e}")
    
    def speak_progress(self, step: str, total: Optional[int] = None):
        """
        Speak progress update.
        
        Args:
            step: Current step description
            total: Total steps (optional)
        """
        if total:
            text = f"Step {step} of {total}"
        else:
            text = step
        
        self.speak(text)
    
    def speak_success(self, message: str):
        """Speak success message."""
        self.speak(f"Success! {message}")
    
    def speak_error(self, message: str):
        """Speak error message."""
        self.speak(f"Error! {message}")
    
    def speak_info(self, message: str):
        """Speak info message."""
        self.speak(f"Info: {message}")
    
    def enable(self):
        """Enable voice commentary."""
        self.enabled = True
        if not self._tts:
            self._init_tts()
        logger.info("Voice commentary ENABLED")
    
    def disable(self):
        """Disable voice commentary."""
        self.enabled = False
        logger.info("Voice commentary DISABLED")
    
    def toggle(self):
        """Toggle voice commentary on/off."""
        self.enabled = not self.enabled
        status = "ENABLED" if self.enabled else "DISABLED"
        logger.info(f"Voice commentary {status}")
        return self.enabled


# Singleton instance
_commentary = None


def get_commentary(enabled: bool = True) -> VoiceCommentary:
    """Get or create global voice commentary instance."""
    global _commentary
    if _commentary is None:
        _commentary = VoiceCommentary(enabled=enabled)
    return _commentary
