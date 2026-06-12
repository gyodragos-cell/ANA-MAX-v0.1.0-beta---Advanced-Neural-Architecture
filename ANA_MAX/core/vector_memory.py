from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


__all__ = [
    "SimpleEmbeddingModel",
    "VectorMemory",
    "VectorMemoryCortex",
    "get_vector_memory",
]


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return (_module_root() / "memory" / "ana_vector_memory.db").resolve()

    path = Path(db_path)
    if not path.is_absolute():
        path = (_workspace_root() / path).resolve()
    return path


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


def _normalize_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    return dict(metadata)


class SimpleEmbeddingModel:
    """Deterministic hashed bag-of-words embedding model."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def _tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        current: list[str] = []
        lowered = text.lower()

        for char in lowered:
            if char.isalnum():
                current.append(char)
                continue
            if current:
                token = "".join(current)
                if len(token) > 1:
                    tokens.append(token)
                current = []

        if current:
            token = "".join(current)
            if len(token) > 1:
                tokens.append(token)

        return tokens

    def encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        token_counts: dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        total = float(len(tokens))
        for token, count in token_counts.items():
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
            index = int(digest, 16) % self.dim
            weight = count / total
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector

    def similarity(self, left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise ValueError("Embedding dimensions do not match")
        return sum(l * r for l, r in zip(left, right))


class VectorMemoryCortex:
    """SQLite-backed semantic memory store for local ANA MAX workflows."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        index_dim: int = 128,
        max_elements: int = 100000,
    ):
        self.db_path = str(_resolve_db_path(db_path))
        self.index_dim = int(index_dim)
        self.max_elements = int(max_elements)
        self.embedding_model = SimpleEmbeddingModel(dim=self.index_dim)
        self._lock = threading.RLock()
        self._closed = False
        self._cache_key = self.db_path

        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()
        self._schema_variant = self._detect_schema_variant()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            if self._closed:
                return

            try:
                self._conn.close()
            finally:
                self._closed = True
                with _VECTOR_MEMORY_CACHE_LOCK:
                    cached = _VECTOR_MEMORY_CACHE.get(self._cache_key)
                    if cached is self:
                        _VECTOR_MEMORY_CACHE.pop(self._cache_key, None)

    def __enter__(self) -> "VectorMemoryCortex":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Schema and helpers
    # ------------------------------------------------------------------
    def _initialize_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    importance REAL NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)"
            )

    def _table_columns(self) -> set[str]:
        cursor = self._conn.execute("PRAGMA table_info(memories)")
        rows = cursor.fetchall()
        return {str(row[1]) for row in rows}

    def _detect_schema_variant(self) -> str:
        columns = self._table_columns()
        if {"memory_id", "tags_json", "embedding_json", "metadata_json"}.issubset(columns):
            return "v1"
        if {"id", "tags", "metadata"}.issubset(columns):
            return "legacy"
        if "memory_id" in columns:
            return "v1"
        if "id" in columns:
            return "legacy"
        return "v1"

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Vector memory store is closed")

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def _memory_id(
        self,
        content: str,
        memory_type: str,
        tags: Sequence[str],
        metadata: dict[str, Any],
    ) -> str:
        payload = {
            "content": content,
            "memory_type": memory_type,
            "tags": list(tags),
            "metadata": metadata,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return f"mem-{digest[:16]}-{uuid.uuid4().hex[:8]}"

    def _row_to_dict(self, row: sqlite3.Row, query_embedding: Optional[list[float]] = None, query_tokens: Optional[set[str]] = None) -> dict[str, Any]:
        row_keys = set(row.keys())
        tags_json = row["tags_json"] if "tags_json" in row_keys else row["tags"]
        metadata_json = row["metadata_json"] if "metadata_json" in row_keys else row["metadata"]
        embedding_json = row["embedding_json"] if "embedding_json" in row_keys else "[]"
        tags = json.loads(tags_json)
        metadata = json.loads(metadata_json)
        embedding = json.loads(embedding_json) if embedding_json else []
        if not embedding or len(embedding) != self.index_dim:
            embedding = self.embedding_model.encode(row["content"])
        score = float(row["importance"])

        if query_embedding is not None:
            cosine = self.embedding_model.similarity(query_embedding, embedding)
            overlap = 0.0
            if query_tokens:
                content_tokens = set(self.embedding_model._tokenize(row["content"]))
                if query_tokens:
                    overlap = len(query_tokens.intersection(content_tokens)) / max(1, len(query_tokens))
            score = (0.85 * cosine) + (0.15 * overlap) + (0.02 * float(row["importance"]))

        return {
            "memory_id": row["memory_id"],
            "content": row["content"],
            "memory_type": row["memory_type"],
            "tags": tags,
            "importance": float(row["importance"]),
            "score": round(score, 6),
            "metadata": metadata,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _iter_rows(self) -> list[sqlite3.Row]:
        if self._schema_variant == "legacy":
            cursor = self._conn.execute(
                """
                SELECT
                    id AS memory_id,
                    content,
                    memory_type,
                    tags AS tags_json,
                    importance,
                    '[]' AS embedding_json,
                    metadata AS metadata_json,
                    CAST(timestamp AS TEXT) AS created_at,
                    CAST(COALESCE(last_access, timestamp) AS TEXT) AS updated_at
                FROM memories
                ORDER BY COALESCE(last_access, timestamp) DESC, id ASC
                """
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT memory_id, content, memory_type, tags_json, importance,
                       embedding_json, metadata_json, created_at, updated_at
                FROM memories
                ORDER BY updated_at DESC, memory_id ASC
                """
            )
        return list(cursor.fetchall())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def store(
        self,
        content: str,
        memory_type: str = "episodic",
        tags: Optional[Sequence[str] | str] = None,
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        self._ensure_open()
        normalized_tags = _normalize_tags(tags)
        normalized_metadata = _normalize_metadata(metadata)
        timestamp = self._now()
        memory_id = self._memory_id(content, memory_type, normalized_tags, normalized_metadata)
        embedding = self.embedding_model.encode(content)

        with self._lock, self._conn:
            if self._schema_variant == "legacy":
                legacy_timestamp = time.time()
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO memories (
                        id, content, memory_type, timestamp, importance,
                        access_count, last_access, tags, metadata
                    ) VALUES (
                        ?, ?, ?, ?, ?, COALESCE((SELECT access_count FROM memories WHERE id = ?), 0),
                        ?, ?, ?
                    )
                    """,
                    (
                        memory_id,
                        content,
                        memory_type,
                        legacy_timestamp,
                        float(importance),
                        memory_id,
                        legacy_timestamp,
                        json.dumps(normalized_tags, sort_keys=True, separators=(",", ":")),
                        json.dumps(normalized_metadata, sort_keys=True, separators=(",", ":")),
                    ),
                )
            else:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO memories (
                        memory_id, content, memory_type, tags_json, importance,
                        embedding_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM memories WHERE memory_id = ?), ?), ?)
                    """,
                    (
                        memory_id,
                        content,
                        memory_type,
                        json.dumps(normalized_tags, sort_keys=True, separators=(",", ":")),
                        float(importance),
                        json.dumps(embedding, separators=(",", ":")),
                        json.dumps(normalized_metadata, sort_keys=True, separators=(",", ":")),
                        memory_id,
                        timestamp,
                        timestamp,
                    ),
                )

        return memory_id

    def search(
        self,
        query: str,
        top_k: int = 10,
        memory_type: Optional[str] = None,
        tags: Optional[Sequence[str] | str] = None,
        min_importance: float = 0.0,
    ) -> list[dict[str, Any]]:
        self._ensure_open()
        query = query or ""
        normalized_tags = _normalize_tags(tags)
        query_embedding = self.embedding_model.encode(query)
        query_tokens = set(self.embedding_model._tokenize(query))

        with self._lock:
            rows = self._iter_rows()

        results: list[dict[str, Any]] = []
        for row in rows:
            row_tags = set(json.loads(row["tags_json"]))
            if memory_type and row["memory_type"] != memory_type:
                continue
            if float(row["importance"]) < float(min_importance):
                continue
            if normalized_tags and not set(normalized_tags).issubset(row_tags):
                continue

            result = self._row_to_dict(row, query_embedding=query_embedding, query_tokens=query_tokens)
            result["score"] = round(
                max(0.0, result["score"] + (0.05 * len(query_tokens.intersection(set(self.embedding_model._tokenize(result["content"]))))) ),
                6,
            )
            results.append(result)

        results.sort(
            key=lambda item: (
                -float(item["score"]),
                -float(item["importance"]),
                item["updated_at"],
                item["memory_id"],
            )
        )
        return results[: max(0, int(top_k))]

    def get_stats(self) -> dict[str, Any]:
        self._ensure_open()
        with self._lock:
            if self._schema_variant == "legacy":
                cursor = self._conn.execute(
                    "SELECT memory_type, tags AS tags_json, importance FROM memories"
                )
            else:
                cursor = self._conn.execute(
                    "SELECT memory_type, tags_json, importance FROM memories"
                )
            rows = cursor.fetchall()

        total = len(rows)
        by_type: dict[str, int] = {}
        tags: dict[str, int] = {}
        importance_total = 0.0

        for row in rows:
            memory_type = row["memory_type"]
            by_type[memory_type] = by_type.get(memory_type, 0) + 1
            importance_total += float(row["importance"])
            for tag in json.loads(row["tags_json"]):
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "schema": "ana.core.vector_memory.v1",
            "db_path": self.db_path,
            "ready": True,
            "dimension": self.index_dim,
            "backend": "sqlite-hashed-bow",
            "total": total,
            "by_type": by_type,
            "tags": tags,
            "average_importance": round(importance_total / total, 6) if total else 0.0,
        }

    def consolidate(self, min_importance: float = 0.1) -> int:
        self._ensure_open()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE importance < ?",
                (float(min_importance),),
            )
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
        return int(deleted)


VectorMemory = VectorMemoryCortex


_VECTOR_MEMORY_CACHE: dict[str, VectorMemoryCortex] = {}
_VECTOR_MEMORY_CACHE_LOCK = threading.Lock()


def get_vector_memory(db_path: str | Path | None = None) -> VectorMemoryCortex:
    resolved = str(_resolve_db_path(db_path))
    with _VECTOR_MEMORY_CACHE_LOCK:
        instance = _VECTOR_MEMORY_CACHE.get(resolved)
        if instance is None or getattr(instance, "_closed", True):
            instance = VectorMemoryCortex(db_path=resolved)
            _VECTOR_MEMORY_CACHE[resolved] = instance
        return instance
