"""
ANA MAX - Live Voice Agent
Full pipeline: Mic -> Whisper STT -> ANA MAX API -> Kokoro TTS

Usage:
    python live_voice_agent.py
"""
from __future__ import annotations

import sys
import os
import json
import logging
import urllib.request
import unicodedata

# ── path setup ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from tools.whisper_stt import WhisperSTT
from tools.kokoro_voice import KokoroVoice
from tools.watchdog_bus import bus

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", force=True)
logger = logging.getLogger(__name__)

_ANA_PORT = os.environ.get("ANA_PORT", "8767")
ANA_URL = f"http://127.0.0.1:{_ANA_PORT}/mcp"
VOICE_PUSH_URL = f"http://127.0.0.1:{_ANA_PORT}/voice/push"
BACKEND_LABEL = os.environ.get("ANA_BACKEND", "openrouter")


def remove_diacritics(text: str) -> str:
    """Remove diacritics from text for PowerShell compatibility."""
    # Normalize to NFD (decomposed form), then remove combining diacritical marks
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


def ask_ana(text: str) -> str:
    """Send text to ANA MAX and return the response string."""
    logger.info("[VOICE API START] Sending to ANA: %s", text[:100])
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "ana.chat",
        "params": {"message": text}
    }).encode("utf-8")

    req = urllib.request.Request(
        ANA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        logger.info("[VOICE API END] Success - response length: %d", len(str(data)))
    except Exception as e:
        logger.error("[VOICE API ERROR] ANA request failed (port %s, backend %s): %s", _ANA_PORT, BACKEND_LABEL, e)
        error_msg = f"Nu am putut contacta ANA MAX pe portul {_ANA_PORT} ({BACKEND_LABEL}). Verifica daca serverul ruleaza."
        return remove_diacritics(error_msg)

    result = data.get("result", {})
    if isinstance(result, str):
        return remove_diacritics(result)
    if isinstance(result, dict):
        response = (result.get("response")
                or result.get("output")
                or result.get("content")
                or json.dumps(result, ensure_ascii=False))
        return remove_diacritics(response)
    return remove_diacritics(str(result))

def push_to_browser(user_text: str, ana_text: str):
    """Trimite conversatia vocala in UI-ul web."""
    logger.info("[VOICE PUSH] Sending to browser: user=%d chars, ana=%d chars", len(user_text), len(ana_text))
    try:
        payload = json.dumps({"user": user_text, "ana": ana_text}).encode("utf-8")
        req = urllib.request.Request(
            VOICE_PUSH_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=2)
        logger.info("[VOICE PUSH] Success")
    except Exception as e:
        logger.error("[VOICE PUSH ERROR] Eroare la push catre browser (port %s): %s", _ANA_PORT, e)

def main() -> int:
    print("=" * 60)
    print(f"  ANA MAX - LIVE VOICE AGENT  [{BACKEND_LABEL.upper()} :{_ANA_PORT}]")
    print("  Mic -> Whisper -> ANA -> Kokoro TTS")
    print(f"  API:  {ANA_URL}")
    print(f"  UI:   {VOICE_PUSH_URL.rsplit('/',1)[0]}/chat")
    print("=" * 60)
    print("Se incarca modelele... (prima rulare poate dura 30-60 sec)")
    print()
    logger.info("[VOICE START] Initializing voice agent (port=%s, backend=%s)", _ANA_PORT, BACKEND_LABEL)

    # Start watchdog bus for event publishing
    try:
        bus.start()
        logger.info("[VOICE START] Watchdog bus started")
    except Exception as e:
        logger.error("[VOICE START] Failed to start watchdog bus: %s", e)

    # Detect if auto-started (by .bat or voice_command_router) vs manual
    auto_mode = os.environ.get("ANA_VOICE_AUTO", "0").strip().lower() in ("1", "yes", "true")
    
    # Single command mode: stop after one response
    single_command = os.environ.get("ANA_VOICE_SINGLE", "0").strip().lower() in ("1", "yes", "true")

    try:
        # Model "medium" pentru acuratete 10× mai buna pe romana
        # Limba romana fortata pentru detectare corecta
        logger.info("[VOICE STT INIT] Loading Whisper medium model (language=ro)...")
        stt = WhisperSTT(model_size="medium", device="cpu", language="ro")
        logger.info("[VOICE STT INIT] Whisper loaded successfully")
    except Exception as e:
        logger.error("[VOICE STT ERROR] Failed to load Whisper: %s", e)
        print(f"[EROARE STT] {e}")
        return 1

    try:
        logger.info("[VOICE TTS INIT] Loading Kokoro TTS...")
        tts = KokoroVoice()
        logger.info("[VOICE TTS INIT] Kokoro loaded successfully")
    except Exception as e:
        logger.error("[VOICE TTS ERROR] Failed to load Kokoro: %s", e)
        print(f"[EROARE TTS] {e}")
        return 1

    # Voce unificata Kokoro: af_bella functioneaza bine si pentru RO si EN.
    chosen_voice = "af_bella"

    # Feedback instant: beep scurt (winsound, zero dependente, Windows-nativ)
    # apoi "Te ascult" prin Kokoro (vocea ANA).
    print()
    try:
        import winsound
        print("[BEEP] Ton confirmare...")
        winsound.Beep(800, 150)
    except Exception:
        pass  # winsound indisponibil pe non-Windows

    if auto_mode:
        tts.speak("Te ascult. Vorbeste.", voice=chosen_voice)
    else:
        tts.speak("ANA voice agent activ. Te ascult. Vorbeste.", voice=chosen_voice)

    print()
    if single_command:
        print("Gata! Vorbeste cu ANA. Se va opri dupa o comanda.")
    else:
        print("Gata! Vorbeste cu ANA. Ctrl+C pentru a opri.")
    print("-" * 60)

    try:
        command_count = 0
        while True:
            # 1. Listen
            logger.info("[VOICE LOOP] Listening...")
            text = stt.listen()
            if not text:
                logger.warning("[VOICE LOOP] No speech detected, retrying...")
                continue

            logger.info("[VOICE STT] Transcribed: %s", text)
            print(f"\n[TU]  {text}")

            # 2. Ask ANA
            print("[ANA] Se gandeste...")
            logger.info("[VOICE LOOP] Sending to ANA...")
            answer = ask_ana(text)
            logger.info("[VOICE LOOP] ANA response: %d chars", len(answer))
            print(f"[ANA] {answer[:200]}{'...' if len(answer) > 200 else ''}")

            # 3. Speak and push to browser
            logger.info("[VOICE TTS] Speaking: %d chars", len(answer[:800]))
            push_to_browser(text, answer)
            tts.speak(answer[:800], voice="af_bella")   # cap la 800 chars TTS
            logger.info("[VOICE TTS] Done")
            
            # Single command mode: exit after first response
            if single_command:
                logger.info("[VOICE STOP] Single command mode - exiting after response")
                print("\n\nComanda executata. Se opreste.")
                tts.speak("Astept urmatoarea instructiune.", voice="af_bella")
                return 0
            
            command_count += 1

    except KeyboardInterrupt:
        logger.info("[VOICE STOP] Interrupted by user")
        print("\n\nOprit de utilizator.")
        tts.speak("La revedere!", voice="af_bella")
        return 0


if __name__ == "__main__":
    sys.exit(main())
