"""Prompt-level RAG policy for ANA_MAX chat mode."""

from __future__ import annotations

import unicodedata


SCHEMA = "ana.os22.rag_prompt_policy.v1"


def _ascii_lower(value: object) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii").lower()


def should_use_rag_for_prompt(prompt: str) -> bool:
    text = _ascii_lower(prompt)
    casual_markers = (
        "salut",
        "buna",
        "hello",
        "lucram ca o echipa",
        "raspunde natural",
        "scurt si clar",
    )
    if any(marker in text for marker in casual_markers) and not any(
        marker in text for marker in ("proiect", "cod", "fisier", "eroare", "test", "rag", "memorie")
    ):
        return False

    useful_markers = (
        "ana",
        "os-22",
        "os22",
        "proiect",
        "cod",
        "fisier",
        "eroare",
        "log",
        "test",
        "rag",
        "memorie",
        "ce am facut",
        "continuam",
        "tool",
        "toolbridge",
    )
    return any(marker in text for marker in useful_markers)


def summarize_rag_prompt_policy(prompt: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "prompt": str(prompt or ""),
        "use_rag": should_use_rag_for_prompt(prompt),
    }
