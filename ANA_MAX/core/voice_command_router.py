"""
ANA MAX - Voice Command Router

Detecteaza comenzi vocale scrise in chat (ex: "activeaza voce", "stop voice")
si executa actiunea direct, fara sa mai treaca prin LLM:

    "activeaza voce" / "start voice" / "porneste vocea" -> porneste live_voice_agent
    "opreste voce"    / "stop voice"  / "dezactiveaza vocea" -> opreste live_voice_agent

Modulul porneste live_voice_agent.py ca subproces in background folosind
acelasi Python (sys.executable) si mostenind env-ul serverului (ANA_PORT,
ANA_BACKEND), ca sa se lege la backend-ul corect.

PID-ul procesului activ e salvat in logs/live_voice_agent.pid.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
LIVE_VOICE_SCRIPT = BASE_DIR / "live_voice_agent.py"
PID_FILE = BASE_DIR / "logs" / "live_voice_agent.pid"

# ------------------------------------------------------------------ #
# Detectie comenzi
# ------------------------------------------------------------------ #

# Cuvinte-cheie pentru activare (ro + en), VARIANTE ASCII DOAR.
# Diacriticele sunt stripate inainte de match (vezi _strip_diacritics), deci
# regex-ul construit aici trebuie sa contina doar litere simple.
_START_WORDS = [
    "activeaza", "activare", "activ",      # activeaza / activare
    "porneste", "pornire", "porn",         # porneste
    "start", "enable", "turn on",
]
_STOP_WORDS = [
    "opreste", "opresc",                   # opreste
    "dezactiveaza", "dezactivare",
    "stop", "disable", "turn off",
    "inchide", "inchid",                   # inchide vocea
]
_VOICE_WORDS = ["voce", "voice", "mic", "microfon", "ascult", "listen"]

_START_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(w) for w in _START_WORDS)
    + r")\w*\b[\s\-]+\b(?:"
    + "|".join(re.escape(w) for w in _VOICE_WORDS)
    + r")\w*\b",
    re.IGNORECASE,
)
_STOP_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(w) for w in _STOP_WORDS)
    + r")\w*\b[\s\-]+\b(?:"
    + "|".join(re.escape(w) for w in _VOICE_WORDS)
    + r")\w*\b",
    re.IGNORECASE,
)


def detect_voice_command(message: str) -> Optional[str]:
    """Returneaza 'start' / 'stop' / None in functie de continutul mesajului.

    Stop are prioritate peste start (ca sa nu oprim si pornim simultan).
    """
    if not message:
        return None
    text = _strip_diacritics(message).lower()
    if _STOP_RE.search(text):
        return "stop"
    if _START_RE.search(text):
        return "start"
    return None


def _strip_diacritics(text: str) -> str:
    """Inlocuieste diacriticele romanesti cu echivalente ASCII."""
    mapping = {
        "a": "a", "A": "A",
        "a": "a", "A": "A",
        "i": "i", "I": "I",
        "s": "s", "S": "S",
        "t": "t", "T": "T",
    }
    for src, dst in mapping.items():
        text = text.replace(src, dst)
    return text


# ------------------------------------------------------------------ #
# Gestiune proces live_voice_agent
# ------------------------------------------------------------------ #

def _read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip() or "0") or None
    except (OSError, ValueError):
        return None


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'alive' }}"],
                capture_output=True, text=True, timeout=3,
            )
            return "alive" in (result.stdout or "")
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> bool:
    """Opreste procesul dupa PID. Returneaza True daca a fost oprit cu succes."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                capture_output=True, timeout=5,
            )
        else:
            os.kill(pid, 9)
        logger.info("Voice agent PID %s terminated", pid)
        return True
    except Exception as exc:
        logger.warning("Failed to kill voice agent PID %s: %s", pid, exc)
        return False


def is_voice_agent_running() -> bool:
    """Returneaza True daca live_voice_agent.py ruleaza acum (PID valid in fisier)."""
    pid = _read_pid()
    if pid is None:
        return False
    if _is_pid_alive(pid):
        return True
    # PID mort - curatam fisierul ca sa nu ramana stale.
    try:
        PID_FILE.unlink()
    except OSError:
        pass
    return False


def start_voice_agent(auto_listen: bool = True) -> dict:
    """Porneste live_voice_agent.py in background.

    Returneaza un dict cu status, mesaj, si detalii (pid, already_running).
    Idempotent: daca ruleaza deja, nu porneste un al doilea proces.
    """
    if is_voice_agent_running():
        pid = _read_pid()
        logger.info("Voice agent already running (PID %s)", pid)
        return {
            "status": "already_running",
            "message": "Vocea ruleaza deja.",
            "pid": pid,
        }

    if not LIVE_VOICE_SCRIPT.exists():
        msg = f"live_voice_agent.py nu exista la {LIVE_VOICE_SCRIPT}"
        logger.error(msg)
        return {"status": "error", "message": msg}

    # Asiguram directorul logs/ exista
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Env: mostenim + marcam modul auto-listen ca sa nu repete greeting lung
    env = os.environ.copy()
    if auto_listen:
        env["ANA_VOICE_AUTO"] = "1"

    try:
        # Pe Windows: fereastra noua vizibila (ca sa vada userul ca asculta),
        # dar detasata de server ca sa nu blocheze Flask.
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

        proc = subprocess.Popen(
            [sys.executable, str(LIVE_VOICE_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as exc:
        msg = f"Eroare la pornirea live_voice_agent: {exc}"
        logger.exception(msg)
        return {"status": "error", "message": msg}

    # Salvam PID-ul
    try:
        PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    except OSError as exc:
        logger.warning("Nu am putut scrie PID file %s: %s", PID_FILE, exc)

    logger.info("Voice agent started (PID %s, auto_listen=%s)", proc.pid, auto_listen)
    return {
        "status": "started",
        "message": "Vocea a fost activata.",
        "pid": proc.pid,
    }


def stop_voice_agent() -> dict:
    """Opreste live_voice_agent.py daca ruleaza."""
    pid = _read_pid()
    if pid is None:
        return {"status": "not_running", "message": "Vocea nu ruleaza."}

    if not _is_pid_alive(pid):
        # Proces mort - curatam fisierul
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        return {"status": "not_running", "message": "Vocea nu ruleaza (proces mort, curatat)."}

    killed = _kill_pid(pid)
    try:
        PID_FILE.unlink()
    except OSError:
        pass

    if killed:
        logger.info("Voice agent stopped (PID %s)", pid)
        return {"status": "stopped", "message": "Vocea a fost dezactivata.", "pid": pid}
    return {"status": "error", "message": f"Nu am putut opri procesul PID {pid}.", "pid": pid}


# ------------------------------------------------------------------ #
# Handler unic
# ------------------------------------------------------------------ #

def handle_voice_command(command: str, message: str = "") -> dict:
    """Executa comanda vocala ('start' sau 'stop') si returneaza raspunsul.

    Returneaza intotdeauna un dict cu 'output' (text pentru chat) si 'success'.
    Nu ridica exceptii.
    """
    command = (command or "").strip().lower()
    logger.info("Voice command received: %s (raw=%r)", command, message[:80])

    try:
        if command == "start":
            result = start_voice_agent(auto_listen=True)
            status = result.get("status")
            if status == "started":
                output = ("Vocea este activa. Te ascult.\n"
                         "Vorbeste la microfon - ANA te aude si raspunde cu voce.\n"
                         "(Scrie 'opreste vocea' pentru a dezactiva.)")
            elif status == "already_running":
                output = "Vocea ruleaza deja. Te ascult - vorbeste la microfon."
            else:
                output = f"Eroare la activarea vocii: {result.get('message', 'eroare necunoscuta')}"
            return {"output": output, "success": status in {"started", "already_running"}}

        if command == "stop":
            result = stop_voice_agent()
            status = result.get("status")
            if status in {"stopped", "not_running"}:
                output = "Vocea a fost dezactivata. Reactiveaza cu 'activeaza vocea'."
                return {"output": output, "success": True}
            return {"output": result.get("message", "Eroare la oprirea vocii."), "success": False}

        return {"output": f"Comanda vocala necunoscuta: {command!r}", "success": False}
    except Exception as exc:
        logger.exception("Voice command handler failed")
        return {"output": f"Eroare interna in voice router: {exc}", "success": False}


def cleanup_stale_pid() -> None:
    """La startup server: curata PID-ul daca procesul e mort."""
    pid = _read_pid()
    if pid is None:
        return
    if not _is_pid_alive(pid):
        try:
            PID_FILE.unlink()
            logger.info("Cleaned stale voice agent PID %s at startup", pid)
        except OSError:
            pass


if __name__ == "__main__":
    # Test rapid din linia de comanda
    import json
    print("=== Test detectie comenzi ===")
    tests = [
        "activeaza vocea",
        "Activeaza vocea te rog",
        "start voice",
        "porneste vocea",
        "opreste vocea",
        "stop voice",
        "disable voice",
        "salut, ce mai faci?",      # nu e comanda
        "vreau sa vorbesc cu tine",  # nu e comanda (fara cuvant cheie)
    ]
    for t in tests:
        print(f"  {t!r:40s} -> {detect_voice_command(t)!r}")
