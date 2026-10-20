from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .models import TraceEvent, utc_now
from .redaction import redact_value, sanitize_url


MAX_EVENT_JSON_BYTES = 1_048_576
MAX_CAPSULE_JSON_BYTES = 262_144
MAX_EVIDENCE_JSON_BYTES = 262_144
MAX_EXPERIENCE_TEXT_BYTES = 65_536


def _bounded_json(value: Any, max_bytes: int, label: str) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite JSON data") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} exceeds the {max_bytes}-byte storage limit")
    return encoded


class Store:
    """SQLite-backed append-oriented evidence, capsule and experience store."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trace_events (
                    event_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    parent_event_id TEXT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    component TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    target TEXT,
                    mission_id TEXT,
                    duration_ms REAL,
                    event_json TEXT NOT NULL,
                    redaction_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_events_trace_time ON trace_events(trace_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_kind_outcome ON trace_events(kind, outcome);
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    cause_hypothesis TEXT NOT NULL,
                    evidence_event_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_incidents_trace ON incidents(trace_id);
                CREATE TABLE IF NOT EXISTS mission_capsules (
                    mission_id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capsule_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiences (
                    lesson_id TEXT PRIMARY KEY,
                    problem_key TEXT NOT NULL,
                    cause TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('candidate','validated','rejected')),
                    verified_by TEXT,
                    source_event_ids_json TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    times_applied INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_experiences_problem ON experiences(problem_key, status);
                CREATE TABLE IF NOT EXISTS capability_nodes (
                    node_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT,
                    evidence_json TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(kind, name)
                );
                CREATE TABLE IF NOT EXISTS capability_edges (
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY(source_node_id, target_node_id, relation),
                    FOREIGN KEY(source_node_id) REFERENCES capability_nodes(node_id),
                    FOREIGN KEY(target_node_id) REFERENCES capability_nodes(node_id)
                );
                CREATE TABLE IF NOT EXISTS memory_documents (
                    doc_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    trust_status TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memory_documents_source
                    ON memory_documents(source_type, trust_status);
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    doc_id UNINDEXED,
                    source_type UNINDEXED,
                    trust_status UNINDEXED,
                    title,
                    body,
                    tokenize='unicode61 remove_diacritics 2'
                );
                """
            )

    def record_event(self, event: TraceEvent | dict[str, Any]) -> dict[str, Any]:
        if isinstance(event, dict):
            event = TraceEvent.from_dict(event)
        event.validate()
        value = event.to_dict()
        value, redactions = redact_value(value)
        if value.get("target"):
            value["target"], count = sanitize_url(str(value["target"]))
            redactions += count
        event_json = _bounded_json(value, MAX_EVENT_JSON_BYTES, "trace event")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO trace_events
                (event_id, trace_id, parent_event_id, timestamp, source, component, kind,
                 action, outcome, target, mission_id, duration_ms, event_json, redaction_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    value["event_id"], value["trace_id"], value.get("parent_event_id"),
                    value["timestamp"], value["source"], value["component"], value["kind"],
                    value["action"], value["outcome"], value.get("target"), value.get("mission_id"),
                    value.get("duration_ms"), event_json, redactions,
                ),
            )
        return {"event_id": value["event_id"], "trace_id": value["trace_id"], "redactions": redactions}

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT event_json FROM trace_events WHERE event_id=?", (event_id,)).fetchone()
        return json.loads(row["event_json"]) if row else None

    def list_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_json FROM trace_events WHERE trace_id=? ORDER BY timestamp, rowid",
                (trace_id,),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_json FROM trace_events ORDER BY timestamp DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def trace_summary(self, trace_id: str) -> dict[str, Any]:
        events = self.list_trace(trace_id)
        failures = [e for e in events if e.get("outcome") in {"failure", "error"}]
        event_ids = {e["event_id"] for e in events}
        parent_edges = [
            {
                "source_event_id": e["parent_event_id"],
                "target_event_id": e["event_id"],
                "relation": "parent_of",
            }
            for e in events
            if e.get("parent_event_id") and e["parent_event_id"] in event_ids
        ]
        orphan_parent_refs = sorted({
            e["parent_event_id"] for e in events
            if e.get("parent_event_id") and e["parent_event_id"] not in event_ids
        })
        return {
            "trace_id": trace_id,
            "event_count": len(events),
            "sources": sorted({e.get("source", "unknown") for e in events}),
            "components": sorted({e.get("component", "unknown") for e in events}),
            "failure_count": len(failures),
            "event_ids": [e["event_id"] for e in events],
            "parent_edge_count": len(parent_edges),
            "parent_edges": parent_edges,
            "orphan_parent_event_ids": orphan_parent_refs,
            "correlation_basis": "shared trace_id and explicit parent_event_id; correlation is not proof of causation",
        }

    def create_incident(self, trace_id: str) -> dict[str, Any]:
        events = self.list_trace(trace_id)
        failures = [e for e in events if e.get("outcome") in {"failure", "error"}]
        if not failures:
            raise ValueError("no failure/error event exists in the requested trace")
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT incident_id FROM incidents WHERE trace_id=? AND status='open' ORDER BY created_at DESC LIMIT 1",
                (trace_id,),
            ).fetchone()
        incident_id = existing["incident_id"] if existing else str(uuid4())
        first = failures[0]
        title = f"{first.get('component', 'unknown')} — {first.get('action', 'failure')}"
        evidence_ids = [e["event_id"] for e in failures]
        summary = f"{len(failures)} failure/error event(s) observed among {len(events)} trace event(s)."
        cause = "UNVERIFIED: correlated evidence only; a root cause has not been established."
        now = utc_now()
        with self._connect() as conn:
            if existing:
                conn.execute(
                    """UPDATE incidents SET title=?, summary=?, cause_hypothesis=?,
                       evidence_event_ids_json=?, updated_at=? WHERE incident_id=? AND status='open'""",
                    (title, summary, cause, json.dumps(evidence_ids), now, incident_id),
                )
            else:
                conn.execute(
                    """INSERT INTO incidents
                    (incident_id, trace_id, title, status, summary, cause_hypothesis,
                     evidence_event_ids_json, created_at, updated_at)
                    VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?)""",
                    (incident_id, trace_id, title, summary, cause, json.dumps(evidence_ids), now, now),
                )
        return self.get_incident(incident_id)  # type: ignore[return-value]

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE incident_id=?", (incident_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["evidence_event_ids"] = json.loads(result.pop("evidence_event_ids_json"))
        return result

    def save_capsule(self, mission_id: str, capsule: dict[str, Any]) -> dict[str, Any]:
        if not mission_id.strip():
            raise ValueError("mission_id is required")
        required = ("project", "objective", "current_state", "known_good", "known_bad", "open_issues", "next_steps")
        for field_name in required:
            if field_name not in capsule:
                raise ValueError(f"capsule is missing required field: {field_name}")
        safe, redactions = redact_value(capsule)
        if not isinstance(safe.get("project"), str) or not safe["project"].strip():
            raise ValueError("capsule project must be a non-empty string")
        if not isinstance(safe.get("objective"), str) or not safe["objective"].strip():
            raise ValueError("capsule objective must be a non-empty string")
        for field_name in ("known_good", "known_bad", "open_issues", "next_steps"):
            if not isinstance(safe[field_name], list):
                raise ValueError(f"capsule {field_name} must be a list")
        now = utc_now()
        encoded = _bounded_json(safe, MAX_CAPSULE_JSON_BYTES, "mission capsule")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO mission_capsules(mission_id, project, status, capsule_json, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET project=excluded.project,
                  status=excluded.status, capsule_json=excluded.capsule_json, updated_at=excluded.updated_at""",
                (mission_id, str(safe["project"]), str(safe.get("status", "active")), encoded, now),
            )
        return {"mission_id": mission_id, "updated_at": now, "redactions": redactions, "capsule": safe}

    def get_capsule(self, mission_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT capsule_json, updated_at FROM mission_capsules WHERE mission_id=?", (mission_id,)).fetchone()
        if not row:
            return None
        return {"mission_id": mission_id, "updated_at": row["updated_at"], "capsule": json.loads(row["capsule_json"])}

    def record_experience(
        self,
        *,
        problem_key: str,
        cause: str,
        solution: str,
        outcome: str,
        source_event_ids: list[str],
        outcome_verified: bool = False,
        verified_by: str | None = None,
        confidence: float = 0.0,
    ) -> dict[str, Any]:
        if not all(isinstance(value, str) and value.strip() for value in (problem_key, cause, solution)):
            raise ValueError("problem_key, cause and solution are required non-empty strings")
        if sum(len(value.encode("utf-8")) for value in (problem_key, cause, solution)) > MAX_EXPERIENCE_TEXT_BYTES:
            raise ValueError("experience text fields exceed the storage size limit")
        if outcome not in {"success", "failure", "partial", "unknown"}:
            raise ValueError("outcome must be success/failure/partial/unknown")
        if not isinstance(source_event_ids, list) or not source_event_ids:
            raise ValueError("at least one source event is required")
        if len(source_event_ids) > 1000 or any(not isinstance(event_id, str) or not event_id.strip() for event_id in source_event_ids):
            raise ValueError("source_event_ids must contain at most 1000 non-empty strings")
        if len(set(source_event_ids)) != len(source_event_ids):
            raise ValueError("source_event_ids must be unique")
        with self._connect() as conn:
            placeholders = ",".join("?" for _ in source_event_ids)
            rows = conn.execute(
                f"SELECT event_id FROM trace_events WHERE event_id IN ({placeholders})",
                source_event_ids,
            ).fetchall()
        found = {row["event_id"] for row in rows}
        if found != set(source_event_ids):
            raise ValueError("all source_event_ids must reference persisted trace events")
        if outcome_verified or verified_by:
            raise ValueError("experience must start as candidate; use validate_experience with a linked verification event")
        status = "candidate"
        confidence = float(confidence)
        if not math.isfinite(confidence):
            raise ValueError("confidence must be finite")
        confidence = min(max(confidence, 0.0), 0.49)
        values = {
            "problem_key": problem_key, "cause": cause, "solution": solution,
            "outcome": outcome, "source_event_ids": source_event_ids, "verified_by": verified_by,
            "confidence": confidence,
        }
        safe, _ = redact_value(values)
        lesson_id = str(uuid4())
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO experiences(lesson_id, problem_key, cause, solution, outcome, status,
                verified_by, source_event_ids_json, confidence, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    lesson_id, safe["problem_key"], safe["cause"], safe["solution"], safe["outcome"],
                    status, safe["verified_by"], json.dumps(safe["source_event_ids"]),
                    safe["confidence"], now, now,
                ),
            )
        return self.get_experience(lesson_id)  # type: ignore[return-value]

    def validate_experience(
        self, *, lesson_id: str, verification_event_id: str,
        verified_by: str, confidence: float = 0.8,
    ) -> dict[str, Any]:
        """Promote a candidate only against a linked, persisted verification/test event."""
        if not verified_by.strip():
            raise ValueError("verified_by is required")
        confidence = float(confidence)
        if not math.isfinite(confidence) or confidence < 0.5 or confidence > 1.0:
            raise ValueError("validated confidence must be finite and between 0.5 and 1.0")
        candidate = self.get_experience(lesson_id)
        if not candidate:
            raise ValueError("experience not found")
        if candidate["status"] != "candidate":
            raise ValueError("only candidate experiences can be validated")
        source_ids = candidate["source_event_ids"]
        if verification_event_id not in source_ids:
            raise ValueError("verification event must already be linked in source_event_ids")
        verification = self.get_event(verification_event_id)
        if not verification:
            raise ValueError("verification event does not exist")
        attrs = verification.get("attributes", {})
        verification_kind = str(verification.get("kind", "")).lower()
        is_test_evidence = (
            verification_kind.startswith(("test.", "verification.", "acceptance."))
            or bool(attrs.get("ground_truth"))
            or attrs.get("verification") is True
        )
        if not is_test_evidence:
            raise ValueError("verification event must carry a test/verification kind or explicit ground_truth marker")
        outcome = verification.get("outcome")
        if outcome not in {"success", "failure"}:
            raise ValueError("verification event must have a definitive success/failure outcome")
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE experiences SET outcome=?, status='validated', verified_by=?,
                   confidence=?, updated_at=? WHERE lesson_id=? AND status='candidate'""",
                (outcome, verified_by, confidence, now, lesson_id),
            )
        result = self.get_experience(lesson_id)
        if not result or result["status"] != "validated":
            raise RuntimeError("experience validation state transition did not persist")
        return result

    def get_experience(self, lesson_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experiences WHERE lesson_id=?", (lesson_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["source_event_ids"] = json.loads(result.pop("source_event_ids_json"))
        return result

    def list_experiences(self, *, status: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        allowed = {None, "candidate", "validated", "rejected"}
        if status not in allowed:
            raise ValueError("status must be candidate/validated/rejected or null")
        with self._connect() as conn:
            if status is None:
                rows = conn.execute(
                    "SELECT * FROM experiences ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiences WHERE status=? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["source_event_ids"] = json.loads(item.pop("source_event_ids_json"))
            out.append(item)
        return out

    def search_experiences(self, query: str, *, include_candidates: bool = True, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        term = f"%{query.strip().lower()}%"
        status_filter = "" if include_candidates else " AND status='validated'"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiences WHERE (lower(problem_key) LIKE ? OR lower(cause) LIKE ? OR lower(solution) LIKE ?)"
                + status_filter + " ORDER BY CASE status WHEN 'validated' THEN 0 ELSE 1 END, updated_at DESC LIMIT ?",
                (term, term, term, limit),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["source_event_ids"] = json.loads(item.pop("source_event_ids_json"))
            out.append(item)
        return out

    def upsert_capability(
        self, *, kind: str, name: str, status: str, evidence: dict[str, Any],
        owner: str | None = None,
    ) -> dict[str, Any]:
        if not kind.strip() or not name.strip():
            raise ValueError("capability kind and name are required")
        allowed_status = {"declared", "configured", "running", "tested", "degraded", "offline", "unknown"}
        if status not in allowed_status:
            raise ValueError(f"status must be one of {sorted(allowed_status)}")
        if not isinstance(evidence, dict):
            raise ValueError("capability evidence must be a JSON object")
        safe, redactions = redact_value(evidence)
        evidence_json = _bounded_json(safe, MAX_EVIDENCE_JSON_BYTES, "capability evidence")
        now = utc_now()
        node_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO capability_nodes(node_id, kind, name, status, owner, evidence_json, observed_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(kind, name) DO UPDATE SET status=excluded.status, owner=excluded.owner,
                  evidence_json=excluded.evidence_json, observed_at=excluded.observed_at""",
                (node_id, kind, name, status, owner, evidence_json, now),
            )
            row = conn.execute("SELECT * FROM capability_nodes WHERE kind=? AND name=?", (kind, name)).fetchone()
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        result["redactions"] = redactions
        return result

    def upsert_capability_edge(
        self, *, source_node_id: str, target_node_id: str, relation: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not source_node_id or not target_node_id or not relation.strip():
            raise ValueError("source, target and relation are required")
        if evidence is not None and not isinstance(evidence, dict):
            raise ValueError("capability edge evidence must be a JSON object")
        safe, redactions = redact_value(evidence or {})
        evidence_json = _bounded_json(safe, MAX_EVIDENCE_JSON_BYTES, "capability edge evidence")
        now = utc_now()
        with self._connect() as conn:
            ids = {
                row["node_id"] for row in conn.execute(
                    "SELECT node_id FROM capability_nodes WHERE node_id IN (?, ?)",
                    (source_node_id, target_node_id),
                ).fetchall()
            }
            if ids != {source_node_id, target_node_id}:
                raise ValueError("both capability edge endpoints must already exist")
            conn.execute(
                """INSERT INTO capability_edges(source_node_id, target_node_id, relation, evidence_json, observed_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(source_node_id, target_node_id, relation) DO UPDATE SET
                  evidence_json=excluded.evidence_json, observed_at=excluded.observed_at""",
                (source_node_id, target_node_id, relation, evidence_json, now),
            )
        return {
            "source_node_id": source_node_id, "target_node_id": target_node_id,
            "relation": relation, "evidence": safe, "observed_at": now, "redactions": redactions,
        }

    def list_capability_edges(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT e.*, s.kind AS source_kind, s.name AS source_name,
                          t.kind AS target_kind, t.name AS target_name
                   FROM capability_edges e
                   JOIN capability_nodes s ON s.node_id=e.source_node_id
                   JOIN capability_nodes t ON t.node_id=e.target_node_id
                   ORDER BY e.observed_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            result.append(item)
        return result

    def list_capabilities(self, *, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM capability_nodes ORDER BY kind, name LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            result.append(item)
        return result

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            events = conn.execute("SELECT COUNT(*) FROM trace_events").fetchone()[0]
            traces = conn.execute("SELECT COUNT(DISTINCT trace_id) FROM trace_events").fetchone()[0]
            incidents = conn.execute("SELECT COUNT(*) FROM incidents WHERE status='open'").fetchone()[0]
            capsules = conn.execute("SELECT COUNT(*) FROM mission_capsules").fetchone()[0]
            candidates = conn.execute("SELECT COUNT(*) FROM experiences WHERE status='candidate'").fetchone()[0]
            validated = conn.execute("SELECT COUNT(*) FROM experiences WHERE status='validated'").fetchone()[0]
            capabilities = conn.execute("SELECT COUNT(*) FROM capability_nodes").fetchone()[0]
            capability_edges = conn.execute("SELECT COUNT(*) FROM capability_edges").fetchone()[0]
        return {
            "status": "ok", "schema_version": "os29.store.v1", "events": events,
            "traces": traces, "open_incidents": incidents, "mission_capsules": capsules,
            "experience_candidates": candidates, "validated_experiences": validated,
            "capability_nodes": capabilities, "capability_edges": capability_edges,
            "db_path": str(self.db_path),
        }