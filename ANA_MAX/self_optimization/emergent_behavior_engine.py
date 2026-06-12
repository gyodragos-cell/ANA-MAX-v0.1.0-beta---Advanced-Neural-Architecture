"""Emergent behavior helpers for OS-16+ additive layers."""

from __future__ import annotations

from typing import Any

from ANA_MAX.self_optimization.osx_level_common import build_memory_snapshot, utc_now


def build_emergent_behavior(
    meta_reasoning: dict[str, Any] | None = None,
    anticipation: dict[str, Any] | None = None,
    emotional_map: dict[str, Any] | None = None,
    memory_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = memory_snapshot or build_memory_snapshot()
    reasoning = meta_reasoning or {}
    forecast = anticipation or {}
    emotion = emotional_map or {}
    consistency = snapshot.get("consistency", {}) if isinstance(snapshot, dict) else {}

    patterns = [
        "bounded_additive_growth",
        "memory_guided_phase_ordering",
        "stability_first_orchestration",
    ]
    if not bool(consistency.get("overall_consistent", True)):
        patterns.append("repair_before_expansion")
    if emotion.get("tone") == "cautious":
        patterns.append("conservative_feedback_loop")

    feedback_loops = [
        "observe -> reason -> anticipate -> map -> stabilize",
        "consolidate -> verify -> summarize -> repeat",
    ]
    if forecast.get("summary", {}).get("risk_count", 0) == 0:
        feedback_loops.append("reuse current stable path")

    return {
        "schema": "ana.os16.emergent_behavior.v1",
        "generated_at": utc_now(),
        "patterns": patterns,
        "feedback_loops": feedback_loops,
        "summary": {
            "pattern_count": len(patterns),
            "feedback_loop_count": len(feedback_loops),
            "reasoning_count": reasoning.get("summary", {}).get("inference_count", 0),
        },
    }
