from __future__ import annotations

from pathlib import Path

from os29.intelligence import build_intelligence_report
from os29.models import TraceEvent
from os29.store import Store


def test_intelligence_report_requires_explicit_agent_identity_and_surfaces_recurrent_failures(tmp_path: Path):
    store = Store(tmp_path / "intelligence.db")
    first = store.record_event(
        TraceEvent(
            trace_id="trace-rem-1", source="tool_runner", component="gateway",
            kind="http.response", action="GET /health", outcome="error",
            attributes={"exception_type": "ReadTimeout"},
        ).to_dict()
    )
    second = store.record_event(
        TraceEvent(
            trace_id="trace-rem-2", source="tool_runner", component="gateway",
            kind="http.response", action="GET /health", outcome="error",
            attributes={"exception_type": "ReadTimeout"},
        ).to_dict()
    )
    store.record_event(
        TraceEvent(
            trace_id="trace-agent-1", source="tool_runner", component="agent_task",
            kind="agent.step", action="inspect", outcome="success",
            attributes={"agent_name": "debug-agent"},
        ).to_dict()
    )
    report = build_intelligence_report(store, event_limit=100)

    assert report["agent_dna"]["explicitly_labeled_agent_count"] == 1
    profile = report["agent_dna"]["profiles"][0]
    assert profile["agent"] == "debug-agent"
    assert profile["confidence"] == "insufficient_evidence"
    assert report["rem_engine"]["recurrent_failure_signatures"] == 1
    assert report["rem_engine"]["review_candidates"][0]["event_ids"] == [
        second["event_id"], first["event_id"],
    ]
    assert report["regret_engine"]["candidates"][0]["regret_score"] is None
    assert report["resource_policy"]["auto_start_performed"] is False
    assert report["resource_policy"]["optional_local_inference_start_performed"] is False


def test_skill_distillation_uses_only_validated_experience(tmp_path: Path):
    store = Store(tmp_path / "distill.db")
    raw = store.record_event(
        TraceEvent(
            trace_id="trace-skill-1", source="pytest", component="verification",
            kind="test.completed", action="test_fix", outcome="success",
            attributes={"ground_truth": "assertions passed"},
        ).to_dict()
    )
    candidate = store.record_experience(
        problem_key="timeout recovery", cause="network timeout",
        solution="add explicit timeout and bounded retry", outcome="partial",
        source_event_ids=[raw["event_id"]], outcome_verified=False,
    )
    report = build_intelligence_report(store)
    assert report["skill_distillation"]["candidate_experience_count"] == 1
    assert report["skill_distillation"]["distilled_validated_patterns"] == []
    assert report["skill_distillation"]["candidate_lessons_not_promoted"][0]["lesson_id"] == candidate["lesson_id"]


def test_intelligence_handles_empty_store(tmp_path: Path):
    report = build_intelligence_report(Store(tmp_path / "empty.db"))
    assert report["agent_dna"]["profiles"] == []
    assert report["rem_engine"]["failure_events_in_window"] == 0
    assert report["regret_engine"]["review_candidate_count"] == 0
    assert report["discovery_engine"]["wildcard_listener_risks"] == []