"""Distributed metrics manager for ANA MAX OS dev mode."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class MetricsManager:
    """Small counter store for distributed kernel metrics."""

    def __init__(self, event_bus: Any = None) -> None:
        """Initialize counters."""
        self.event_bus = event_bus
        self.counters: dict[str, int] = defaultdict(int)

    def increment(self, name: str, amount: int = 1) -> int:
        """Increment a counter and publish metrics.update."""
        self.counters[name] += amount
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish("metrics.update", {"name": name, "value": self.counters[name]})
        return self.counters[name]

    def snapshot(self) -> dict[str, int]:
        """Return metric counters."""
        return dict(self.counters)


__all__ = ["MetricsManager"]

