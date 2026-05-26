"""Distributed debugger hooks for ANA MAX AI Kernel v1."""

from __future__ import annotations

from typing import Any


class DebugManager:
    """Set breakpoints and inspect simulated node state."""

    def __init__(self, event_bus: Any = None, providers: dict[str, Any] | None = None) -> None:
        """Initialize debugger state."""
        self.event_bus = event_bus
        self.providers = dict(providers or {})
        self.breakpoints: set[tuple[str, str]] = set()

    def set_breakpoint(self, node_id: str, target: str) -> bool:
        """Set a fake distributed breakpoint."""
        self.breakpoints.add((node_id, target))
        self._publish("debug.breakpoint.set", {"node_id": node_id, "target": target})
        return True

    def clear_breakpoint(self, node_id: str, target: str) -> bool:
        """Clear a fake distributed breakpoint."""
        self.breakpoints.discard((node_id, target))
        return True

    def inspect_state(self, node_id: str, target: str) -> dict[str, Any]:
        """Inspect a configured provider snapshot."""
        provider = self.providers.get(target)
        snapshot = provider.snapshot() if hasattr(provider, "snapshot") else {}
        payload = {"node_id": node_id, "target": target, "snapshot": snapshot}
        self._publish("debug.inspect.response", payload)
        return payload

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a debug event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)


__all__ = ["DebugManager"]

