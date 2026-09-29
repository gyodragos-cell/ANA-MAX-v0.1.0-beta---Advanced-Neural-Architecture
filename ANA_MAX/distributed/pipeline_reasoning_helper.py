"""OS-21.5 optional local-brain helper for pipeline metadata.

This helper never changes distributed pipeline execution. It only builds
review-only reasoning hints from existing pipeline metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents.local_brain_agent import LocalBrainAgent


PIPELINE_REASONING_SCHEMA = "ana.os21.pipeline_reasoning_helper.v1"
HELPER_NAME = "pipeline_reasoning_helper_v1"


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


class PipelineReasoningHelper:
    """Build optional local-brain summaries for pipeline metadata."""

    def __init__(self, agent: LocalBrainAgent | None = None, *, enable_inference: bool = False) -> None:
        self.agent = agent or LocalBrainAgent(enable_inference=enable_inference)
        self.enable_inference = bool(enable_inference)
        self._last_summary: dict[str, Any] | None = None

    def _pipeline_summary(self, pipeline_metadata: Mapping[str, Any]) -> dict[str, Any]:
        phases = pipeline_metadata.get("phases")
        tasks = pipeline_metadata.get("tasks")
        shards = pipeline_metadata.get("shards")
        schedule = pipeline_metadata.get("schedule")
        assignments = schedule.get("assignments") if isinstance(schedule, Mapping) else []
        return {
            "phase_count": _list_count(phases),
            "task_count": _list_count(tasks),
            "shard_count": _list_count(shards),
            "assignment_count": _list_count(assignments),
            "has_reasoning_graph": "reasoning_graph" in pipeline_metadata,
            "has_capsules": "capsules" in pipeline_metadata,
        }

    def summarize_pipeline(self, pipeline_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        metadata = dict(pipeline_metadata or {})
        pipeline_summary = self._pipeline_summary(metadata)
        user_prompt = metadata.get("user_prompt") or metadata.get("prompt") or metadata.get("query")
        brain_capsule = self.agent.build_reasoning_capsule(
            {
                "pipeline": pipeline_summary,
                "reasoning_graph": metadata.get("reasoning_graph", {}),
                "capsules": metadata.get("capsules", []),
            },
            user_prompt=user_prompt if isinstance(user_prompt, str) else None,
        )
        payload = {
            "schema": PIPELINE_REASONING_SCHEMA,
            "helper_name": HELPER_NAME,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "no_pipeline_execution": True,
            "enable_inference": self.enable_inference,
            "pipeline_summary": pipeline_summary,
            "local_brain": {
                "schema": brain_capsule.get("schema"),
                "used_llm": brain_capsule.get("reasoning_capsule", {}).get("used_llm", False),
                "backend_available": brain_capsule.get("backend", {}).get("available", False),
                "capsule_type": brain_capsule.get("reasoning_capsule", {}).get("capsule_type", "local_brain_reasoning"),
            },
            "plan_hints": [
                "Keep pipeline execution unchanged.",
                "Attach local-brain reasoning as metadata only.",
                "Promote to runtime use only behind a future explicit gate.",
            ],
            "reflection_hints": [
                "Check pipeline phase count before scheduling.",
                "Check shard count before migration planning.",
                "Use capsule lineage for future sync and merge reviews.",
            ],
            "reasoning_graph_hints": {
                "nodes": [
                    "helper:pipeline_reasoning_helper_v1",
                    "agent:local_brain_agent_v1",
                    "capsule_hint:local_brain_reasoning",
                ],
                "edges": [
                    {
                        "source": "helper:pipeline_reasoning_helper_v1",
                        "target": "agent:local_brain_agent_v1",
                        "relation": "delegates_to",
                    },
                    {
                        "source": "helper:pipeline_reasoning_helper_v1",
                        "target": "capsule_hint:local_brain_reasoning",
                        "relation": "summarizes",
                    },
                ],
            },
        }
        self._last_summary = payload
        return payload

    def summarize_helper(self) -> dict[str, Any]:
        return {
            "schema": PIPELINE_REASONING_SCHEMA,
            "helper_name": HELPER_NAME,
            "metadata_only": True,
            "local_only": True,
            "enable_inference": self.enable_inference,
            "last_summary_present": self._last_summary is not None,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build optional pipeline reasoning metadata.")
    parser.add_argument("--summary", action="store_true", help="Print compact helper summary")
    args = parser.parse_args(argv)
    helper = PipelineReasoningHelper()
    payload = helper.summarize_helper() if args.summary else helper.summarize_pipeline({})
    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
