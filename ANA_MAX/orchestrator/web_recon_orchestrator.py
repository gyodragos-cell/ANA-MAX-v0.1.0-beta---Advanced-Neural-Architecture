"""
OS-21 web recon orchestrator v1.

This module is planning-only. It consumes BrowserReconAgent metadata and turns
it into a structured recon pipeline without executing browser actions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ANA_MAX.agents.browser_recon_agent import BrowserReconAgent


ORCHESTRATOR_SCHEMA = "ana.os21.web_recon_orchestrator.v1"
ORCHESTRATOR_NAME = "web_recon_orchestrator_v1"
ORCHESTRATOR_VERSION = "1.0"
CAPSULE_HINT_SCHEMA = "ana.os21.recon_capsule.v1"


def _json_key(value: Any) -> str:
    return repr(value)


def _unique_items(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    unique: list[Any] = []
    for item in items:
        key = _json_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


class WebReconOrchestrator:
    """Build a deterministic, metadata-only recon pipeline."""

    def __init__(self, agent: BrowserReconAgent | None = None) -> None:
        self.agent = agent or BrowserReconAgent()
        self._last_pipeline: dict[str, Any] | None = None

    def _merge_agent_plan(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        active_names = {
            str(phase.get("name", ""))
            for phase in (plan.get("active_phases") or [])
            if isinstance(phase, dict)
        }

        merged: list[dict[str, Any]] = [
            {
                "index": 0,
                "name": "orchestrator_scope",
                "purpose": "Normalize the URL, mode, and recon boundary before agent phases.",
                "phase_kind": "orchestrator",
                "source": ORCHESTRATOR_NAME,
                "tools": [],
                "operations": [],
                "risk": "low",
                "requires_confirmation": False,
                "outputs": ["scope", "policy", "capsule_seed"],
            }
        ]

        for index, phase in enumerate(plan.get("selected_phases") or [], start=1):
            if not isinstance(phase, dict):
                continue
            phase_name = str(phase.get("name", f"phase_{index}"))
            merged.append(
                {
                    "index": index,
                    "name": phase_name,
                    "purpose": str(phase.get("purpose", "")),
                    "phase_kind": "active" if phase_name in active_names else "passive",
                    "source": "browser_recon_agent",
                    "tools": list(phase.get("tools") or []),
                    "operations": list(phase.get("operations") or []),
                    "risk": str(phase.get("risk", "low")),
                    "requires_confirmation": bool(phase.get("requires_confirmation", False)),
                    "outputs": list(phase.get("outputs") or []),
                }
            )

        merged.append(
            {
                "index": len(merged),
                "name": "capsule_handoff",
                "purpose": "Prepare the recon metadata for future capsule storage and graph build steps.",
                "phase_kind": "handoff",
                "source": ORCHESTRATOR_NAME,
                "tools": [],
                "operations": [],
                "risk": "low",
                "requires_confirmation": False,
                "outputs": ["capsule_hints", "graph_hints"],
            }
        )
        return merged

    def _merge_graph_hints(self, plan: dict[str, Any], url: str, mode: str) -> dict[str, Any]:
        agent_hints = plan.get("reasoning_graph_hints") or {}
        nodes = list(agent_hints.get("nodes") or [])
        edges = list(agent_hints.get("edges") or [])

        orchestrator_node = f"orchestrator:{ORCHESTRATOR_NAME}"
        capsule_node = "capsule:recon_seed"
        url_node = f"context:url:{url}"
        mode_node = f"context:mode:{mode}"

        nodes.extend([orchestrator_node, capsule_node, url_node, mode_node])
        edges.extend(
            [
                {"source": orchestrator_node, "target": f"agent:{plan.get('agent_name', 'browser_recon_agent_v1')}", "relation": "delegates"},
                {"source": f"agent:{plan.get('agent_name', 'browser_recon_agent_v1')}", "target": capsule_node, "relation": "prepares"},
                {"source": orchestrator_node, "target": url_node, "relation": "scopes"},
            ]
        )

        return {
            "nodes": _unique_items(nodes),
            "edges": _unique_items(edges),
        }

    def _build_summary(self, pipeline: dict[str, Any]) -> dict[str, Any]:
        phases = list(pipeline.get("phases") or [])
        passive_count = sum(1 for phase in phases if isinstance(phase, dict) and phase.get("phase_kind") == "passive")
        active_count = sum(1 for phase in phases if isinstance(phase, dict) and phase.get("phase_kind") == "active")
        confirm_count = sum(1 for phase in phases if isinstance(phase, dict) and phase.get("requires_confirmation"))
        graph_hints = pipeline.get("reasoning_graph_hints") or {}
        capability_contracts = pipeline.get("capability_contracts") or {}
        return {
            "schema": ORCHESTRATOR_SCHEMA,
            "orchestrator_name": ORCHESTRATOR_NAME,
            "url": pipeline.get("url", ""),
            "mode": pipeline.get("mode", "passive"),
            "phase_count": len(phases),
            "passive_phase_count": passive_count,
            "active_phase_count": active_count,
            "confirm_required_phase_count": confirm_count,
            "capability_contract_count": len(capability_contracts),
            "reasoning_node_count": len(graph_hints.get("nodes") or []),
            "reasoning_edge_count": len(graph_hints.get("edges") or []),
        }

    def build_pipeline(self, url: str, mode: str = "passive") -> dict[str, Any]:
        normalized_url = (url or "").strip() or "unspecified-url"
        normalized_mode = (mode or "passive").strip().lower()
        if normalized_mode not in {"passive", "active"}:
            normalized_mode = "passive"

        agent_plan = self.agent.build_plan(target=normalized_url, mode=normalized_mode)
        pipeline = {
            "schema": ORCHESTRATOR_SCHEMA,
            "orchestrator_name": ORCHESTRATOR_NAME,
            "version": ORCHESTRATOR_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "local_only": True,
            "baseline_compatible": True,
            "url": normalized_url,
            "mode": normalized_mode,
            "agent_plan": agent_plan,
            "phases": self._merge_agent_plan(agent_plan),
            "capability_contracts": dict(agent_plan.get("capability_contracts") or {}),
            "reasoning_graph_hints": self._merge_graph_hints(agent_plan, normalized_url, normalized_mode),
            "capsule_hints": {
                "schema": CAPSULE_HINT_SCHEMA,
                "capsule_kind": "recon",
                "artifact_groups": ["passive", "active", "pipeline", "graph"],
                "version": "1.0",
                "lineage_seed": [ORCHESTRATOR_NAME, agent_plan.get("agent_name", "browser_recon_agent_v1")],
            },
        }
        pipeline["summary"] = self._build_summary(pipeline)
        self._last_pipeline = pipeline
        return pipeline

    def summarize_pipeline(self) -> dict[str, Any]:
        pipeline = self._last_pipeline or self.build_pipeline("", mode="passive")
        return dict(pipeline.get("summary") or self._build_summary(pipeline))

