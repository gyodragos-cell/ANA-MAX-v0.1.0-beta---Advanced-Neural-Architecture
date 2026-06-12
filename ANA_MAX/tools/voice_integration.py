"""
ANA MAX - Voice Integration Helper
Adds automatic speech to every console output.
"""

from __future__ import annotations

import builtins
import logging
import threading
from tools.edge_tts_voice import EdgeTTSVoice

_logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Shared voice instance (lazy, thread-safe)
# ----------------------------------------------------------------------
_voice_instance: EdgeTTSVoice | None = None
_voice_lock = threading.Lock()


def _get_voice() -> EdgeTTSVoice | None:
    """Create/reuse a single EdgeTTSVoice instance."""
    global _voice_instance
    if _voice_instance is None:
        with _voice_lock:
            if _voice_instance is None:
                try:
                    _voice_instance = EdgeTTSVoice()
                except Exception as exc:
                    _logger.warning("Voice init failed: %s", exc)
                    _voice_instance = None
    return _voice_instance


# ----------------------------------------------------------------------
# Public helper - print + optional speech
# ----------------------------------------------------------------------
def speak_and_print(*args, **kwargs):
    """Replacement for built-in `print`.  Prints to stdout and, if a voice
    engine is available, speaks the same text asynchronously.
    """
    # Preserve original behaviour
    builtins.__original_print__(*args, **kwargs)

    # Assemble the message exactly as `print` would output it
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    message = sep.join(str(a) for a in args) + end

    voice = _get_voice()
    if voice and voice.enabled:
        # Fire-and-forget - do not block the main thread
        threading.Thread(
            target=lambda: voice.execute("speak", text=message, **{"async": True}),
            daemon=True,
        ).start()
    else:
        _logger.debug("Voice not available - skipping speech.")


# ----------------------------------------------------------------------
# Install the wrapper at import time
# ----------------------------------------------------------------------
def _install_wrapper():
    # Save the original `print` only once
    if not hasattr(builtins, "__original_print__"):
        builtins.__original_print__ = builtins.print
    builtins.print = speak_and_print
    _logger.info("Global print  speak_and_print installed.")


_install_wrapper()
