"""Natural chat quality coach for ANA_MAX ana_chat mode."""

from __future__ import annotations

import unicodedata
from typing import Any


SCHEMA = "ana.os22.chat_response_coach.v1"


def _ascii_lower(value: object) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii").lower()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _is_rag_question(prompt_text: str) -> bool:
    stripped = prompt_text.strip(" ?!.")
    return stripped in {"ce este rag", "ce e rag", "what is rag"}


def _is_collaboration_prompt(prompt_text: str) -> bool:
    return _has_any(prompt_text, ("lucram ca o echipa", "raspunde natural", "scurt si clar", "vorbim ca o echipa"))


def _is_greeting_prompt(prompt_text: str) -> bool:
    stripped = prompt_text.strip(" ?!.")
    return stripped in {"buna", "buna ziua", "salut", "hello", "hi", "hey"}


def _is_polite_status_prompt(prompt_text: str) -> bool:
    return _has_any(prompt_text, ("how are you", "ce faci", "cum esti", "cum merge"))


def _quality_issues(prompt_text: str, response_text: str) -> list[str]:
    issues: list[str] = []
    if "?" in response_text:
        issues.append("question_mark_artifacts")
    if _has_any(
        response_text,
        (
            "ragoada",
            "supporta",
            "scumat",
            "por ejemplo",
            "echip.",
            "ziua bune",
            "mulumesc",
            "asta o va rog",
            "note: no tool",
            "tool_dispatcher",
            "unknown tool",
        ),
    ):
        issues.append("translation_drift")
    if _has_any(response_text, ("ora", "thursday", "monday", "tuesday", "wednesday", "friday", "saturday", "sunday", "2026")) and not _has_any(
        prompt_text,
        ("ora", "timp", "zi", "data", "today"),
    ):
        issues.append("irrelevant_time")
    if len(response_text.split()) > 90 and _is_collaboration_prompt(prompt_text):
        issues.append("too_long_for_collaboration")
    return issues


def coach_chat_response(prompt: str, response: str) -> dict[str, Any]:
    prompt_text = _ascii_lower(prompt)
    response_text = str(response or "").strip()
    issues = _quality_issues(prompt_text, _ascii_lower(response_text))

    replacement = ""
    if issues and _is_rag_question(prompt_text):
        replacement = (
            "RAG este memoria de lucru a agentului: cauta informatii locale relevante, "
            "le pune in context, apoi raspunsul devine mai precis."
        )
    elif issues and _is_greeting_prompt(prompt_text):
        replacement = "Buna, colegu. Sunt aici si sunt gata sa lucram."
    elif issues and _is_polite_status_prompt(prompt_text):
        replacement = "Sunt bine, colegu. Sunt aici, atent si gata sa lucram."
    elif issues and _is_collaboration_prompt(prompt_text):
        replacement = (
            "Salut, colegu. Asa lucram: tu imi spui ce vrei, eu raspund natural si aleg singur "
            "RAG sau ToolBridge cand chiar ajuta."
        )

    return {
        "schema": SCHEMA,
        "changed": bool(replacement),
        "issues": issues,
        "text": replacement or response_text,
    }
