"""
Routing helpers for ANA Engineer interactive input.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Optional


ROMANIAN_WEEKDAYS = [
    "luni",
    "marți",
    "miercuri",
    "joi",
    "vineri",
    "sâmbătă",
    "duminică",
]

ROMANIAN_MONTHS = [
    "ianuarie",
    "februarie",
    "martie",
    "aprilie",
    "mai",
    "iunie",
    "iulie",
    "august",
    "septembrie",
    "octombrie",
    "noiembrie",
    "decembrie",
]

TASK_KEYWORDS = {
    "analizeaza", "analizează", "analyze", "debug", "fix", "repara", "repară",
    "repair", "refactor", "creeaza", "creează", "create", "build", "construieste",
    "construiește", "scrie", "write", "cod", "code", "script", "fisier", "fișier",
    "file", "folder", "director", "project", "proiect", "repo", "repository",
    "test", "pytest", "terminal", "command", "comanda", "comandă", "browser",
    "mcp", "bot", "patch", "search in repo", "cauta in repo", "cauta in proiect",
}


def normalize_text(text: str) -> str:
    return (
        (text or "")
        .strip()
        .lower()
        .translate(str.maketrans({
            "ă": "a",
            "â": "a",
            "î": "i",
            "ș": "s",
            "ş": "s",
            "ț": "t",
            "ţ": "t",
        }))
    )


def get_local_runtime_answer(text: str, now: Optional[datetime] = None) -> Optional[str]:
    normalized = normalize_text(text)
    if not normalized:
        return None

    wants_time = any(
        token in normalized for token in [
            "ce ora", "cat e ceasul", "ora este", "ora e", "what time", "current time",
        ]
    )
    wants_day = any(
        token in normalized for token in [
            "ce zi", "zi este", "zi e", "ziua", "weekday", "what day",
        ]
    )
    wants_date = any(
        token in normalized for token in [
            "ce data", "data e", "data este", "today date", "current date",
        ]
    )

    if "azi" in normalized:
        if "zi" in normalized:
            wants_day = True
        if "data" in normalized:
            wants_date = True
        if not wants_day and not wants_date and not wants_time:
            wants_day = True
            wants_date = True

    if not (wants_time or wants_day or wants_date):
        return None

    current = now or datetime.now().astimezone()
    weekday = ROMANIAN_WEEKDAYS[current.weekday()]
    month = ROMANIAN_MONTHS[current.month - 1]
    date_str = f"{current.day} {month} {current.year}"
    time_str = current.strftime("%H:%M")

    parts = []
    if wants_day and wants_date:
        parts.append(f"Astăzi este {weekday}, {date_str}.")
    elif wants_day:
        parts.append(f"Astăzi este {weekday}.")
    elif wants_date:
        parts.append(f"Astăzi este {date_str}.")

    if wants_time:
        parts.append(f"Ora curentă este {time_str}.")

    return " ".join(parts)


def classify_engineer_input(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return "chat"

    if get_local_runtime_answer(text):
        return "local"

    if re.search(r"[A-Za-z]:\\", text):
        return "task"

    if any(keyword in normalized for keyword in TASK_KEYWORDS):
        return "task"

    if normalized.startswith(("salut", "hello", "hi", "hei", "ce poti", "ce poți", "cine esti", "cine ești")):
        return "chat"

    if normalized.endswith("?") or normalized.split(" ", 1)[0] in {
        "ce", "care", "cum", "unde", "cand", "când", "cine", "cat", "cât", "de", "what", "how", "who", "when",
    }:
        return "chat"

    return "task"


def route_engineer_input(text: str, now: Optional[datetime] = None) -> Dict[str, str]:
    mode = classify_engineer_input(text)
    if mode == "local":
        return {"mode": "local", "response": get_local_runtime_answer(text, now=now) or ""}
    return {"mode": mode, "response": ""}
