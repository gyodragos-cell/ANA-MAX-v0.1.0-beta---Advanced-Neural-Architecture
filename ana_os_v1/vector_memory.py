"""Small vector memory for ANA MAX AI Kernel v1."""

from __future__ import annotations

import math
from typing import Any


class VectorMemory:
    """Store vectors and query by cosine similarity."""

    def __init__(self, distributed_memory: Any = None, node_id: str = "local") -> None:
        """Initialize vector store."""
        self.distributed_memory = distributed_memory
        self.node_id = node_id
        self.vectors: dict[str, dict[str, Any]] = {}

    def store_embedding(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        """Store one embedding."""
        entry = {"key": key, "vector": list(vector), "metadata": dict(metadata or {}), "node_id": self.node_id}
        self.vectors[key] = entry
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"vector:{key}", entry)

    def query_embedding(self, vector: list[float], top_k: int = 1) -> list[dict[str, Any]]:
        """Query by cosine similarity."""
        scored = []
        for entry in self.vectors.values():
            scored.append({**entry, "score": self._cosine(vector, entry["vector"])})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        """Return cosine similarity."""
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return 0.0 if not left_norm or not right_norm else dot / (left_norm * right_norm)


__all__ = ["VectorMemory"]

