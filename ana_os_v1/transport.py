"""Transport abstraction for ANA MAX OS dev protocols."""

from __future__ import annotations

from typing import Any, Protocol


class Transport(Protocol):
    """Minimal send-only transport used by cluster membership."""

    def send(self, envelope: dict[str, Any]) -> None:
        """Send one protocol envelope."""


__all__ = ["Transport"]

