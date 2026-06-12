from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from ANA_MAX.core.vector_memory import get_vector_memory


__all__ = ["RAGBridge", "get_rag_bridge"]


def _normalize_tags(tags: Optional[Sequence[str] | str]) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        text = tags.strip()
        if not text:
            return []
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            return [text]
        if isinstance(loaded, list):
            return [str(item) for item in loaded if str(item).strip()]
        if isinstance(loaded, str):
            return [loaded]
        return [str(loaded)]
    return [str(item).strip() for item in tags if str(item).strip()]


class RAGBridge:
    """Metadata-only RAG bridge for ANA MAX local workflows."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path) if db_path is not None else None
        self._memory = get_vector_memory(db_path=db_path)

    def ingest_text(
        self,
        text: str,
        memory_type: str = "semantic",
        tags: Optional[Sequence[str] | str] = None,
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        normalized_metadata = dict(metadata or {})
        normalized_metadata.setdefault("source", "rag_bridge")
        normalized_metadata.setdefault("kind", "ingest_text")
        return self._memory.store(
            content=text,
            memory_type=memory_type,
            tags=_normalize_tags(tags),
            importance=importance,
            metadata=normalized_metadata,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        tags: Optional[Sequence[str] | str] = None,
        min_importance: float = 0.0,
    ) -> dict[str, Any]:
        results = self._memory.search(
            query=query,
            top_k=top_k,
            memory_type=memory_type,
            tags=_normalize_tags(tags),
            min_importance=min_importance,
        )
        return {
            "schema": "ana.local.rag_bridge.v1",
            "query": query,
            "count": len(results),
            "results": results,
            "metadata_only": True,
            "local_only": True,
            "ready": True,
        }

    def build_context(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        tags: Optional[Sequence[str] | str] = None,
        min_importance: float = 0.0,
    ) -> str:
        retrieval = self.retrieve(
            query=query,
            top_k=top_k,
            memory_type=memory_type,
            tags=tags,
            min_importance=min_importance,
        )
        lines: list[str] = []
        for index, item in enumerate(retrieval["results"], start=1):
            lines.append(f"[{index}] {item['content']}")
        return "\n".join(lines)

    def get_status(self) -> dict[str, Any]:
        return {
            "schema": "ana.local.rag_bridge.v1",
            "ready": True,
            "local_only": True,
            "memory_store": self._memory.get_stats(),
            "db_path": self._memory.db_path,
            "capabilities": [
                "ingest_text",
                "retrieve",
                "build_context",
                "get_status",
            ],
        }


_RAG_BRIDGE_CACHE: dict[str | None, RAGBridge] = {}


def get_rag_bridge(db_path: str | Path | None = None) -> RAGBridge:
    key = str(db_path) if db_path is not None else None
    bridge = _RAG_BRIDGE_CACHE.get(key)
    if bridge is None:
        bridge = RAGBridge(db_path=db_path)
        _RAG_BRIDGE_CACHE[key] = bridge
    return bridge


if __name__ == "__main__":
    bridge = RAGBridge()
    print(json.dumps(bridge.get_status(), indent=2, ensure_ascii=True))

