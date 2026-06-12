"""Compact local conversation audit for ANA voice and chat bridges.

This is private-lab evidence only. It stores text that already entered ANA
through microphone transcription, clipboard readout, or the local voice queue.
It never stores raw audio, screenshots, or unbounded chat dumps.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ANA_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ANA_ROOT / "memory"
DEFAULT_AUDIT_FILE = MEMORY_DIR / "conversation_audit.jsonl"
LATEST_FILE = MEMORY_DIR / "conversation_audit_latest.json"
SECRET_WORDS = ("api key", "password", "token", "secret", "private key", "authorization")
WINDOWS_USER_PATH_RE = re.compile(r"\b[a-z]:\\users\\[^\s\"']+", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in value.split("\n")]
    return " ".join(line for line in lines if line).strip()


def redact_private_text(text: str) -> str:
    return WINDOWS_USER_PATH_RE.sub("local path", str(text or ""))


def contains_sensitive_words(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(word in lowered for word in SECRET_WORDS)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        key_text = str(key)
        if contains_sensitive_words(key_text):
            clean[key_text] = "********"
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            text = redact_private_text(str(value)) if isinstance(value, str) else value
            clean[key_text] = text[:200] if isinstance(text, str) else text
        else:
            clean[key_text] = redact_private_text(str(value))[:200]
    return clean


def build_conversation_entry(
    source: str,
    text: str,
    *,
    spoken: bool = False,
    copied: bool = False,
    submitted: bool = False,
    sensitive_skipped: bool | None = None,
    metadata: dict[str, Any] | None = None,
    max_chars: int = 1200,
) -> dict[str, Any]:
    raw_text = str(text or "")
    normalized = normalize_text(redact_private_text(raw_text))
    sensitive = contains_sensitive_words(raw_text) or contains_sensitive_words(normalized) or bool(sensitive_skipped)
    limit = max(80, int(max_chars or 1200))
    truncated = len(normalized) > limit
    stored_text = "" if sensitive else normalized[:limit]
    return {
        "schema": "ana.conversation_audit.entry.v1",
        "ts": now_iso(),
        "source": str(source or "unknown"),
        "text": stored_text,
        "chars": len(normalized),
        "text_digest": "" if sensitive or not stored_text else _digest(stored_text),
        "spoken": bool(spoken),
        "copied_to_clipboard": bool(copied),
        "submitted_to_focused_window": bool(submitted),
        "sensitive_skipped": bool(sensitive),
        "truncated": bool(truncated and not sensitive),
        "metadata": _compact_metadata(metadata),
    }


def append_conversation_audit(
    source: str,
    text: str,
    *,
    spoken: bool = False,
    copied: bool = False,
    submitted: bool = False,
    sensitive_skipped: bool | None = None,
    metadata: dict[str, Any] | None = None,
    path: Path | None = None,
    max_chars: int = 1200,
) -> dict[str, Any]:
    entry = build_conversation_entry(
        source,
        text,
        spoken=spoken,
        copied=copied,
        submitted=submitted,
        sensitive_skipped=sensitive_skipped,
        metadata=metadata,
        max_chars=max_chars,
    )
    target = path or DEFAULT_AUDIT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    if target == DEFAULT_AUDIT_FILE:
        LATEST_FILE.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def read_conversation_entries(
    *,
    hours: int = 24,
    limit: int = 80,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    target = path or DEFAULT_AUDIT_FILE
    if not target.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours or 24)))
    entries: list[dict[str, Any]] = []
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(str(entry.get("ts") or ""))
        if ts and ts < cutoff:
            break
        entries.append(entry)
        if len(entries) >= max(1, int(limit or 80)):
            break
    entries.reverse()
    return entries


def summarize_conversation_audit(
    *,
    hours: int = 24,
    limit: int = 80,
    path: Path | None = None,
) -> dict[str, Any]:
    entries = read_conversation_entries(hours=hours, limit=limit, path=path)
    sources = Counter(str(entry.get("source") or "unknown") for entry in entries)
    spoken = sum(1 for entry in entries if entry.get("spoken"))
    sensitive = sum(1 for entry in entries if entry.get("sensitive_skipped"))
    latest = entries[-10:]
    return {
        "schema": "ana.conversation_audit.summary.v1",
        "status": "PASS" if entries else "WARN",
        "path": str(path or DEFAULT_AUDIT_FILE),
        "hours": max(1, int(hours or 24)),
        "events": len(entries),
        "spoken_events": spoken,
        "sensitive_skipped": sensitive,
        "sources": dict(sorted(sources.items())),
        "latest": latest,
        "message": (
            f"Conversation audit PASS: {len(entries)} events, {spoken} spoken."
            if entries
            else "Conversation audit WARN: no recent voice or chat evidence."
        ),
    }
