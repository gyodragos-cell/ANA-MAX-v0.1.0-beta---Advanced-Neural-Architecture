"""
ANA MAX - Edge TTS Voice Tool (experimental)

Natural local voice feedback for ANA MAX tests.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)
logging.getLogger("comtypes").setLevel(logging.WARNING)
logging.getLogger("comtypes.client").setLevel(logging.WARNING)
logging.getLogger("comtypes.client._code_cache").setLevel(logging.WARNING)

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.info("edge-tts not installed - Edge voice disabled")


def _get_live_speak():
    """Import live voice lazily so imports stay quiet."""
    try:
        from tools.live_voice_bridge import speak as live_speak

        return live_speak
    except Exception as exc:
        logger.debug("live_voice_bridge not available: %s", exc)
        return None


class EdgeTTSVoice(Tool):
    """Voice output using local pyttsx3 by default, with Edge TTS support."""

    VOICES = {
        "en-us": "en-US-AriaNeural",
        "en-gb": "en-GB-SoniaNeural",
        "ro-ro": "ro-RO-AlinaNeural",
    }

    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        rate: int = 150,
        volume: float = 0.8,
        use_edge_tts: bool = False,
    ):
        super().__init__()
        self.enabled = True
        self.voice_name = voice
        self.rate = rate
        self.volume = volume
        self.use_edge_tts = use_edge_tts

        self._temp_dir = Path.cwd() / "voice_temp"
        self._temp_dir.mkdir(exist_ok=True)
        self._tts_engine = None
        self._pyttsx3_available = False

        if not use_edge_tts:
            self._init_pyttsx3(rate=rate, volume=volume)

    def _init_pyttsx3(self, rate: int, volume: float):
        try:
            import pyttsx3

            self._tts_engine = pyttsx3.init()
            voices = self._tts_engine.getProperty("voices") or []
            for voice in voices:
                if "Zira" in voice.name:
                    self._tts_engine.setProperty("voice", voice.id)
                    logger.info("Using voice: %s", voice.name)
                    break
            self._tts_engine.setProperty("rate", rate)
            self._tts_engine.setProperty("volume", volume)
            self._pyttsx3_available = True
        except Exception as exc:
            self._tts_engine = None
            self._pyttsx3_available = False
            logger.debug("pyttsx3 unavailable; live voice fallback will be used: %s", exc)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edge_tts_voice",
            description="Natural voice feedback using Edge TTS or local pyttsx3.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operation: speak, list_voices, enable, disable",
                    type="string",
                    required=True,
                    choices=["speak", "list_voices", "enable", "disable"],
                ),
                ToolParameter(
                    name="text",
                    description="Text to speak for the speak operation",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="voice",
                    description="Voice name, for example en-US-AriaNeural",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="async",
                    description="Speak in a background thread and return immediately (default: true)",
                    type="boolean",
                    required=False,
                    default="true",
                ),
            ],
            category="voice",
        )

    def execute(
        self,
        operation: str,
        text: Optional[str] = None,
        voice: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if operation == "speak" and text:
                async_mode = str(kwargs.get("async", "true")).lower() != "false"
                if async_mode:
                    thread = threading.Thread(
                        target=self._speak,
                        args=(text, voice or self.voice_name),
                        daemon=True,
                    )
                    thread.start()
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"queued": text},
                        message=f"Queued speech: {text[:50]}...",
                    )

                self._speak(text, voice or self.voice_name)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"spoken": text},
                    message=f"Spoke: {text[:50]}...",
                )

            if operation == "list_voices":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"voices": self.VOICES},
                    message="Available voices listed",
                )

            if operation == "enable":
                self.enabled = True
                return ToolResult(status=ToolStatus.SUCCESS, message="Voice enabled")

            if operation == "disable":
                self.enabled = False
                return ToolResult(status=ToolStatus.SUCCESS, message="Voice disabled")

            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")
        except Exception as exc:
            logger.error("Voice tool error: %s", exc)
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _speak(self, text: str, voice: str):
        if not self.enabled:
            return

        if self.use_edge_tts and EDGE_TTS_AVAILABLE:
            self._speak_text(text, voice)
            return

        live_speak = _get_live_speak()
        if live_speak:
            live_speak(text)
        else:
            self._speak_realtime(text)

    def _speak_realtime(self, text: str):
        # Thread-local engine: create, use, and stop per call
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            # Select voice if available
            voices = engine.getProperty('voices') or []
            for v in voices:
                if 'Zira' in v.name:
                    engine.setProperty('voice', v.id)
                    break
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:
            logger.debug("pyttsx3 realtime fallback failed: %s", exc)
        except Exception as exc:
            logger.debug("Voice fallback failed: %s", exc)

    def _speak_text(self, text: str, voice: str):
        try:
            timestamp = int(time.time() * 1000)
            temp_file = self._temp_dir / f"voice_{timestamp}.mp3"
            asyncio.run(self._generate_and_play(text, str(temp_file), voice))
            self._cleanup_old_files()
        except Exception as exc:
            logger.warning("Edge TTS speak error: %s", exc)

    async def _generate_and_play(self, text: str, output_file: str, voice: str):
        communicate = edge_tts.Communicate(text, voice, rate=str(self.rate), volume=str(self.volume))
        await communicate.save(output_file)
        self._play_audio(output_file)

    def _play_audio(self, file_path: str):
        try:
            os.startfile(file_path)  # type: ignore[attr-defined]
            time.sleep(5)
        except Exception as exc:
            logger.warning("Failed to play audio: %s", exc)

    def _cleanup_old_files(self):
        try:
            voice_files = sorted(
                self._temp_dir.glob("voice_*.mp3"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            for old_file in voice_files[5:]:
                old_file.unlink()
        except Exception as exc:
            logger.debug("Cleanup error: %s", exc)
