from __future__ import annotations

from typing import Any

from .store import Store


def _failure_lineage(
    event: dict[str, Any], by_id: dict[str, dict[str, Any]], max_depth: int = 128
) -> dict[str, Any]:
    current = event
    visited = {event["event_id"]}
    ancestor_ids: list[str] = []
    warnings: list[str] = []
    while current.get("parent_event_id"):
        parent_id = current["parent_event_id"]
        if parent_id in visited:
            warnings.append("parent_cycle_detected")
            break
        parent = by_id.get(parent_id)
        if parent is None:
            warnings.append("parent_event_not_in_trace")
            break
        ancestor_ids.append(parent_id)
        visited.add(parent_id)
        current = parent
        if len(ancestor_ids) >= max_depth:
            warnings.append("lineage_depth_limit_reached")
            break
    return {
        "failure_event_id": event["event_id"],
        "ancestor_event_ids_nearest_first": ancestor_ids,
        "warnings": warnings,
        "root_cause": None,
    }


def diagnose_trace(store: Store, trace_id: str) -> dict[str, Any]:
    """Evidence-first diagnosis. Produces lineage and hypotheses, never asserted causality."""
    events = store.list_trace(trace_id)
    if not events:
        raise ValueError(f"trace not found: {trace_id}")
    failures = [event for event in events if event.get("outcome") in {"failure", "error"}]
    by_id = {event["event_id"]: event for event in events}
    components = [event.get("component", "unknown") for event in events]
    summary = store.trace_summary(trace_id)
    incident = store.create_incident(trace_id) if failures else None
    repeated_components = sorted({c for c in components if components.count(c) > 1})
    return {
        "trace_id": trace_id,
        "event_count": len(events),
        "failure_count": len(failures),
        "components_seen": list(dict.fromkeys(components)),
        "repeated_components": repeated_components,
        "explicit_parent_edges": summary["parent_edges"],
        "orphan_parent_event_ids": summary["orphan_parent_event_ids"],
        "observed_failures": [
            {
                "event_id": event["event_id"],
                "component": event["component"],
                "action": event["action"],
                "timestamp": event["timestamp"],
                "parent_event_id": event.get("parent_event_id"),
            }
            for event in failures
        ],
        "failure_lineage": [_failure_lineage(event, by_id) for event in failures],
        "root_cause": None,
        "hypothesis": (
            "Failure events are observed. Parent links show event lineage, not necessarily causation; independent reproduction or additional evidence is required."
            if failures else "No explicit failure/error outcome is recorded in this trace."
        ),
        "incident": incident,
        "correlation_basis": summary["correlation_basis"],
    }