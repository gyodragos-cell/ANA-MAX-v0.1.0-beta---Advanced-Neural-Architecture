"""Local fake model loader for ANA MAX AI Kernel v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelHandle:
    """Loaded fake model handle."""

    name: str
    version: str
    warmed: bool = False


class ModelLoader:
    """Idempotent local model loader with in-memory cache."""

    def __init__(self, node_id: str = "local") -> None:
        """Initialize model cache."""
        self.node_id = node_id
        self.cache: dict[tuple[str, str], ModelHandle] = {}

    def load_model(self, name: str, version: str) -> ModelHandle:
        """Load or reuse a fake model handle."""
        key = (name, version)
        self.cache.setdefault(key, ModelHandle(name, version))
        return self.cache[key]

    def unload_model(self, handle: ModelHandle) -> bool:
        """Unload a fake model handle."""
        return self.cache.pop((handle.name, handle.version), None) is not None

    def warmup_model(self, name: str, version: str) -> ModelHandle:
        """Warm up a model and cache the warmed handle."""
        handle = ModelHandle(name, version, warmed=True)
        self.cache[(name, version)] = handle
        return handle


__all__ = ["ModelHandle", "ModelLoader"]

