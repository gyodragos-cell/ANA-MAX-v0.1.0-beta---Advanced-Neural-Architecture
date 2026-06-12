"""
OS-21 browser recon agent v1.

This slice is metadata-only. It plans passive and active recon work without
executing browser automation, so OS-20.1 stays stable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.tools import browser_pack

RECON_SCHEMA = "ana.os21.browser_recon_agent.v1"
AGENT_NAME = "browser_recon_agent_v1"
AGENT_ROLE = "browser_recon"
DEFAULT_MODE = "passive"


@dataclass(frozen=True)
class ReconPhase:
    name: str
    purpose: str
    tools: tuple[str, ...]
    operations: tuple[str, ...]
    risk: str = "low"
    requires_confirmation: bool = False
    outputs: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "tools": list(self.tools),
            "operations": list(self.operations),
            "risk": self.risk,
            "requires_confirmation": self.requires_confirmation,
            "outputs": list(self.outputs),
        }


def _phase(
    name: str,
    purpose: str,
    tools: tuple[str, ...],
    operations: tuple[str, ...],
    *,
    risk: str = "low",
    requires_confirmation: bool = False,
    outputs: tuple[str, ...] = (),
) -> ReconPhase:
    return ReconPhase(
        name=name,
        purpose=purpose,
        tools=tools,
        operations=operations,
        risk=risk,
        requires_confirmation=requires_confirmation,
        outputs=outputs,
    )


def _passive_phases() -> list[ReconPhase]:
    return [
        _phase(
            "scope_target",
            "Normalize the target, scope, and constraints before any recon planning.",
            (),
            (),
            outputs=("target_scope", "constraints"),
        ),
        _phase(
            "passive_scrape",
            "Collect static page evidence without interactive actions.",
            ("web_scraper",),
            ("fetch", "parse", "extract_links", "extract_text", "extract_metadata"),
            outputs=("static_html", "link_inventory", "text_preview"),
        ),
        _phase(
            "dom_snapshot",
            "Describe the visible DOM and page state through read-only browser inspection.",
            ("browser_control",),
            ("status", "inspect", "dom_refs", "page_snapshot", "read", "screenshot", "get_page_info", "get_all_links"),
            outputs=("dom_refs", "page_snapshot", "page_state"),
        ),
        _phase(
            "headers_tls_review",
            "Review headers and transport hints from passive fetch evidence.",
            ("web_scraper",),
            ("fetch", "extract_metadata"),
            outputs=("headers", "tls_hints"),
        ),
        _phase(
            "forms_inventory",
            "Inventory forms and inputs from the page without submitting anything.",
            ("web_scraper", "browser_control"),
            ("extract_forms", "dom_refs", "page_snapshot"),
            outputs=("forms", "input_inventory"),
        ),
        _phase(
            "js_endpoint_mapping",
            "Map JavaScript-linked endpoints and app surfaces from observed evidence.",
            ("browser_control", "web_scraper"),
            ("inspect", "page_snapshot", "extract_links", "extract_metadata"),
            outputs=("js_endpoints", "client_routes"),
        ),
        _phase(
            "risk_classification",
            "Classify the recon surface and separate safe read-only work from active follow-up.",
            (),
            (),
            outputs=("risk_summary", "recommended_followup"),
        ),
    ]


def _active_phases() -> list[ReconPhase]:
    return [
        _phase(
            "interactive_probe",
            "Plan optional interactive checks that require explicit confirmation before execution.",
            ("browser_control",),
            ("click", "type", "press", "evaluate", "evaluate_on_selector", "upload_file"),
            risk="medium",
            requires_confirmation=True,
            outputs=("interaction_notes", "probe_candidates"),
        ),
        _phase(
            "network_intercept_review",
            "Plan optional network interception follow-up for advanced recon review.",
            ("browser_control",),
            ("intercept_network", "stop_intercept", "get_network_log"),
            risk="medium",
            requires_confirmation=True,
            outputs=("network_log", "intercept_notes"),
        ),
    ]


def _selected_phases(mode: str) -> list[ReconPhase]:
    selected = list(_passive_phases())
    if mode == "active":
        selected.extend(_active_phases())
    return selected


def build_browser_recon_plan(target: str = "", mode: str = DEFAULT_MODE) -> dict[str, Any]:
    normalized_mode = (mode or DEFAULT_MODE).strip().lower()
    if normalized_mode not in {"passive", "active"}:
        normalized_mode = DEFAULT_MODE

    normalized_target = target.strip() or "unspecified-target"
    pack_manifest = browser_pack.build_browser_pack_manifest()
    selected_phases = _selected_phases(normalized_mode)

    plan = {
        "schema": RECON_SCHEMA,
        "agent_name": AGENT_NAME,
        "agent_role": AGENT_ROLE,
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_only": True,
        "baseline_compatible": True,
        "target": normalized_target,
        "mode": normalized_mode,
        "browser_pack": browser_pack.summarize_browser_pack(),
        "operation_policy": pack_manifest["operation_policy"],
        "required_tools": [
            {
                "name": "web_scraper",
                "purpose": "passive fetch and HTML parsing",
                "load_policy": "default",
            },
            {
                "name": "browser_control",
                "purpose": "read-only browser inspection and optional active follow-up",
                "load_policy": "hybrid_optional",
            },
        ],
        "capability_contracts": {
            "browser_control": {
                "read_only_operations": list(pack_manifest["operation_policy"]["browser_control"]["read_only_operations"]),
                "confirm_required_operations": list(pack_manifest["operation_policy"]["browser_control"]["confirm_required_operations"]),
            },
            "web_scraper": {
                "read_only_operations": list(pack_manifest["operation_policy"]["web_scraper"]["read_only_operations"]),
                "network_operations": list(pack_manifest["operation_policy"]["web_scraper"]["network_operations"]),
            },
        },
        "passive_phases": [phase.to_dict() for phase in _passive_phases()],
        "active_phases": [phase.to_dict() for phase in _active_phases()],
        "selected_phases": [phase.to_dict() for phase in selected_phases],
        "reasoning_graph_hints": {
            "nodes": [
                f"agent:{AGENT_NAME}",
                "tool:web_scraper",
                "tool:browser_control",
                f"context:target:{normalized_target}",
                f"context:mode:{normalized_mode}",
                "memory:browser_pack_v1",
            ],
            "edges": [
                {"source": f"agent:{AGENT_NAME}", "target": "tool:web_scraper", "relation": "uses"},
                {"source": f"agent:{AGENT_NAME}", "target": "tool:browser_control", "relation": "uses"},
                {"source": f"agent:{AGENT_NAME}", "target": "memory:browser_pack_v1", "relation": "reads"},
                {"source": f"agent:{AGENT_NAME}", "target": f"context:target:{normalized_target}", "relation": "plans_for"},
            ],
        },
        "handoff": {
            "next_agent_candidates": [
                "web_recon_orchestrator",
                "capsule_sync_agent",
            ],
            "notes": "Planning only; no browser execution is performed by this module.",
        },
    }
    return plan


def validate_browser_recon_plan(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []

    if plan.get("schema") != RECON_SCHEMA:
        issues.append("schema_mismatch")
    if plan.get("agent_name") != AGENT_NAME:
        issues.append("agent_name_mismatch")
    if not plan.get("target"):
        issues.append("missing_target")

    passive_phases = plan.get("passive_phases") or []
    selected_phases = plan.get("selected_phases") or []
    if not passive_phases:
        issues.append("missing_passive_phases")
    if not selected_phases:
        issues.append("missing_selected_phases")

    selected_names = [phase.get("name", "") for phase in selected_phases if isinstance(phase, dict)]
    if "scope_target" not in selected_names:
        issues.append("missing_scope_phase")
    if "passive_scrape" not in selected_names:
        issues.append("missing_passive_scrape_phase")
    if plan.get("mode") == "active" and "interactive_probe" not in selected_names:
        issues.append("missing_active_probe_phase")

    contract = plan.get("capability_contracts", {})
    browser_control = contract.get("browser_control", {})
    read_only = set(browser_control.get("read_only_operations", []))
    confirm_required = set(browser_control.get("confirm_required_operations", []))
    if not read_only:
        issues.append("empty_read_only_policy")
    if not confirm_required:
        issues.append("empty_confirm_policy")
    if not read_only.isdisjoint(confirm_required):
        issues.append("policy_overlap")

    return {
        "schema": RECON_SCHEMA,
        "agent_name": AGENT_NAME,
        "success": not issues,
        "issues": issues,
        "selected_phase_count": len(selected_phases),
        "passive_phase_count": len(passive_phases),
    }


def summarize_browser_recon_plan(plan: dict[str, Any]) -> dict[str, Any]:
    selected_phases = plan.get("selected_phases") or []
    return {
        "schema": RECON_SCHEMA,
        "agent_name": AGENT_NAME,
        "target": plan.get("target", ""),
        "mode": plan.get("mode", DEFAULT_MODE),
        "phase_count": len(selected_phases),
        "tool_count": len(plan.get("required_tools") or []),
    }


class BrowserReconAgent:
    """Metadata-only recon planner for browser and web surfaces."""

    def __init__(self, default_mode: str = DEFAULT_MODE) -> None:
        self.default_mode = default_mode

    def build_plan(self, target: str = "", mode: str | None = None) -> dict[str, Any]:
        return build_browser_recon_plan(target=target, mode=mode or self.default_mode)

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        return validate_browser_recon_plan(plan)

    def summarize(self, plan: dict[str, Any]) -> dict[str, Any]:
        return summarize_browser_recon_plan(plan)

    def run_cycle(self, target: str = "", mode: str | None = None) -> dict[str, Any]:
        plan = self.build_plan(target=target, mode=mode)
        validation = self.validate(plan)
        return {
            "schema": RECON_SCHEMA,
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
    agent = BrowserReconAgent(default_mode=mode)

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
    parser = argparse.ArgumentParser(description="Build a metadata-only browser recon plan.")
    parser.add_argument("--target", default="", help="Target URL or asset to plan against")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["passive", "active"], help="Recon planning mode")
    parser.add_argument("--plan", action="store_true", help="Print the recon plan")
    parser.add_argument("--validate", action="store_true", help="Validate the recon plan")
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
    print(json.dumps(output, indent=2, ensure_ascii=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
