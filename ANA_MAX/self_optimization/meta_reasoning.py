"""Meta-reasoning helpers for OS-16+ additive layers."""

from __future__ import annotations

from typing import Any

from ANA_MAX.self_optimization.osx_level_common import baseline_metrics, build_memory_snapshot, utc_now


def build_meta_reasoning(
    memory_snapshot: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = memory_snapshot or build_memory_snapshot()
    base = baseline or baseline_metrics()
    consistency = snapshot.get("consistency", {}) if isinstance(snapshot, dict) else {}
    preferences = snapshot.get("preferences", {}) if isinstance(snapshot, dict) else {}
    stability_priority = str(preferences.get("stability_priority", "high"))
    warnings_tolerance = str(preferences.get("warnings_tolerance", "zero"))
    contradictions = int(consistency.get("contradiction_count", 0) or 0)
    regressions = int(consistency.get("regression_count", 0) or 0)

    assumptions = [
        "Keep OS-3/OS-4 schemas unchanged.",
        "Prefer additive, local-only changes.",
        "Treat memory snapshots as bounded summaries, not full state dumps.",
    ]
    inferences = [
        "Baseline health remains stable when health_score is 100 and warnings are 0.",
        f"Memory consistency currently reports {contradictions} contradictions and {regressions} regressions.",
    ]
    if base.get("overall_success", False):
        inferences.append("The evolution and daemon flows are both currently stable.")

    questions = [
        "Which additive layer would create the highest leverage with the least schema risk?",
        "Should conservative strategies remain the default while warnings tolerance stays zero?",
    ]
    guardrails = [
        "Preserve OS-3/OS-4 baseline reports.",
        "Never auto-enable dangerous tools.",
        "Keep outputs RAW-tagged and local-only.",
    ]
    if stability_priority == "high" or warnings_tolerance == "zero":
        guardrails.append("Prefer bounded recovery paths over aggressive expansion.")

    return {
        "schema": "ana.os16.meta_reasoning.v1",
        "generated_at": utc_now(),
        "baseline": base,
        "assumptions": assumptions,
        "inferences": inferences,
        "questions": questions,
        "guardrails": guardrails,
        "summary": {
            "assumption_count": len(assumptions),
            "inference_count": len(inferences),
            "question_count": len(questions),
            "guardrail_count": len(guardrails),
        },
    }
