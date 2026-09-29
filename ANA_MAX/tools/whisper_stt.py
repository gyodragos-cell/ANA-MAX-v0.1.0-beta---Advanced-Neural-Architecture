"""
ANA MAX - Whisper STT (Speech-to-Text) Module
Uses faster-whisper for local, offline transcription.
"""
from __future__ import annotations

import collections
import logging
import numpy as np
import sounddevice as sd
import webrtcvad

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000          # Hz — Whisper native
FRAME_MS = 30                # ms per VAD frame (10, 20 or 30 ms only)
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
SILENCE_FRAMES = 30          # ~900ms silence → end of speech
SPEECH_TRIGGER = 5           # nr of speech frames to trigger recording
MAX_RECORD_FRAMES = 600      # hard cap ~18 sec


def normalize_ro(text: str) -> str:
    """Normalize Romanian diacritics (old ASCII → Unicode)."""
    text = text.strip()
    text = text.replace("t", "t").replace("s", "s")
    text = text.replace("T", "T").replace("S", "S")
    return text


class WhisperSTT:
    def __init__(self, model_size: str = "tiny", device: str = "cpu", language: str | None = None):
        """
        model_size: 'tiny' (fastest, ~39MB) or 'base' (better accuracy, ~74MB).
        Downloads automatically from HuggingFace on first run.
        language: optional language code (e.g., 'en' or 'ro'). If None, attempts to read from config/settings.yaml ui.language.
        """
        # Determine language from config if not provided
        if language is None:
            try:
                import yaml
                from pathlib import Path
                cfg_path = Path(__file__).parent.parent / "config" / "settings.yaml"
                if cfg_path.exists():
                    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
                    language = cfg.get('ui', {}).get('language')
            except Exception:
                language = None

        self.language = (language or '').lower() if language else None

        logger.info("Loading Whisper model '%s'...", model_size)
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.vad = webrtcvad.Vad(2)   # aggressiveness 0-3 (2 = balanced)
        logger.info("Whisper STT ready. Language=%s", self.language or 'auto')

    def _record_utterance(self) -> np.ndarray | None:
        """
        Blocks until the user speaks and then stops talking.
        Returns a float32 audio array at 16kHz, or None if nothing detected.
        """
        ring = collections.deque(maxlen=15)   # pre-speech ring buffer
        frames: list[bytes] = []
        speech_frames = 0
        silence_frames = 0
        recording = False

        print("  [MIC] Ascult... (vorbeste acum)")

        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                               dtype="int16", blocksize=FRAME_SAMPLES) as stream:
            for _ in range(MAX_RECORD_FRAMES):
                data, _ = stream.read(FRAME_SAMPLES)
                pcm = bytes(data)

                try:
                    is_speech = self.vad.is_speech(pcm, SAMPLE_RATE)
                except Exception:
                    is_speech = False

                if recording:
                    frames.append(pcm)
                    if is_speech:
                        silence_frames = 0
                    else:
                        silence_frames += 1
                        if silence_frames >= SILENCE_FRAMES:
                            break
                else:
                    ring.append(pcm)
                    if is_speech:
                        speech_frames += 1
                        if speech_frames >= SPEECH_TRIGGER:
                            recording = True
                            frames.extend(ring)
                            ring.clear()
                    else:
                        speech_frames = 0

        if not frames:
            return None

        raw = b"".join(frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    def listen(self) -> str:
        """
        Block until user speaks, transcribe and return text.
        Returns empty string if nothing was captured.
        """
        audio = self._record_utterance()
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            return ""

        logger.info("Transcribing %d samples...", len(audio))
        # Force Romanian language for better accuracy (fallback to config or 'ro')
        lang_param = self.language if self.language else "ro"
        segments, _ = self.model.transcribe(
            audio,
            language=lang_param,
            beam_size=5,
            task="transcribe",
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300}
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        # Normalize Romanian diacritics
        text = normalize_ro(text)
        logger.info("Transcribed: %s", text)
        return text
