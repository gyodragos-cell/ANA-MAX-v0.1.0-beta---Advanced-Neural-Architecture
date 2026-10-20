from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .redaction import redact_value, sanitize_url
from .store import Store

SOURCE_TYPES = {"event", "incident", "capsule", "experience", "capability", "document"}
MAX_DOCUMENT_CHARS = 16_000
MAX_QUERY_CHARS = 500
MAX_QUERY_TERMS = 12
MAX_LOCAL_FILE_BYTES = 524_288
MAX_LOCAL_FILES = 200
MAX_LOCAL_SOURCE_BYTES = 8 * 1024 * 1024
LOCAL_TEXT_EXTENSIONS = {".md", ".txt", ".rst"}
EVENT_ATTRIBUTE_ALLOWLIST = {
    "status_code", "response_code", "exception_type", "error_type", "error_code",
    "method", "http_method", "tool_name", "operation", "agent_name", "verification",
    "exit_code", "host", "port", "scheme", "span_id", "capability_name",
    "capability_kind",
}


def _text(value: Any, max_chars: int = 4000) -> str:
    safe, _ = redact_value(value)
    if isinstance(safe, str):
        text = safe
    else:
        text = json.dumps(safe, ensure_ascii=True, sort_keys=True, default=str)
    return text[:max_chars]


def _document(
    *, doc_id: str, source_type: str, source_ref: str, title: str, body: str,
    trust_status: str, observed_at: str, metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_title = _text(title, 500)
    safe_body = _text(body, MAX_DOCUMENT_CHARS)
    safe_metadata, _ = redact_value(metadata or {})
    if not isinstance(safe_metadata, dict):
        safe_metadata = {}
    core = {
        "doc_id": doc_id,
        "source_type": source_type,
        "source_ref": _text(source_ref, 2000),
        "title": safe_title,
        "body": safe_body,
        "trust_status": _text(trust_status, 100),
        "observed_at": _text(observed_at or "", 100),
        "metadata": safe_metadata,
    }
    canonical = json.dumps(core, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    core["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return core


def _event_document(event: dict[str, Any]) -> dict[str, Any]:
    attributes = event.get("attributes") if isinstance(event.get("attributes"), dict) else {}
    safe_attributes: dict[str, Any] = {}
    for key in sorted(EVENT_ATTRIBUTE_ALLOWLIST):
        if key not in attributes:
            continue
        value = attributes[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean = _text(value, 160)
            if clean not in ("", "null", "None"):
                safe_attributes[key] = clean
    target = event.get("target")
    safe_target = ""
    if isinstance(target, str) and target:
        safe_target, _ = sanitize_url(target)
    facts = {
        "timestamp": event.get("timestamp"),
        "trace_id": event.get("trace_id"),
        "mission_id": event.get("mission_id"),
        "source": event.get("source"),
        "component": event.get("component"),
        "kind": event.get("kind"),
        "action": event.get("action"),
        "outcome": event.get("outcome"),
        "parent_event_id": event.get("parent_event_id"),
        "duration_ms": event.get("duration_ms"),
        "target": safe_target,
        "attributes": safe_attributes,
    }
    label = " ".join(str(event.get(k, "")) for k in ("component", "kind", "action", "outcome"))
    return _document(
        doc_id=f"event:{event['event_id']}",
        source_type="event",
        source_ref=str(event["event_id"]),
        title=label.strip() or "Trace event",
        body=json.dumps(facts, ensure_ascii=True, sort_keys=True),
        trust_status="observed_evidence",
        observed_at=str(event.get("timestamp", "")),
        metadata={
            "event_id": event["event_id"],
            "trace_id": event.get("trace_id"),
            "mission_id": event.get("mission_id"),
            "outcome": event.get("outcome"),
            "kind": event.get("kind"),
            "component": event.get("component"),
        },
    )


def _local_document_sources(store: Store) -> list[dict[str, Any]]:
    """Read only operator-listed UTF-8 text sources under strict size/extension limits."""
    db_parent = store.db_path.parent
    roots = [db_parent, db_parent.parent]
    config_path = next(
        (root / "config" / "memory_sources.json" for root in roots
         if (root / "config" / "memory_sources.json").is_file()),
        None,
    )
    if config_path is None:
        return []
    root = config_path.parent.parent
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(config, dict):
        return []
    raw_limits = config.get("limits", {})
    if not isinstance(raw_limits, dict):
        raw_limits = {}
    try:
        file_byte_limit = max(1, min(int(raw_limits.get("max_file_bytes", MAX_LOCAL_FILE_BYTES)), MAX_LOCAL_FILE_BYTES))
        total_byte_limit = max(1, min(int(raw_limits.get("max_total_source_bytes", MAX_LOCAL_SOURCE_BYTES)), MAX_LOCAL_SOURCE_BYTES))
        file_count_limit = max(1, min(int(raw_limits.get("max_files", MAX_LOCAL_FILES)), MAX_LOCAL_FILES))
    except (TypeError, ValueError):
        return []

    paths: list[Path] = []
    seen_paths: set[str] = set()

    def add_path(candidate: Any) -> None:
        if not isinstance(candidate, str) or not candidate.strip():
            return
        candidate_path = Path(candidate.strip())
        if not candidate_path.is_absolute():
            candidate_path = root / candidate_path
        try:
            if candidate_path.is_symlink() or not candidate_path.is_file():
                return
            resolved = candidate_path.resolve()
            key = str(resolved).casefold()
            if resolved.suffix.lower() not in LOCAL_TEXT_EXTENSIONS or key in seen_paths:
                return
            seen_paths.add(key)
            paths.append(resolved)
        except OSError:
            return

    raw_files = config.get("files", [])
    if isinstance(raw_files, list):
        for item in raw_files:
            add_path(item)

    raw_directories = config.get("directories", [])
    if isinstance(raw_directories, list):
        for entry in raw_directories:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            ext_values = entry.get("extensions", [".md"])
            if not isinstance(ext_values, list):
                continue
            extensions = {str(x).lower() for x in ext_values} & LOCAL_TEXT_EXTENSIONS
            directory = Path(entry["path"])
            if not directory.is_absolute():
                directory = root / directory
            try:
                if directory.is_symlink() or not directory.is_dir():
                    continue
                for candidate in directory.rglob("*"):
                    if len(paths) >= file_count_limit:
                        break
                    if candidate.is_symlink() or not candidate.is_file():
                        continue
                    if candidate.suffix.lower() not in extensions:
                        continue
                    add_path(str(candidate))
            except OSError:
                continue

    output: list[dict[str, Any]] = []
    total_bytes = 0
    for path in paths[:file_count_limit]:
        try:
            size = path.stat().st_size
            if size < 1 or size > file_byte_limit:
                continue
            if total_bytes + size > total_byte_limit:
                break
            raw = path.read_bytes()
            total_bytes += len(raw)
            text = _text(raw.decode("utf-8-sig", errors="replace"), file_byte_limit)
            paragraphs = re.split(r"\n[ \t]*\n", text)
            chunks: list[str] = []
            current = ""
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                while len(paragraph) > 8000:
                    piece, paragraph = paragraph[:8000], paragraph[8000:]
                    if current:
                        chunks.append(current)
                        current = ""
                    chunks.append(piece)
                if not paragraph:
                    continue
                candidate = (current + "\n\n" + paragraph).strip() if current else paragraph
                if len(candidate) > 8000 and current:
                    chunks.append(current)
                    current = paragraph
                else:
                    current = candidate
            if current:
                chunks.append(current)
            path_hash = hashlib.sha256(str(path).casefold().encode("utf-8")).hexdigest()[:20]
            modified = str(path.stat().st_mtime)
            for index, chunk in enumerate(chunks, start=1):
                headings = re.findall(r"(?m)^#{1,6}\s+(.+)$", chunk)
                heading = headings[-1].strip()[:120] if headings else f"chunk {index}"
                output.append(_document(
                    doc_id=f"document:{path_hash}:{index:04d}",
                    source_type="document",
                    source_ref=str(path),
                    title=f"{path.name} — {heading}",
                    body=chunk,
                    trust_status="local_document",
                    observed_at=modified,
                    metadata={
                        "path": str(path),
                        "chunk_index": index,
                        "file_size_bytes": size,
                        "modified_timestamp": modified,
                    },
                ))
                if len(output) >= file_count_limit * 16:
                    return output
        except (OSError, UnicodeError):
            continue
    return output


def _source_documents(store: Store) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    with store._connect() as conn:
        event_rows = conn.execute(
            "SELECT event_json FROM trace_events ORDER BY timestamp DESC LIMIT 50000"
        ).fetchall()
        incident_rows = conn.execute("SELECT * FROM incidents ORDER BY updated_at DESC LIMIT 10000").fetchall()
        capsule_rows = conn.execute("SELECT * FROM mission_capsules ORDER BY updated_at DESC LIMIT 5000").fetchall()
        experience_rows = conn.execute("SELECT * FROM experiences ORDER BY updated_at DESC LIMIT 20000").fetchall()
        capability_rows = conn.execute(
            "SELECT kind, name, status, owner, observed_at FROM capability_nodes ORDER BY observed_at DESC LIMIT 10000"
        ).fetchall()

    for row in event_rows:
        try:
            event = json.loads(row["event_json"])
            if isinstance(event, dict) and event.get("event_id"):
                docs.append(_event_document(event))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    for row in incident_rows:
        evidence_ids = json.loads(row["evidence_event_ids_json"])
        body = " ".join([
            str(row["summary"]), str(row["cause_hypothesis"]),
            " ".join(str(x) for x in evidence_ids),
        ])
        docs.append(_document(
            doc_id=f"incident:{row['incident_id']}", source_type="incident",
            source_ref=row["incident_id"], title=row["title"], body=body,
            trust_status="unverified_hypothesis" if "UNVERIFIED" in str(row["cause_hypothesis"]).upper() else row["status"],
            observed_at=row["updated_at"],
            metadata={"incident_id": row["incident_id"], "trace_id": row["trace_id"], "status": row["status"]},
        ))

    for row in capsule_rows:
        try:
            capsule = json.loads(row["capsule_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        # Index the mission-relevant summary only; avoid bulk payloads and arbitrary nested dumps.
        parts: list[str] = []
        for field in ("project", "objective", "status", "known_good", "known_bad", "open_issues", "next_steps"):
            if field in capsule:
                parts.append(f"{field}: {_text(capsule[field], 2500)}")
        current = capsule.get("current_state")
        if isinstance(current, dict):
            useful = {key: current[key] for key in (
                "checkpoint", "stage", "status", "latest_test_result", "root", "mission_id"
            ) if key in current}
            if useful:
                parts.append("current_state: " + _text(useful, 1000))
        docs.append(_document(
            doc_id=f"capsule:{row['mission_id']}", source_type="capsule",
            source_ref=row["mission_id"], title=f"{row['project']} mission capsule",
            body="\n".join(parts), trust_status=str(row["status"]),
            observed_at=row["updated_at"],
            metadata={"mission_id": row["mission_id"], "project": row["project"], "status": row["status"]},
        ))

    for row in experience_rows:
        source_ids = json.loads(row["source_event_ids_json"])
        body = (
            f"problem: {row['problem_key']}\n"
            f"cause: {row['cause']}\n"
            f"solution: {row['solution']}\n"
            f"outcome: {row['outcome']}\n"
            f"source event ids: {' '.join(str(x) for x in source_ids)}"
        )
        docs.append(_document(
            doc_id=f"experience:{row['lesson_id']}", source_type="experience",
            source_ref=row["lesson_id"], title=row["problem_key"], body=body,
            trust_status=row["status"], observed_at=row["updated_at"],
            metadata={
                "lesson_id": row["lesson_id"], "status": row["status"],
                "outcome": row["outcome"], "confidence": row["confidence"],
                "verified_by": row["verified_by"], "source_event_ids": source_ids,
            },
        ))

    for row in capability_rows:
        title = f"{row['kind']} {row['name']}"
        body = f"kind: {row['kind']}\nname: {row['name']}\nstatus: {row['status']}\nowner: {row['owner'] or ''}"
        docs.append(_document(
            doc_id=f"capability:{row['kind']}:{row['name']}", source_type="capability",
            source_ref=f"{row['kind']}:{row['name']}", title=title, body=body,
            trust_status=row["status"], observed_at=row["observed_at"],
            metadata={"kind": row["kind"], "name": row["name"], "status": row["status"], "owner": row["owner"]},
        ))
    docs.extend(_local_document_sources(store))
    return docs


def refresh_memory_index(store: Store) -> dict[str, Any]:
    """Incrementally synchronize safe local source summaries into the SQLite FTS5 index."""
    docs = _source_documents(store)
    inserted = updated = unchanged = 0
    with store._connect() as conn:
        existing_rows = conn.execute("SELECT doc_id, content_hash FROM memory_documents").fetchall()
        existing = {row["doc_id"]: row["content_hash"] for row in existing_rows}
        desired_ids = {doc["doc_id"] for doc in docs}

        for doc in docs:
            previous_hash = existing.get(doc["doc_id"])
            if previous_hash == doc["content_hash"]:
                unchanged += 1
                continue
            if previous_hash is None:
                inserted += 1
            else:
                updated += 1
                conn.execute("DELETE FROM memory_fts WHERE doc_id=?", (doc["doc_id"],))
            conn.execute(
                """INSERT INTO memory_documents
                   (doc_id, source_type, source_ref, title, body, trust_status, observed_at, metadata_json, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(doc_id) DO UPDATE SET source_type=excluded.source_type,
                     source_ref=excluded.source_ref, title=excluded.title, body=excluded.body,
                     trust_status=excluded.trust_status, observed_at=excluded.observed_at,
                     metadata_json=excluded.metadata_json, content_hash=excluded.content_hash""",
                (
                    doc["doc_id"], doc["source_type"], doc["source_ref"], doc["title"], doc["body"],
                    doc["trust_status"], doc["observed_at"],
                    json.dumps(doc["metadata"], ensure_ascii=True, sort_keys=True), doc["content_hash"],
                ),
            )
            conn.execute(
                "INSERT INTO memory_fts(doc_id, source_type, trust_status, title, body) VALUES (?, ?, ?, ?, ?)",
                (doc["doc_id"], doc["source_type"], doc["trust_status"], doc["title"], doc["body"]),
            )

        stale = set(existing) - desired_ids
        for doc_id in stale:
            conn.execute("DELETE FROM memory_fts WHERE doc_id=?", (doc_id,))
            conn.execute("DELETE FROM memory_documents WHERE doc_id=?", (doc_id,))

    counts = Counter(doc["source_type"] for doc in docs)
    return {
        "backend": "sqlite_fts5",
        "retrieval_mode": "lexical_bm25",
        "semantic_embeddings_enabled": False,
        "documents_seen": len(docs),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "deleted": len(stale),
        "source_counts": dict(sorted(counts.items())),
    }


def search_memory(
    store: Store,
    query: str,
    *,
    limit: int = 10,
    include_candidates: bool = False,
    source_types: Iterable[str] | None = None,
    refresh: bool = True,
) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query cannot exceed {MAX_QUERY_CHARS} characters")
    limit = int(limit)
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    selected_sources = list(source_types or [])
    if any(item not in SOURCE_TYPES for item in selected_sources):
        raise ValueError(f"source_types must be drawn from {sorted(SOURCE_TYPES)}")

    raw_terms = re.findall(r"[^\W_]+(?:[_-][^\W_]+)*", query, flags=re.UNICODE)
    terms: list[str] = []
    for term in raw_terms:
        if len(term) >= 2 and term.lower() not in terms:
            terms.append(term.lower())
        if len(terms) >= MAX_QUERY_TERMS:
            break
    if not terms:
        raise ValueError("query must contain at least one searchable term of 2+ characters")
    # Each user term is quoted independently so FTS operators/punctuation are not executable syntax.
    match_expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)

    index_status = refresh_memory_index(store) if refresh else None
    filters: list[str] = []
    params: list[Any] = [match_expression]
    if include_candidates:
        filters.append("d.trust_status != 'rejected'")
    else:
        filters.append("d.trust_status NOT IN ('candidate', 'rejected')")
    if selected_sources:
        filters.append("d.source_type IN (" + ",".join("?" for _ in selected_sources) + ")")
        params.extend(selected_sources)
    where = (" AND " + " AND ".join(filters)) if filters else ""

    with store._connect() as conn:
        rows = conn.execute(
            f"""SELECT d.doc_id, d.source_type, d.source_ref, d.title, d.body,
                       d.trust_status, d.observed_at, d.metadata_json,
                       bm25(memory_fts, 4.0, 0.0, 0.0, 5.0, 1.0) AS rank,
                       snippet(memory_fts, 4, '[', ']', ' … ', 18) AS excerpt
                FROM memory_fts
                JOIN memory_documents d ON d.doc_id=memory_fts.doc_id
                WHERE memory_fts MATCH ?{where}
                ORDER BY rank ASC, d.observed_at DESC
                LIMIT ?""",
            params + [limit],
        ).fetchall()

    results = []
    for row in rows:
        results.append({
            "doc_id": row["doc_id"],
            "source_type": row["source_type"],
            "source_ref": row["source_ref"],
            "title": row["title"],
            "trust_status": row["trust_status"],
            "observed_at": row["observed_at"],
            "relevance_score": round(max(0.0, -float(row["rank"])), 8),
            "excerpt": row["excerpt"],
            "metadata": json.loads(row["metadata_json"]),
        })
    return {
        "query": query,
        "backend": "sqlite_fts5",
        "retrieval_mode": "lexical_bm25",
        "semantic_embeddings_enabled": False,
        "candidate_filter": "included" if include_candidates else "excluded",
        "source_filter": selected_sources or "all",
        "indexed_documents": index_status["documents_seen"] if index_status else None,
        "index_refresh": index_status,
        "result_count": len(results),
        "results": results,
    }