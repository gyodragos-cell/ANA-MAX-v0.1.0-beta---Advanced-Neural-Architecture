"""
ANA MAX - Advanced Voice Bridge (Kokoro TTS)
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from tools.kokoro_voice import KokoroVoice

BASE_DIR = Path(__file__).resolve().parent
QUEUE_FILE = BASE_DIR / "voice_queue.txt"

def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in lines if line).strip()
    return cleaned

def speak_queue(voice: KokoroVoice, last_pos: int) -> int:
    QUEUE_FILE.touch(exist_ok=True)
    with QUEUE_FILE.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(last_pos)
        new_text = normalize_text(handle.read())
        last_pos = handle.tell()

    if new_text:
        # We only speak the new text
        voice.speak(new_text, voice="af_bella", speed=1.0)
    
    return last_pos

def main() -> int:
    print("=" * 70)
    print("ANA MAX - ADVANCED VOICE BRIDGE (KOKORO-ONNX)")
    print("=" * 70)
    print("Initializing high quality local voice engine...")
    
    try:
        voice = KokoroVoice()
    except Exception as e:
        print(f"Eroare fatala la incarcarea vocii: {e}")
        return 1

    QUEUE_FILE.touch(exist_ok=True)
    last_queue_pos = QUEUE_FILE.stat().st_size

    print(f"Voice ready. Listening to queue: {QUEUE_FILE}")
    print("=" * 70)
    
    voice.speak("Modulul de voce avansat a fost pornit.", voice="af_bella", speed=1.0)

    try:
        while True:
            last_queue_pos = speak_queue(voice, last_queue_pos)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nOprit.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
