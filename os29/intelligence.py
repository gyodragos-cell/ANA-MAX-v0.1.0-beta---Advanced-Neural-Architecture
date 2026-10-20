from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .store import Store


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _agent_label(event: dict[str, Any]) -> str | None:
    attributes = event.get("attributes") or {}
    if not isinstance(attributes, dict):
        return None
    for key in ("agent_id", "agent_name", "agent"):
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:128]
    return None


def _signature(event: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(event.get("component", "unknown"))[:160],
        str(event.get("kind", "unknown"))[:160],
        str(event.get("action", "unknown"))[:160],
    )


def _resource_snapshot() -> dict[str, Any]:
    """Read-only host resource telemetry. It never starts/stops services or models."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(".")
        cpu_percent = float(psutil.cpu_percent(interval=0.1))
        ram_percent = float(memory.percent)
        disk_percent = float(disk.percent)
        pressures = []
        if cpu_percent >= 85:
            pressures.append("cpu_pressure")
        if ram_percent >= 85:
            pressures.append("memory_pressure")
        if disk_percent >= 90:
            pressures.append("disk_pressure")
        return {
            "status": "observed",
            "cpu_percent": round(cpu_percent, 2),
            "ram_percent": round(ram_percent, 2),
            "ram_available_bytes": int(memory.available),
            "disk_percent": round(disk_percent, 2),
            "disk_free_bytes": int(disk.free),
            "pressure_signals": pressures,
            "gpu_state": "not_measured",
            "thresholds": {"cpu_warning_percent": 85, "ram_warning_percent": 85, "disk_warning_percent": 90},
            "action_taken": "none_read_only_observation",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "gpu_state": "not_measured",
            "action_taken": "none",
        }


def _temporal_branch(event: dict[str, Any]) -> dict[str, Any]:
    attributes = event.get("attributes") or {}
    status_code = attributes.get("status_code") if isinstance(attributes, dict) else None
    exception_type = str(attributes.get("exception_type", "")) if isinstance(attributes, dict) else ""
    action_text = str(event.get("action", ""))
    if isinstance(status_code, int) and status_code >= 500:
        experiment = "Replay the same safe request against a controlled test endpoint while recording dependency health and one retry-free baseline."
        expected = "Determine whether the server-side failure is reproducible independently of the client."
        falsifier = "The controlled endpoint is healthy and repeated failures cannot be reproduced."
    elif "timeout" in exception_type.lower() or "timeout" in action_text.lower():
        experiment = "Separate connection establishment time from response-read time using a bounded benign probe; compare with a baseline."
        expected = "Identify whether delay occurs before connection or while waiting for the response."
        falsifier = "Both phases complete within baseline bounds and the timeout cannot be reproduced."
    elif event.get("kind", "").startswith("frida.method.exit"):
        experiment = "Repeat the approved test method once with a shared trace ID and compare method entry/exit to the matching HTTP status."
        expected = "Establish whether the method exception and HTTP event occur in the same trace."
        falsifier = "No matching HTTP event exists or the method outcome is stable on the controlled retest."
    else:
        experiment = "Create the smallest benign reproducer and collect a fresh trace with an explicit parent-event chain before changing code."
        expected = "Produce a repeatable failure signature and a trace that can distinguish competing hypotheses."
        falsifier = "The minimal reproducer is stable and no corresponding failure recurs."
    return {
        "branch_id": f"branch-review-{event.get('event_id', 'unknown')}",
        "based_on_event_id": event.get("event_id"),
        "trace_id": event.get("trace_id"),
        "component": event.get("component"),
        "action": event.get("action"),
        "hypothesis": "Unverified hypothesis generated from an observed failure; not a root-cause finding.",
        "experiment": experiment,
        "expected_observation": expected,
        "falsifying_observation": falsifier,
        "status": "proposed_not_executed",
        "automatic_execution": False,
    }


def build_intelligence_report(store: Store, *, event_limit: int = 1000) -> dict[str, Any]:
    """Evidence-first report spanning Agent DNA, REM, Regret, Discovery, immunity and branching."""
    event_limit = max(1, min(int(event_limit), 1000))
    sampled_events = store.recent_events(limit=event_limit)
    synthetic_event_ids = {
        event.get("event_id")
        for event in sampled_events
        if isinstance(event.get("attributes"), dict) and event["attributes"].get("synthetic") is True
    }
    events = [
        event for event in sampled_events
        if not (isinstance(event.get("attributes"), dict) and event["attributes"].get("synthetic") is True)
    ]

    all_experiences = store.list_experiences(limit=1000)
    synthetic_experience_ids = set()
    experiences = []
    for item in all_experiences:
        source_ids = item.get("source_event_ids", [])
        if source_ids and set(source_ids).issubset(synthetic_event_ids):
            synthetic_experience_ids.add(item["lesson_id"])
            continue
        experiences.append(item)
    validated = [item for item in experiences if item.get("status") == "validated"]
    candidates = [item for item in experiences if item.get("status") == "candidate"]
    nodes = store.list_capabilities(limit=2000)
    edges = store.list_capability_edges(limit=5000)
    edge_node_ids = {
        endpoint
        for edge in edges
        for endpoint in (edge.get("source_node_id"), edge.get("target_node_id"))
        if endpoint
    }

    # Agent DNA and reputation are reported only when events explicitly identify an agent.
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        label = _agent_label(event)
        if label:
            by_agent[label].append(event)
    agent_profiles = []
    for agent, samples in sorted(by_agent.items()):
        definitive = [event for event in samples if event.get("outcome") in {"success", "failure", "error"}]
        successes = sum(event.get("outcome") == "success" for event in definitive)
        failures = sum(event.get("outcome") in {"failure", "error"} for event in definitive)
        durations = [
            float(event["duration_ms"])
            for event in samples
            if isinstance(event.get("duration_ms"), (int, float))
            and not isinstance(event.get("duration_ms"), bool)
            and 0 <= event["duration_ms"] < float("inf")
        ]
        enough = len(definitive) >= 10
        agent_profiles.append({
            "agent": agent,
            "event_count": len(samples),
            "definitive_outcome_count": len(definitive),
            "success_count": successes,
            "failure_or_error_count": failures,
            "success_rate": round(successes / len(definitive), 4) if definitive else None,
            "mean_observed_duration_ms": round(sum(durations) / len(durations), 3) if durations else None,
            "confidence": "eligible_for_review" if enough else "insufficient_evidence",
            "evidence_event_ids": [event["event_id"] for event in samples[:20]],
        })

    failures = [event for event in events if event.get("outcome") in {"failure", "error"}]
    failure_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in failures:
        failure_groups[_signature(event)].append(event)
    failure_memory = []
    for signature, samples in sorted(failure_groups.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        failure_memory.append({
            "component": signature[0],
            "kind": signature[1],
            "action": signature[2],
            "occurrences_in_window": len(samples),
            "trace_ids": sorted({str(event.get("trace_id")) for event in samples}),
            "event_ids": [event["event_id"] for event in samples[:20]],
            "review_priority": "recurrent" if len(samples) >= 2 else "single_observation",
            "causal_status": "unverified",
        })

    validated_sources = {event_id for item in validated for event_id in item.get("source_event_ids", [])}
    regret_candidates = []
    for signature, samples in failure_groups.items():
        if len(samples) < 2:
            continue
        unresolved = [event for event in samples if event.get("event_id") not in validated_sources]
        if unresolved:
            regret_candidates.append({
                "component": signature[0],
                "kind": signature[1],
                "action": signature[2],
                "repeated_failure_count": len(samples),
                "unlinked_failure_count": len(unresolved),
                "evidence_event_ids": [event["event_id"] for event in unresolved[:20]],
                "regret_score": None,
                "reason": "Repeated failures have no linked validated experience; cost and avoidability have not been established.",
                "status": "candidate_for_operator_review",
            })
    regret_candidates.sort(key=lambda item: (-item["repeated_failure_count"], item["component"], item["action"]))

    validated_by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in validated:
        validated_by_problem[str(item.get("problem_key", ""))].append(item)
    distilled_skills = [
        {
            "problem_key": problem,
            "validated_instance_count": len(items),
            "lesson_ids": [item["lesson_id"] for item in items],
            "source_event_ids": sorted({event_id for item in items for event_id in item.get("source_event_ids", [])}),
            "status": "repeated_validated_pattern",
        }
        for problem, items in validated_by_problem.items()
        if problem and len(items) >= 2
    ]

    degraded_nodes = [
        {
            "kind": node.get("kind"),
            "name": node.get("name"),
            "status": node.get("status"),
            "observed_at": node.get("observed_at"),
        }
        for node in nodes
        if node.get("status") in {"offline", "degraded", "unknown"}
    ]
    orphans = [
        {
            "kind": node.get("kind"),
            "name": node.get("name"),
            "status": node.get("status"),
            "node_id": node.get("node_id"),
        }
        for node in nodes
        if node.get("node_id") not in edge_node_ids
    ]
    wildcard_risks = []
    for node in nodes:
        evidence = node.get("evidence") or {}
        if node.get("kind") == "port" and isinstance(evidence, dict) and evidence.get("wildcard_binding"):
            wildcard_risks.append({
                "name": node.get("name"),
                "node_id": node.get("node_id"),
                "status": node.get("status"),
                "evidence": evidence,
            })

    scope_denials = [
        event for event in events
        if event.get("source") == "os29.scope" and event.get("outcome") == "blocked"
    ]
    immune_signals = []
    if scope_denials:
        immune_signals.append({"signal": "out_of_scope_target_denials", "count": len(scope_denials), "event_ids": [e["event_id"] for e in scope_denials[:20]]})
    if wildcard_risks:
        immune_signals.append({"signal": "wildcard_listener_binding", "count": len(wildcard_risks), "evidence": wildcard_risks})
    recurrent_count = sum(1 for items in failure_groups.values() if len(items) >= 2)
    if recurrent_count:
        immune_signals.append({"signal": "recurrent_failure_signature", "count": recurrent_count})
    immune_status = "review_needed" if immune_signals else "no_high_confidence_signal_in_window"

    temporal_branches = [_temporal_branch(event) for event in failures[:10]]

    resource_snapshot = _resource_snapshot()
    resource_pressures = resource_snapshot.get("pressure_signals", [])
    resource_recommendations = []
    if "cpu_pressure" in resource_pressures or "memory_pressure" in resource_pressures:
        resource_recommendations.append("Prefer incremental reads and bounded batches until CPU/RAM pressure declines.")
    if "disk_pressure" in resource_pressures:
        resource_recommendations.append("Review capture retention and artifact size before starting additional capture jobs.")
    if not resource_recommendations:
        resource_recommendations.append("No configured CPU/RAM/disk pressure threshold was crossed in this sample.")
    return {
        "schema_version": "os29.intelligence_report.v1",
        "generated_at": _utc_now(),
        "evidence_window": {
            "max_events_examined": event_limit,
            "events_examined": len(events),
            "synthetic_fixture_events_excluded": len(sampled_events) - len(events),
            "synthetic_fixture_experiences_excluded": len(synthetic_experience_ids),
        },
        "agent_dna": {
            "explicitly_labeled_agent_count": len(agent_profiles),
            "profiles": agent_profiles,
            "confidence_rule": "Success rates require at least 10 definitive outcomes; no agent identity is inferred from source names.",
        },
        "rem_engine": {
            "status": "complete",
            "events_examined": len(events),
            "failure_events_in_window": len(failures),
            "failure_signature_count": len(failure_groups),
            "recurrent_failure_signatures": recurrent_count,
            "review_candidates": failure_memory[:50],
            "note": "Synthetic fixture events are excluded. REM observations are evidence candidates, not root-cause determinations.",
        },
        "regret_engine": {
            "status": "complete",
            "review_candidate_count": len(regret_candidates),
            "candidates": regret_candidates[:50],
            "note": "Regret score remains null unless cost, avoidability and a validated alternative are established.",
        },
        "temporal_branching": {
            "status": "proposed_only",
            "branch_count": len(temporal_branches),
            "branches": temporal_branches,
            "note": "Branches are falsifiable test plans, not executed simulations or live changes.",
        },
        "skill_distillation": {
            "validated_experience_count": len(validated),
            "candidate_experience_count": len(candidates),
            "distilled_validated_patterns": distilled_skills,
            "candidate_lessons_not_promoted": [
                {"lesson_id": item["lesson_id"], "problem_key": item["problem_key"], "source_event_ids": item["source_event_ids"]}
                for item in candidates[:50]
            ],
            "note": "Synthetic-only lessons are excluded; no skill or memory is promoted from an unvalidated candidate.",
        },
        "digital_immune_system": {
            "status": immune_status,
            "signals": immune_signals,
            "scope_denial_count": len(scope_denials),
            "wildcard_listener_risk_count": len(wildcard_risks),
            "recurrent_failure_signature_count": recurrent_count,
            "note": "This is read-only detection from the sampled local evidence; it is not an endpoint protection system and takes no repair action.",
        },
        "discovery_engine": {
            "degraded_or_offline_capabilities": degraded_nodes[:100],
            "unlinked_graph_nodes": orphans[:100],
            "wildcard_listener_risks": wildcard_risks,
            "recommendations": [
                "Review whether offline services are intentionally disabled before starting anything.",
                "Connect one explicitly approved test app to complete Frida-to-HTTP trace correlation.",
                "Validate a real fix/retest before promoting an experience.",
            ] if not validated else [
                "Measure subsequent-session retrieval of validated experiences against a known test result.",
            ],
        },
        "resource_aware_cognition": {
            **resource_snapshot,
            "recommendations": resource_recommendations,
            "resource_scheduler_active": False,
        },
        "self_building_guard": {
            "status": "suggestion_only",
            "automatic_code_changes": False,
            "automatic_policy_changes": False,
            "recommendation": "Convert recurring evidence into a reviewed patch proposal and a regression test; apply changes only through an explicit operator workflow.",
        },
        "resource_policy": {
            "auto_start_performed": False,
            "optional_local_inference_start_performed": False,
            "recommendation": "Do not start offline model/gateway services automatically; require an explicit mission and resource-budget check.",
        },
        "store": store.stats(),
    }