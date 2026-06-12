"""Compact local conversation context for ANA_MAX chat mode."""

from __future__ import annotations

import unicodedata
from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable


SCHEMA = "ana.os22.conversation_context.v1"


def ascii_text(value: object) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def compact_line(value: object, *, limit: int = 240) -> str:
    text = " ".join(ascii_text(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


@dataclass(frozen=True)
class ConversationTurn:
    user: str
    assistant: str

    def to_prompt_line(self, index: int) -> str:
        return (
            f"{index}. User: {compact_line(self.user)}\n"
            f"   ANA: {compact_line(self.assistant)}"
        )

    def to_dict(self) -> dict[str, str]:
        return {"user": compact_line(self.user), "assistant": compact_line(self.assistant)}


class ConversationMemory:
    """Small in-process memory for natural local chat continuity."""

    def __init__(self, *, max_turns: int = 6) -> None:
        self.max_turns = max(1, int(max_turns or 6))
        self._turns: Deque[ConversationTurn] = deque(maxlen=self.max_turns)

    def add_turn(self, user: object, assistant: object) -> None:
        user_text = compact_line(user)
        assistant_text = compact_line(assistant)
        if not user_text and not assistant_text:
            return
        self._turns.append(ConversationTurn(user=user_text, assistant=assistant_text))

    def extend(self, turns: Iterable[ConversationTurn]) -> None:
        for turn in turns:
            self.add_turn(turn.user, turn.assistant)

    def render(self) -> str:
        if not self._turns:
            return ""
        lines = ["Recent conversation context:"]
        for index, turn in enumerate(self._turns, start=1):
            lines.append(turn.to_prompt_line(index))
        lines.append("Use this context for continuity. Do not repeat it unless useful.")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "max_turns": self.max_turns,
            "turn_count": len(self._turns),
            "turns": [turn.to_dict() for turn in self._turns],
        }
