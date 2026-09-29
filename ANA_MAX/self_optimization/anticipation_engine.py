"""Anticipation helpers for OS-16+ additive layers."""

from __future__ import annotations

from typing import Any

from ANA_MAX.self_optimization.osx_level_common import baseline_metrics, build_memory_snapshot, utc_now


def build_anticipation(
    meta_reasoning: dict[str, Any] | None = None,
    memory_snapshot: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = memory_snapshot or build_memory_snapshot()
    base = baseline or baseline_metrics()
    reasoning = meta_reasoning or {}
    consistency = snapshot.get("consistency", {}) if isinstance(snapshot, dict) else {}
    contradictions = int(consistency.get("contradiction_count", 0) or 0)
    regressions = int(consistency.get("regression_count", 0) or 0)

    risks = []
    if base.get("warnings", 0) > 0 or contradictions or regressions:
        risks.append("Repair and consolidation should precede any aggressive expansion.")
    else:
        risks.append("The current local-only ladder can continue bounded additive growth.")

    opportunities = [
        "Use stable memory context to bias future phase ordering.",
        "Surface recurring report patterns into the next planning cycle.",
        "Reuse deterministic outputs for local dashboards and summaries.",
    ]
    if reasoning.get("summary", {}).get("guardrail_count", 0) >= 3:
        opportunities.append("Tight guardrails make safe automation easier to extend.")

    next_actions = [
        "refresh_memory_snapshot",
        "compare_recent_reports",
        "prioritize_low_risk_additive_changes",
    ]

    return {
        "schema": "ana.os16.anticipation.v1",
        "generated_at": utc_now(),
        "risks": risks,
        "opportunities": opportunities,
        "next_actions": next_actions,
        "summary": {
            "risk_count": len(risks),
            "opportunity_count": len(opportunities),
            "next_action_count": len(next_actions),
        },
    }
