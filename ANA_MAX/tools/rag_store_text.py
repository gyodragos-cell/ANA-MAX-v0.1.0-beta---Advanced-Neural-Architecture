"""OS-22 RAG text store helper."""

from __future__ import annotations

from typing import Any

from ANA_MAX.local.rag_bridge import get_rag_bridge


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 100) -> list[str]:
    """Split text into deterministic overlapping chunks."""
    payload = " ".join(str(text or "").split())
    size = max(1, int(chunk_size or 1200))
    overlap = max(0, min(int(chunk_overlap or 0), size - 1))
    if not payload:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(payload):
        end = min(len(payload), start + size)
        chunk = payload[start:end].strip()
        if chunk:
            chunks.append(_ascii_text(chunk))
        if end >= len(payload):
            break
        start = max(start + 1, end - overlap)
    if overlap and chunks:
        tail_start = max(0, len(payload) - overlap)
        tail = payload[tail_start:].strip()
        if tail and tail != chunks[-1]:
            chunks.append(_ascii_text(tail))
    return chunks


def rag_store_text(
    text: str,
    source: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 100,
    bridge: Any | None = None,
) -> dict[str, Any]:
    """Store text chunks into RAGBridge with source metadata."""
    payload = str(text or "").strip()
    source_text = _ascii_text(source).strip()
    if not payload:
        return {
            "schema": "ana.os22.rag_store_text.v1",
            "success": False,
            "local_only": True,
            "source": source_text,
            "stored_count": 0,
            "memory_ids": [],
            "error": "empty_text",
        }
    if not source_text:
        return {
            "schema": "ana.os22.rag_store_text.v1",
            "success": False,
            "local_only": True,
            "source": source_text,
            "stored_count": 0,
            "memory_ids": [],
            "error": "missing_source",
        }

    rag_bridge = bridge or get_rag_bridge()
    chunks = chunk_text(payload, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    memory_ids: list[str] = []
    for index, chunk in enumerate(chunks):
        memory_id = rag_bridge.ingest_text(
            chunk,
            memory_type="semantic",
            tags=["os22", "web_learning", source_text],
            importance=0.6,
            metadata={
                "schema": "ana.os22.rag_store_text.chunk.v1",
                "source": source_text,
                "chunk_index": index,
                "chunk_count": len(chunks),
            },
        )
        memory_ids.append(_ascii_text(memory_id))

    return {
        "schema": "ana.os22.rag_store_text.v1",
        "success": True,
        "local_only": True,
        "source": source_text,
        "chunk_size": int(chunk_size or 1200),
        "chunk_overlap": int(chunk_overlap or 100),
        "stored_count": len(memory_ids),
        "memory_ids": memory_ids,
        "error": "",
    }
