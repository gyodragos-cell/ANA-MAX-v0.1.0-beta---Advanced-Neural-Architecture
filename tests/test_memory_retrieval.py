from __future__ import annotations

import json
from pathlib import Path

import pytest

from os29.models import TraceEvent
from os29.retrieval import refresh_memory_index, search_memory
from os29.store import Store


def _capsule(objective: str) -> dict:
    return {
        "project": "fixture-project",
        "objective": objective,
        "current_state": {"stage": "test"},
        "known_good": ["SQLite persistence"],
        "known_bad": [],
        "open_issues": ["gateway health endpoint timeout"],
        "next_steps": ["run a bounded health probe"],
    }


def test_memory_search_retrieves_across_sources_and_filters_candidate_lessons(tmp_path: Path):
    store = Store(tmp_path / "retrieval.db")
    observed = store.record_event(TraceEvent(
        trace_id="trace-gateway-timeout",
        source="pytest",
        component="gateway-health",
        kind="http.response",
        action="gateway health endpoint timeout",
        outcome="error",
        attributes={"exception_type": "ReadTimeout", "status_code": 503},
    ).to_dict())
    store.create_incident("trace-gateway-timeout")
    store.save_capsule("mission-gateway", _capsule("Investigate the gateway health timeout"))
    store.upsert_capability(
        kind="service", name="gateway-health-probe", status="degraded",
        evidence={"port": 8766},
    )
    candidate = store.record_experience(
        problem_key="gateway health timeout recovery",
        cause="ReadTimeout on the local health endpoint",
        solution="use a bounded retry with exponential backoff",
        outcome="partial",
        source_event_ids=[observed["event_id"]],
    )

    ordinary = search_memory(store, "gateway health timeout", limit=20)
    assert ordinary["backend"] == "sqlite_fts5"
    assert ordinary["retrieval_mode"] == "lexical_bm25"
    assert ordinary["semantic_embeddings_enabled"] is False
    found_types = {item["source_type"] for item in ordinary["results"]}
    assert {"event", "incident", "capsule", "capability"}.issubset(found_types)
    assert not any(item["source_ref"] == candidate["lesson_id"] for item in ordinary["results"])

    with_candidates = search_memory(
        store, "gateway health timeout", limit=20,
        include_candidates=True, source_types=["experience"],
    )
    assert with_candidates["result_count"] == 1
    assert with_candidates["results"][0]["source_ref"] == candidate["lesson_id"]
    assert with_candidates["results"][0]["trust_status"] == "candidate"


def test_memory_index_redacts_sensitive_values_and_omits_unapproved_event_fields(tmp_path: Path):
    store = Store(tmp_path / "retrieval-redaction.db")
    store.record_event(TraceEvent(
        trace_id="trace-secret-check",
        source="pytest",
        component="health-check",
        kind="http.response",
        action="health endpoint check",
        outcome="error",
        target="http://127.0.0.1:8766/health?token=very-secret-token-value",
        attributes={
            "exception_type": "ReadTimeout",
            "Authorization": "Bearer never-index-this-bearer",
            "request_body": "private payload should not be indexed",
        },
    ).to_dict())

    refresh_memory_index(store)
    with store._connect() as conn:
        rows = conn.execute("SELECT title, body, metadata_json FROM memory_documents").fetchall()
    all_text = json.dumps([dict(row) for row in rows], ensure_ascii=True)
    assert "very-secret-token-value" not in all_text
    assert "never-index-this-bearer" not in all_text
    assert "private payload should not be indexed" not in all_text
    assert "ReadTimeout" in all_text


def test_memory_index_incremental_update_and_stale_text_removal(tmp_path: Path):
    store = Store(tmp_path / "retrieval-update.db")
    store.save_capsule("mission-retrieval", _capsule("Blue comet is the old test objective"))
    first = refresh_memory_index(store)
    assert first["inserted"] >= 1
    second = refresh_memory_index(store)
    assert second["unchanged"] == second["documents_seen"]
    assert second["inserted"] == 0
    assert second["updated"] == 0

    store.save_capsule("mission-retrieval", _capsule("Amber lantern is the new test objective"))
    changed = refresh_memory_index(store)
    assert changed["updated"] == 1
    old_result = search_memory(store, "blue comet", source_types=["capsule"])
    new_result = search_memory(store, "amber lantern", source_types=["capsule"])
    assert old_result["result_count"] == 0
    assert new_result["result_count"] == 1


def test_memory_search_validates_query_limits_and_source_types(tmp_path: Path):
    store = Store(tmp_path / "retrieval-validation.db")
    with pytest.raises(ValueError, match="non-empty"):
        search_memory(store, " ")
    with pytest.raises(ValueError, match="searchable term"):
        search_memory(store, "!")
    with pytest.raises(ValueError, match="source_types"):
        search_memory(store, "gateway", source_types=["arbitrary"])
    with pytest.raises(ValueError, match="between 1 and 100"):
        search_memory(store, "gateway", limit=101)


def test_memory_search_indexes_only_explicit_local_document_sources(tmp_path: Path):
    db_root = tmp_path
    config_dir = db_root / "config"
    docs_dir = db_root / "docs"
    config_dir.mkdir()
    docs_dir.mkdir()
    approved = docs_dir / "approved.md"
    unapproved = docs_dir / "unapproved.md"
    approved.write_text(
        "# Frida MITM correlation\n\nOS29 correlates an approved Frida method span with a local MITM HTTP response.",
        encoding="utf-8",
    )
    unapproved.write_text(
        "# Private unrelated file\n\nThis phrase must never enter the retrieval index.",
        encoding="utf-8",
    )
    (config_dir / "memory_sources.json").write_text(
        json.dumps({
            "files": [str(approved)],
            "directories": [],
            "limits": {"max_file_bytes": 524288, "max_total_source_bytes": 8388608, "max_files": 200},
        }),
        encoding="utf-8",
    )
    store = Store(db_root / "os29.db")

    result = search_memory(store, "Frida MITM correlation", source_types=["document"])
    assert result["result_count"] == 1
    assert result["results"][0]["metadata"]["path"] == str(approved.resolve())
    assert "correlates" in result["results"][0]["excerpt"]

    with store._connect() as conn:
        indexed_bodies = " ".join(row[0] for row in conn.execute(
            "SELECT body FROM memory_documents WHERE source_type='document'"
        ).fetchall())
    assert "must never enter" not in indexed_bodies