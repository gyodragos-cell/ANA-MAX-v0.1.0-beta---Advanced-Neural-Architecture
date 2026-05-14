"""
Learning helpers for ANA Engineer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.repair_controller import normalize_error_signature

logger = logging.getLogger(__name__)


class LocalLearningLab:
    """Extract reusable patterns from Engineer runs."""

    def __init__(self, memory):
        self.memory = memory

    def learn_from_run(self, run_id: str) -> Dict[str, Any]:
        run = self.memory.get_engineer_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        learned_patterns: List[Dict[str, Any]] = []
        failure_count = 0

        for step in run.get("steps", []):
            details = step.get("details", {}) or {}
            error_text = details.get("error")
            if not error_text and isinstance(details.get("result"), dict):
                error_text = details["result"].get("error")

            if not error_text:
                continue

            failure_count += 1
            signature = normalize_error_signature(str(error_text))
            patch_hint = details.get("patch_hint", step.get("title", ""))
            self.memory.record_repair_pattern(
                signature,
                strategy=f"learned_from_run:{run.get('profile', 'engineer')}",
                successful=step.get("status") == "completed",
                patch_hint=patch_hint,
                example_error=str(error_text),
                metadata={"run_id": run_id, "stage": step.get("stage")},
            )
            learned_patterns.append({
                "signature": signature,
                "stage": step.get("stage"),
                "status": step.get("status"),
            })

        summary = {
            "run_id": run_id,
            "profile": run.get("profile"),
            "failures_seen": failure_count,
            "patterns_recorded": len(learned_patterns),
            "patterns": learned_patterns,
        }
        logger.info("Lab learned %s patterns from run %s", len(learned_patterns), run_id)
        return summary
