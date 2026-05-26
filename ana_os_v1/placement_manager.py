"""Model placement manager for ANA MAX AI Kernel v1."""

from __future__ import annotations

from typing import Any


class PlacementManager:
    """Track where model versions should live."""

    def __init__(self, distributed_memory: Any = None, event_bus: Any = None) -> None:
        """Initialize placement table."""
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.placements: dict[tuple[str, str], list[str] | str] = {}

    def set_placement(self, model: str, version: str, nodes: list[str] | str) -> dict[str, Any]:
        """Set model placement."""
        self.placements[(model, version)] = nodes
        payload = {"model": model, "version": version, "nodes": nodes, "policy": "all" if nodes == "all" else "manual"}
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"placement:{model}:{version}", payload)
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish("model.placement.changed", payload)
        return payload

    def get_placement(self, model: str, version: str) -> dict[str, Any] | None:
        """Return placement for a model version."""
        if (model, version) in self.placements:
            nodes = self.placements[(model, version)]
            return {"model": model, "version": version, "nodes": nodes, "policy": "all" if nodes == "all" else "manual"}
        value = self._memory_get(f"placement:{model}:{version}")
        return dict(value) if isinstance(value, dict) else None

    def list_placements(self) -> list[dict[str, Any]]:
        """Return all placements from local and distributed memory."""
        merged = {
            (model, version): {"model": model, "version": version, "nodes": nodes, "policy": "all" if nodes == "all" else "manual"}
            for (model, version), nodes in self.placements.items()
        }
        for key, value in self._memory_items("placement:"):
            parts = key.split(":", 2)
            if len(parts) == 3 and isinstance(value, dict):
                merged[(parts[1], parts[2])] = dict(value)
        return list(merged.values())

    def get_nodes(self, name: str, version: str | None = None) -> list[str]:
        """Return placement nodes for a model."""
        matches = [(key, value) for key, value in self.placements.items() if key[0] == name and (version is None or key[1] == version)]
        if not matches and version is not None:
            placement = self.get_placement(name, version)
            if not placement:
                return []
            nodes = placement.get("nodes")
            return ["*"] if nodes == "all" else list(nodes or [])
        if not matches:
            placements = [item for item in self.list_placements() if item.get("model") == name]
            if not placements:
                return []
            nodes = sorted(placements, key=lambda item: str(item.get("version", "")))[-1].get("nodes")
            return ["*"] if nodes == "all" else list(nodes or [])
        placement = sorted(matches, key=lambda item: item[0][1])[-1][1]
        return ["*"] if placement == "all" else list(placement)

    def snapshot(self) -> dict[str, Any]:
        """Return placement state."""
        return {f"{item['model']}:{item['version']}": item for item in self.list_placements()}

    def _memory_items(self, prefix: str) -> list[tuple[str, Any]]:
        """Return unwrapped memory items matching a prefix."""
        if not self.distributed_memory or not hasattr(self.distributed_memory, "store"):
            return []
        return [
            (key, self._unwrap(value))
            for key, value in self.distributed_memory.store.items()
            if str(key).startswith(prefix)
        ]

    def _memory_get(self, key: str) -> Any:
        """Read one unwrapped memory value."""
        if not self.distributed_memory or not hasattr(self.distributed_memory, "store"):
            return None
        return self._unwrap(self.distributed_memory.store.get(key))

    @staticmethod
    def _unwrap(value: Any) -> Any:
        """Unwrap MemoryValue-like records."""
        return getattr(value, "value", value)


__all__ = ["PlacementManager"]

