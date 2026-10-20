from __future__ import annotations

from pathlib import Path

import pytest

from os29.diagnosis import diagnose_trace
from os29.models import TraceEvent
from os29.store import Store


def event(trace_id: str, action: str, outcome: str = "observed", **kwargs) -> TraceEvent:
    return TraceEvent(
        trace_id=trace_id,
        source="pytest",
        component="sample_component",
        kind="sample.event",
        action=action,
        outcome=outcome,
        attributes=kwargs,
    )


def test_event_persists_after_store_reopen_and_redacts_values(tmp_path: Path):
    path = tmp_path / "nested" / "os29.db"
    first = Store(path)
    raw = event(
        "trace-persist-1",
        "GET /health",
        "observed",
        headers={"Authorization": "Bearer should-not-persist-this"},
        message="api_key=other-secret",
    )
    result = first.record_event(raw)
    assert result["redactions"] >= 2

    reopened = Store(path)
    recovered = reopened.get_event(result["event_id"])
    assert recovered is not None
    encoded = str(recovered)
    assert "should-not-persist-this" not in encoded
    assert "other-secret" not in encoded
    assert reopened.stats()["events"] == 1


def test_trace_parent_chain_and_incident_do_not_claim_root_cause(tmp_path: Path):
    store = Store(tmp_path / "trace.db")
    first = store.record_event(event("trace-fail", "request", "observed").to_dict())
    failed = store.record_event(
        TraceEvent(
            trace_id="trace-fail", source="mitmproxy", component="demo-api",
            kind="http.response", action="HTTP response", outcome="failure",
            parent_event_id=first["event_id"], attributes={"status_code": 503},
        ).to_dict()
    )
    diag = diagnose_trace(store, "trace-fail")
    assert diag["failure_count"] == 1
    assert diag["root_cause"] is None
    assert "not necessarily causation" in diag["hypothesis"]
    assert diag["incident"]["status"] == "open"
    assert diag["incident"]["evidence_event_ids"] == [failed["event_id"]]
    assert diag["explicit_parent_edges"] == [{
        "source_event_id": first["event_id"],
        "target_event_id": failed["event_id"],
        "relation": "parent_of",
    }]
    assert diag["failure_lineage"][0]["ancestor_event_ids_nearest_first"] == [first["event_id"]]
    assert diag["failure_lineage"][0]["warnings"] == []


def test_candidate_experience_requires_persisted_source_events(tmp_path: Path):
    store = Store(tmp_path / "experience.db")
    saved = store.record_event(event("trace-exp", "reproduce", "failure").to_dict())
    candidate = store.record_experience(
        problem_key="HTTP 503",
        cause="hypothesis only",
        solution="candidate workaround",
        outcome="partial",
        source_event_ids=[saved["event_id"]],
        outcome_verified=False,
    )
    assert candidate["status"] == "candidate"
    assert candidate["confidence"] <= 0.49
    assert store.search_experiences("503", include_candidates=False) == []
    assert len(store.search_experiences("503", include_candidates=True)) == 1


def test_experience_requires_a_linked_verification_event_to_validate(tmp_path: Path):
    store = Store(tmp_path / "experience-gate.db")
    observed = store.record_event(event("trace-exp-gate", "reproduce", "failure").to_dict())
    verification = store.record_event(
        TraceEvent(
            trace_id="trace-exp-gate", source="pytest", component="acceptance_suite",
            kind="test.completed", action="retest_known_fix", outcome="success",
            parent_event_id=observed["event_id"], attributes={"ground_truth": "test assertions passed"},
        ).to_dict()
    )

    with pytest.raises(ValueError, match="must start as candidate"):
        store.record_experience(
            problem_key="known fix", cause="reproduced cause", solution="verified fix",
            outcome="success", source_event_ids=[observed["event_id"], verification["event_id"]],
            outcome_verified=True, verified_by="pytest-acceptance", confidence=0.95,
        )

    candidate = store.record_experience(
        problem_key="known fix", cause="reproduced cause", solution="verified fix",
        outcome="partial", source_event_ids=[observed["event_id"], verification["event_id"]],
        outcome_verified=False, confidence=0.3,
    )
    assert candidate["status"] == "candidate"
    validated = store.validate_experience(
        lesson_id=candidate["lesson_id"], verification_event_id=verification["event_id"],
        verified_by="pytest-acceptance", confidence=0.95,
    )
    assert validated["status"] == "validated"
    assert validated["outcome"] == "success"
    assert validated["confidence"] == 0.95


def test_experience_validation_rejects_unlinked_or_non_test_evidence(tmp_path: Path):
    store = Store(tmp_path / "experience-negative-gate.db")
    observed = store.record_event(event("trace-neg", "request", "failure").to_dict())
    ordinary = store.record_event(event("trace-neg", "response", "success").to_dict())
    candidate = store.record_experience(
        problem_key="network issue", cause="unknown", solution="test later",
        outcome="partial", source_event_ids=[observed["event_id"], ordinary["event_id"]],
    )
    with pytest.raises(ValueError, match="test/verification kind"):
        store.validate_experience(
            lesson_id=candidate["lesson_id"], verification_event_id=ordinary["event_id"],
            verified_by="manual-review", confidence=0.8,
        )
    with pytest.raises(ValueError, match="linked"):
        store.validate_experience(
            lesson_id=candidate["lesson_id"], verification_event_id="not-linked",
            verified_by="manual-review", confidence=0.8,
        )


def test_incident_creation_is_idempotent_and_refreshes_evidence(tmp_path: Path):
    store = Store(tmp_path / "incident-idempotency.db")
    first_failure = store.record_event(event("trace-incident-idempotent", "call", "error").to_dict())
    first = store.create_incident("trace-incident-idempotent")
    second = store.create_incident("trace-incident-idempotent")
    assert first["incident_id"] == second["incident_id"]
    assert store.stats()["open_incidents"] == 1

    second_failure = store.record_event(event("trace-incident-idempotent", "retest", "failure").to_dict())
    refreshed = store.create_incident("trace-incident-idempotent")
    assert refreshed["incident_id"] == first["incident_id"]
    assert refreshed["evidence_event_ids"] == [first_failure["event_id"], second_failure["event_id"]]
    assert refreshed["summary"].startswith("2 failure/error event(s)")
    assert store.stats()["open_incidents"] == 1


def test_capsule_survives_restart_and_redacts_secrets(tmp_path: Path):
    path = tmp_path / "capsules.db"
    store = Store(path)
    capsule = {
        "project": "fixture",
        "objective": "verify capsule durability",
        "current_state": {"stage": "testing", "Authorization": "Bearer capsule-secret-value"},
        "known_good": ["SQLite"],
        "known_bad": [],
        "open_issues": ["integration pending"],
        "next_steps": ["rerun suite"],
        "notes": "token=private-capsule-token",
    }
    saved = store.save_capsule("mission-42", capsule)
    assert saved["redactions"] >= 2
    reopened = Store(path)
    value = reopened.get_capsule("mission-42")
    assert value is not None
    encoded = str(value["capsule"])
    assert "capsule-secret-value" not in encoded
    assert "private-capsule-token" not in encoded
    assert value["capsule"]["project"] == "fixture"


def test_capability_upsert_updates_same_node(tmp_path: Path):
    store = Store(tmp_path / "capabilities.db")
    a = store.upsert_capability(kind="service", name="local-test", status="running", evidence={"port": 8790})
    b = store.upsert_capability(kind="service", name="local-test", status="offline", evidence={"last_probe": "timeout"})
    assert a["node_id"] == b["node_id"]
    nodes = store.list_capabilities()
    assert len(nodes) == 1
    assert nodes[0]["status"] == "offline"


def test_event_schema_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown event fields"):
        TraceEvent.from_dict({
            "trace_id": "bad", "source": "test", "component": "x", "kind": "y", "action": "z",
            "outcome": "observed", "mystery": "not-allowed",
        })


def test_trace_event_rejects_nan_duration_and_non_string_parent():
    with pytest.raises(ValueError, match="finite non-negative"):
        TraceEvent(
            trace_id="trace-nan", source="test", component="x", kind="event",
            action="bad-duration", duration_ms=float("nan"),
        ).validate()
    with pytest.raises(ValueError, match="parent_event_id must be a string"):
        TraceEvent.from_dict({
            "trace_id": "trace-parent-type", "source": "test", "component": "x",
            "kind": "event", "action": "bad-parent", "parent_event_id": 42,
        })


def test_store_rejects_oversized_events_capsules_and_capability_evidence(tmp_path: Path):
    store = Store(tmp_path / "size-limits.db")
    too_large_event = event(
        "trace-too-large", "big-attributes", "observed",
        payload=["x" * 96 for _ in range(12000)],
    )
    with pytest.raises(ValueError, match="storage limit"):
        store.record_event(too_large_event)

    capsule = {
        "project": "fixture",
        "objective": "oversize check",
        "current_state": {"details": ["x" * 100 for _ in range(3000)]},
        "known_good": [],
        "known_bad": [],
        "open_issues": [],
        "next_steps": [],
    }
    with pytest.raises(ValueError, match="storage limit"):
        store.save_capsule("too-big-capsule", capsule)

    with pytest.raises(ValueError, match="storage limit"):
        store.upsert_capability(
            kind="test", name="too-big-evidence", status="configured",
            evidence={"items": ["e" * 100 for _ in range(4000)]},
        )


def test_experience_rejects_non_finite_confidence(tmp_path: Path):
    store = Store(tmp_path / "non-finite-confidence.db")
    saved = store.record_event(event("trace-finite", "test", "success").to_dict())
    with pytest.raises(ValueError, match="finite"):
        store.record_experience(
            problem_key="finite test", cause="known", solution="candidate",
            outcome="partial", source_event_ids=[saved["event_id"]], confidence=float("nan"),
        )