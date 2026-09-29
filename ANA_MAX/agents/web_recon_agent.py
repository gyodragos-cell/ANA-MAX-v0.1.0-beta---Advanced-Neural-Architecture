"""OS-21 web recon agent v1.

This module composes browser recon, scraper planning, and recon orchestration
metadata without executing browser actions, network requests, or file writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents.browser_recon_agent import BrowserReconAgent
from ANA_MAX.agents.web_scraper_agent import WebScraperAgent
from ANA_MAX.orchestrators.web_recon_orchestrator import WebReconOrchestrator


WEB_RECON_SCHEMA = "ana.os21.web_recon_agent.v1"
AGENT_NAME = "web_recon_agent_v1"
AGENT_ROLE = "web_recon"
DEFAULT_MODE = "passive"


def _normalize_mode(mode: str | None) -> str:
    normalized = str(mode or DEFAULT_MODE).strip().lower()
    if normalized not in {"passive", "active"}:
        return DEFAULT_MODE
    return normalized


def _normalize_target(target: str | None) -> str:
    return str(target or "").strip() or "unspecified-target"


def _unique_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        signature = (
            str(item.get("source", "")),
            str(item.get("target", "")),
            str(item.get("relation", "")),
        )
        if signature in seen:
            continue
        seen.add(signature)
        output.append(item)
    return output


class WebReconAgent:
    """Metadata-only coordinator for web recon planning."""

    def __init__(
        self,
        *,
        browser_agent: BrowserReconAgent | None = None,
        scraper_agent: WebScraperAgent | None = None,
        orchestrator: WebReconOrchestrator | None = None,
        default_mode: str = DEFAULT_MODE,
    ) -> None:
        self.default_mode = _normalize_mode(default_mode)
        self.browser_agent = browser_agent or BrowserReconAgent(default_mode=self.default_mode)
        self.scraper_agent = scraper_agent or WebScraperAgent(default_mode=self.default_mode)
        self.orchestrator = orchestrator or WebReconOrchestrator(self.browser_agent)

    def _reasoning_graph_hints(
        self,
        *,
        target: str,
        mode: str,
        browser_plan: dict[str, Any],
        scraper_plan: dict[str, Any],
        pipeline_plan: dict[str, Any],
    ) -> dict[str, Any]:
        nodes = [
            f"agent:{AGENT_NAME}",
            "agent:browser_recon_agent_v1",
            "agent:web_scraper_agent_v1",
            "orchestrator:web_recon_orchestrator_v1",
            "tool:web_scraper",
            "tool:browser_control",
            f"context:target:{target}",
            f"context:mode:{mode}",
            "capsule_hint:web_recon_metadata",
        ]
        for source in (browser_plan, scraper_plan, pipeline_plan):
            hints = source.get("reasoning_graph_hints") or {}
            nodes.extend(str(item) for item in hints.get("nodes") or [])

        edges = [
            {"source": f"agent:{AGENT_NAME}", "target": "agent:browser_recon_agent_v1", "relation": "coordinates"},
            {"source": f"agent:{AGENT_NAME}", "target": "agent:web_scraper_agent_v1", "relation": "coordinates"},
            {"source": f"agent:{AGENT_NAME}", "target": "orchestrator:web_recon_orchestrator_v1", "relation": "hands_off"},
            {"source": f"agent:{AGENT_NAME}", "target": "capsule_hint:web_recon_metadata", "relation": "emits"},
            {"source": f"agent:{AGENT_NAME}", "target": f"context:target:{target}", "relation": "plans_for"},
        ]
        for source in (browser_plan, scraper_plan, pipeline_plan):
            hints = source.get("reasoning_graph_hints") or {}
            edges.extend(dict(item) for item in hints.get("edges") or [] if isinstance(item, dict))

        return {
            "nodes": sorted(set(nodes)),
            "edges": _unique_dicts(edges),
        }

    def build_plan(self, target: str = "", mode: str | None = None) -> dict[str, Any]:
        normalized_target = _normalize_target(target)
        normalized_mode = _normalize_mode(mode or self.default_mode)
        browser_plan = self.browser_agent.build_plan(target=normalized_target, mode=normalized_mode)
        scraper_plan = self.scraper_agent.build_plan(targets=[normalized_target], mode=normalized_mode)
        pipeline_plan = self.orchestrator.build_pipeline(url=normalized_target, mode=normalized_mode)
        requires_confirmation = normalized_mode == "active"

        graph_hints = self._reasoning_graph_hints(
            target=normalized_target,
            mode=normalized_mode,
            browser_plan=browser_plan,
            scraper_plan=scraper_plan,
            pipeline_plan=pipeline_plan,
        )

        return {
            "schema": WEB_RECON_SCHEMA,
            "agent_name": AGENT_NAME,
            "agent_role": AGENT_ROLE,
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "no_execution": True,
            "baseline_compatible": True,
            "target": normalized_target,
            "mode": normalized_mode,
            "browser_plan": browser_plan,
            "scraper_plan": scraper_plan,
            "pipeline_plan": pipeline_plan,
            "risk_profile": {
                "mode": normalized_mode,
                "requires_confirmation": requires_confirmation,
                "execution_allowed": False,
                "notes": "Planning only. Active mode marks follow-up that requires explicit execution approval elsewhere.",
            },
            "capability_contracts": {
                "browser_recon": browser_plan.get("capability_contracts", {}),
                "web_scraper": scraper_plan.get("capability_contracts", {}),
                "web_recon_orchestrator": pipeline_plan.get("capability_contracts", {}),
            },
            "capsule_hints": {
                "schema": "ana.os21.web_recon_capsule_hint.v1",
                "capsule_type": "web_recon_metadata",
                "target": normalized_target,
                "subplans": ["browser_plan", "scraper_plan", "pipeline_plan"],
                "artifact_keys": [
                    "browser_recon",
                    "scrape_metadata",
                    "pipeline_phases",
                    "risk_profile",
                ],
            },
            "reasoning_graph_hints": graph_hints,
            "handoff": {
                "next_layers": ["capsule_store", "reasoning_graph", "distributed_pipeline"],
                "notes": "No execution is performed by this agent.",
            },
        }

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        issues: list[str] = []
        if plan.get("schema") != WEB_RECON_SCHEMA:
            issues.append("schema_mismatch")
        if plan.get("agent_name") != AGENT_NAME:
            issues.append("agent_name_mismatch")
        if not plan.get("metadata_only"):
            issues.append("metadata_only_false")
        if not plan.get("no_execution"):
            issues.append("no_execution_false")
        if not plan.get("target"):
            issues.append("missing_target")
        for key in ("browser_plan", "scraper_plan", "pipeline_plan"):
            if not isinstance(plan.get(key), dict):
                issues.append(f"missing_{key}")
        if not plan.get("reasoning_graph_hints", {}).get("nodes"):
            issues.append("missing_reasoning_graph_nodes")
        return {
            "schema": WEB_RECON_SCHEMA,
            "agent_name": AGENT_NAME,
            "success": not issues,
            "issues": issues,
            "subplan_count": len([key for key in ("browser_plan", "scraper_plan", "pipeline_plan") if isinstance(plan.get(key), dict)]),
        }

    def summarize(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": WEB_RECON_SCHEMA,
            "agent_name": AGENT_NAME,
            "target": plan.get("target", ""),
            "mode": plan.get("mode", DEFAULT_MODE),
            "metadata_only": bool(plan.get("metadata_only", False)),
            "subplan_count": len([key for key in ("browser_plan", "scraper_plan", "pipeline_plan") if isinstance(plan.get(key), dict)]),
            "graph_node_count": len(plan.get("reasoning_graph_hints", {}).get("nodes") or []),
            "requires_confirmation": bool(plan.get("risk_profile", {}).get("requires_confirmation", False)),
        }

    def run_cycle(self, target: str = "", mode: str | None = None) -> dict[str, Any]:
        plan = self.build_plan(target=target, mode=mode)
        validation = self.validate(plan)
        return {
            "schema": WEB_RECON_SCHEMA,
            "agent_name": AGENT_NAME,
            "plan": plan,
            "validation": validation,
            "summary": self.summarize(plan),
        }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "plan"))
    target = str(args.get("target", "") or "")
    mode = str(args.get("mode", DEFAULT_MODE) or DEFAULT_MODE)
    agent = WebReconAgent(default_mode=mode)

    if action == "plan":
        plan = agent.build_plan(target=target, mode=mode)
        return {"success": True, "result": plan}
    if action == "validate":
        plan = agent.build_plan(target=target, mode=mode)
        result = agent.validate(plan)
        return {"success": result["success"], "result": result}
    if action == "summary":
        plan = agent.build_plan(target=target, mode=mode)
        return {"success": True, "result": agent.summarize(plan)}
    if action == "cycle":
        result = agent.run_cycle(target=target, mode=mode)
        return {"success": result["validation"]["success"], "result": result}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only web recon agent plan.")
    parser.add_argument("--target", default="", help="Target URL or asset to plan against")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["passive", "active"], help="Recon planning mode")
    parser.add_argument("--plan", action="store_true", help="Print the web recon plan")
    parser.add_argument("--validate", action="store_true", help="Validate the web recon plan")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary")
    parser.add_argument("--cycle", action="store_true", help="Build, validate, and summarize in one pass")
    args = parser.parse_args(argv)

    action = "plan"
    if args.validate:
        action = "validate"
    elif args.summary:
        action = "summary"
    elif args.cycle:
        action = "cycle"

    output = run({"action": action, "target": args.target, "mode": args.mode})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
