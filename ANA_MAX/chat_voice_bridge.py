"""
ANA MAX - Chat Voice Bridge

Speaks text copied from chat and lines appended to a local voice queue.
This gives Codex/ANA a practical local bridge without needing access to the
chat application's private internals.
"""

from __future__ import annotations

import argparse
import atexit
import os
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from tools.conversation_audit import append_conversation_audit


BASE_DIR = Path(__file__).resolve().parent
QUEUE_FILE = BASE_DIR / "voice_queue.txt"
LOCK_FILE = BASE_DIR / "logs" / "chat_voice_bridge.pid"


def speak(text: str) -> None:
    raise RuntimeError("Voice speaker is not initialized")


def load_speaker() -> None:
    global speak
    from tools.live_voice_bridge import speak as live_speak

    speak = live_speak


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'alive' }}",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            return False
        return "alive" in result.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_single_instance_lock() -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            existing_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip() or "0")
        except (OSError, ValueError):
            existing_pid = 0
        if existing_pid and existing_pid != os.getpid() and is_process_alive(existing_pid):
            print(f"ANA chat voice bridge already active: pid={existing_pid}")
            return False
        try:
            LOCK_FILE.unlink()
        except OSError:
            return False

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(LOCK_FILE), flags)
    except OSError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    atexit.register(release_single_instance_lock)
    return True


def release_single_instance_lock() -> None:
    try:
        existing_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return
    if existing_pid == os.getpid():
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass


def get_clipboard_text() -> str:
    """Read Windows clipboard text without adding Python dependencies."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""
    return normalize_text(result.stdout)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in lines if line).strip()
    cleaned = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    return cleaned


def should_speak(text: str, max_chars: int) -> bool:
    if not text:
        return False
    if len(text) > max_chars:
        return False
    return not contains_secret_words(text)


def contains_secret_words(text: str) -> bool:
    lowered = text.lower()
    secret_words = ("api key", "password", "token", "secret", "private key")
    return any(word in lowered for word in secret_words)


def chunk_text(text: str, chunk_chars: int) -> list[str]:
    cleaned = normalize_text(text)
    limit = max(120, int(chunk_chars or 700))
    chunks: list[str] = []
    while cleaned:
        if len(cleaned) <= limit:
            chunks.append(cleaned)
            break
        split_at = cleaned.rfind(" ", 0, limit)
        if split_at < max(80, limit // 2):
            split_at = limit
        chunks.append(cleaned[:split_at].strip())
        cleaned = cleaned[split_at:].strip()
    return [chunk for chunk in chunks if chunk]


def speak_readout(text: str, *, max_chars: int, full_readout: bool, full_max_chars: int, chunk_chars: int) -> bool:
    if not text or contains_secret_words(text):
        return False
    if not full_readout:
        if len(text) > max_chars:
            return False
        speak(text)
        return True
    capped = text[: max(max_chars, int(full_max_chars or max_chars))]
    for chunk in chunk_text(capped, chunk_chars):
        speak(chunk)
    return bool(capped)


def audit_bridge_text(source: str, text: str, *, spoken: bool, max_chars: int) -> None:
    if not text:
        return
    try:
        append_conversation_audit(
            source,
            text,
            spoken=spoken,
            metadata={"bridge": "chat_voice_bridge"},
            max_chars=max_chars,
        )
    except Exception:
        # Audit is evidence only; voice must not stop if the file is locked.
        return


def speak_queue(last_pos: int, max_chars: int, *, full_readout: bool, full_max_chars: int, chunk_chars: int) -> int:
    QUEUE_FILE.touch(exist_ok=True)
    with QUEUE_FILE.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(last_pos)
        new_text = normalize_text(handle.read())
        last_pos = handle.tell()

    if speak_readout(new_text, max_chars=max_chars, full_readout=full_readout, full_max_chars=full_max_chars, chunk_chars=chunk_chars):
        audit_bridge_text("voice_queue", new_text, spoken=True, max_chars=max(full_max_chars, max_chars))
    elif new_text:
        audit_bridge_text("voice_queue_skipped", new_text, spoken=False, max_chars=max(full_max_chars, max_chars))
    return last_pos


def main() -> int:
    parser = argparse.ArgumentParser(description="Speak copied chat text and ANA queue messages.")
    parser.add_argument("--poll", type=float, default=1.0, help="Clipboard polling interval in seconds.")
    parser.add_argument("--max-chars", type=int, default=900, help="Skip copied text longer than this.")
    parser.add_argument("--full-readout", action="store_true", help="Speak long text in chunks instead of skipping it.")
    parser.add_argument("--full-max-chars", type=int, default=6000, help="Safety cap for full readout text.")
    parser.add_argument("--chunk-chars", type=int, default=700, help="Characters per spoken chunk in full readout mode.")
    parser.add_argument("--no-clipboard", action="store_true", help="Only read voice_queue.txt.")
    args = parser.parse_args()

    if not acquire_single_instance_lock():
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    load_speaker()

    QUEUE_FILE.touch(exist_ok=True)
    last_clipboard = ""
    last_queue_pos = QUEUE_FILE.stat().st_size

    print("=" * 70)
    print("ANA MAX - CHAT VOICE BRIDGE")
    print("=" * 70)
    print("Copy any chat text and ANA will speak it.")
    print(f"Queue file: {QUEUE_FILE}")
    print("Secrets are skipped if they contain words like token/password/api key.")
    print("Press Ctrl+C to stop.")
    print("=" * 70)
    speak("ANA chat voice bridge is active.")
    audit_bridge_text(
        "chat_voice_bridge_status",
        "ANA chat voice bridge is active.",
        spoken=True,
        max_chars=args.max_chars,
    )

    try:
        while True:
            last_queue_pos = speak_queue(
                last_queue_pos,
                args.max_chars,
                full_readout=args.full_readout,
                full_max_chars=args.full_max_chars,
                chunk_chars=args.chunk_chars,
            )

            if not args.no_clipboard:
                text = get_clipboard_text()
                if text != last_clipboard and speak_readout(
                    text,
                    max_chars=args.max_chars,
                    full_readout=args.full_readout,
                    full_max_chars=args.full_max_chars,
                    chunk_chars=args.chunk_chars,
                ):
                    last_clipboard = text
                    audit_bridge_text("clipboard_chat", text, spoken=True, max_chars=max(args.full_max_chars, args.max_chars))
                elif text != last_clipboard and text:
                    last_clipboard = text
                    audit_bridge_text("clipboard_chat_skipped", text, spoken=False, max_chars=max(args.full_max_chars, args.max_chars))

            time.sleep(args.poll)
    except KeyboardInterrupt:
        speak("ANA chat voice bridge stopped.")
        audit_bridge_text(
            "chat_voice_bridge_status",
            "ANA chat voice bridge stopped.",
            spoken=True,
            max_chars=args.max_chars,
        )
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
