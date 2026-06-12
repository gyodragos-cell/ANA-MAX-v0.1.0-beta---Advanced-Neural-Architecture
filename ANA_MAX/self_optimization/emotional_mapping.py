"""Emotional mapping helpers for OS-16+ additive layers."""

from __future__ import annotations

from typing import Any

from ANA_MAX.self_optimization.osx_level_common import baseline_metrics, build_memory_snapshot, utc_now


def map_emotional_state(
    memory_snapshot: dict[str, Any] | None = None,
    anticipation: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = memory_snapshot or build_memory_snapshot()
    base = baseline or baseline_metrics()
    consistency = snapshot.get("consistency", {}) if isinstance(snapshot, dict) else {}
    anticipation = anticipation or {}

    tone = "calm"
    if base.get("warnings", 0) > 0:
        tone = "guarded"
    if not bool(consistency.get("overall_consistent", True)):
        tone = "cautious"

    confidence = 0.98 if base.get("health_score", 0) == 100 else 0.82
    friction = "low" if tone == "calm" else "medium"
    if anticipation.get("summary", {}).get("risk_count", 0) > 0:
        friction = "medium"

    return {
        "schema": "ana.os16.emotional_mapping.v1",
        "generated_at": utc_now(),
        "tone": tone,
        "confidence": confidence,
        "friction": friction,
        "signals": {
            "health_score": base.get("health_score", 0),
            "warnings": base.get("warnings", 0),
            "consistency": bool(consistency.get("overall_consistent", True)),
        },
        "summary": {
            "tone": tone,
            "confidence": confidence,
            "friction": friction,
        },
    }
