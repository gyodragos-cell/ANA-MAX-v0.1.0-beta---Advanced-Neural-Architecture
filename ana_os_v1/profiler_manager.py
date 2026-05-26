"""Distributed profiler facade for ANA MAX AI Kernel v1."""

from __future__ import annotations

from typing import Any


class ProfilerManager:
    """Record simulated profile lifecycle events."""

    def __init__(self, event_bus: Any = None) -> None:
        """Initialize profiles."""
        self.event_bus = event_bus
        self.profiles: dict[tuple[str, str], dict[str, Any]] = {}

    def start_profile(self, node_id: str, target: str) -> dict[str, Any]:
        """Start a simulated profile."""
        profile = {"node_id": node_id, "target": target, "running": True, "samples": []}
        self.profiles[(node_id, target)] = profile
        return profile

    def stop_profile(self, node_id: str, target: str) -> dict[str, Any]:
        """Stop a simulated profile."""
        profile = self.profiles[(node_id, target)]
        profile["running"] = False
        return profile

    def collect_profile(self, node_id: str, target: str) -> dict[str, Any]:
        """Collect a simulated profile."""
        profile = self.profiles.get((node_id, target), {"node_id": node_id, "target": target, "running": False, "samples": []})
        profile["samples"].append({"latency_ms": 1.0})
        return profile


__all__ = ["ProfilerManager"]

