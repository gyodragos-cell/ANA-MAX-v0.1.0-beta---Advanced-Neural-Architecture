"""Distributed model registry for ANA MAX AI Kernel v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelRecord:
    """One registered model version."""

    name: str
    version: str
    path: str
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe record."""
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
            "node_id": self.node_id,
        }


class ModelRegistry:
    """Register model metadata and replicate it through distributed memory."""

    def __init__(self, distributed_memory: Any = None, event_bus: Any = None) -> None:
        """Initialize model registry."""
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.models: dict[tuple[str, str], ModelRecord] = {}
        self.canary_weights: dict[str, dict[str, int]] = {}

    def register_model(self, name: str, version: str, metadata: dict[str, Any] | str | None = None, capabilities=None, tags=None) -> ModelRecord:
        """Register a model version."""
        if isinstance(metadata, dict):
            data = dict(metadata)
            path = data.get("path")
            capabilities = data.get("capabilities", capabilities or [])
            tags = data.get("tags", tags or [])
            node_id = data.get("node_id")
        else:
            path = metadata
            node_id = None
        record = ModelRecord(name, version, str(path or ""), list(capabilities or []), list(tags or []), node_id)
        self.models[(name, version)] = record
        self._replicate(record)
        self._publish("model.registered", {"name": name, "version": version, "metadata": record.to_dict()})
        return record

    def unregister_model(self, name: str, version: str) -> bool:
        """Unregister a model version."""
        existed = self.models.pop((name, version), None) is not None
        if self.distributed_memory and hasattr(self.distributed_memory, "store"):
            self.distributed_memory.store.pop(f"model:{name}:{version}", None)
        if existed:
            self._publish("model.unregistered", {"name": name, "version": version})
        return existed

    def list_models(self) -> list[dict[str, Any]]:
        """Return all models."""
        merged = {(record.name, record.version): record.to_dict() for record in self.models.values()}
        for key, value in self._memory_items("model:"):
            parts = key.split(":", 2)
            if len(parts) == 3 and isinstance(value, dict):
                merged[(parts[1], parts[2])] = dict(value)
        return list(merged.values())

    def get_model(self, name: str, version: str | None = None) -> dict[str, Any] | None:
        """Return a model by name and optional version."""
        if version is not None:
            record = self.models.get((name, version))
            if record:
                return record.to_dict()
            value = self._memory_get(f"model:{name}:{version}")
            return dict(value) if isinstance(value, dict) else None
        matches = [model for model in self.list_models() if model.get("name") == name]
        if not matches:
            return None
        return sorted(matches, key=lambda item: str(item.get("version", "")))[-1]

    def set_canary_weights(self, name: str, weights: dict[str, int]) -> None:
        """Store canary weights per version."""
        self.canary_weights[name] = dict(weights)

    def choose_version(self, name: str, bucket: int = 0) -> str | None:
        """Choose a version using deterministic canary weights."""
        weights = self.canary_weights.get(name)
        if not weights:
            model = self.get_model(name)
            return model["version"] if model else None
        total = sum(weights.values())
        point = bucket % max(1, total)
        running = 0
        for version, weight in sorted(weights.items()):
            running += weight
            if point < running:
                return version
        return None

    def _replicate(self, record: ModelRecord) -> None:
        """Replicate model metadata into distributed memory."""
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"model:{record.name}:{record.version}", record.to_dict())

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish model registry events."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)

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


__all__ = ["ModelRecord", "ModelRegistry"]

