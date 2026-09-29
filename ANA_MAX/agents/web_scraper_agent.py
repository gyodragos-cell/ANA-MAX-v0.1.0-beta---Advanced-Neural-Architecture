"""OS-21 web scraper agent v1.

This module is metadata-only. It plans web scraping work without executing
network calls, browser automation, or file writes.
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


SCRAPER_SCHEMA = "ana.os21.web_scraper_agent.v1"
AGENT_NAME = "web_scraper_agent_v1"
AGENT_ROLE = "web_scraper"
DEFAULT_MODE = "passive"


@dataclass(frozen=True)
class ScrapePhase:
    name: str
    purpose: str
    operations: tuple[str, ...]
    outputs: tuple[str, ...]
    risk: str = "low"
    requires_operator_review: bool = False
    metadata_only: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "tool": "web_scraper",
            "operations": list(self.operations),
            "outputs": list(self.outputs),
            "risk": self.risk,
            "requires_operator_review": self.requires_operator_review,
            "metadata_only": self.metadata_only,
            "notes": list(self.notes),
        }


def _phase(
    name: str,
    purpose: str,
    operations: tuple[str, ...],
    outputs: tuple[str, ...],
    *,
    risk: str = "low",
    requires_operator_review: bool = False,
    notes: tuple[str, ...] = (),
) -> ScrapePhase:
    return ScrapePhase(
        name=name,
        purpose=purpose,
        operations=operations,
        outputs=outputs,
        risk=risk,
        requires_operator_review=requires_operator_review,
        notes=notes,
    )


def _normalize_mode(mode: str | None) -> str:
    normalized = str(mode or DEFAULT_MODE).strip().lower()
    if normalized not in {"passive", "active"}:
        return DEFAULT_MODE
    return normalized


def _normalize_targets(targets: Any) -> list[str]:
    if isinstance(targets, str):
        raw_items = [targets]
    elif isinstance(targets, (list, tuple, set)):
        raw_items = [str(item) for item in targets]
    elif targets is None:
        raw_items = []
    else:
        raw_items = [str(targets)]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        target = str(item or "").strip()
        if not target or target in seen:
            continue
        seen.add(target)
        normalized.append(target)
    return normalized or ["unspecified-target"]


def _passive_phases() -> list[ScrapePhase]:
    return [
        _phase(
            "scope_targets",
            "Normalize target URLs, boundaries, and scraping constraints.",
            (),
            ("target_inventory", "scope_constraints"),
        ),
        _phase(
            "fetch_metadata_plan",
            "Plan safe fetch metadata collection without executing requests.",
            ("fetch", "extract_metadata"),
            ("headers", "status_hint", "content_type_hint"),
        ),
        _phase(
            "parse_html_plan",
            "Plan HTML parsing and selector inventory from provided or future HTML.",
            ("parse",),
            ("title", "text_preview", "selector_inventory"),
        ),
        _phase(
            "extract_links_plan",
            "Plan link extraction and URL normalization.",
            ("extract_links",),
            ("link_inventory", "internal_links", "external_links"),
        ),
        _phase(
            "extract_text_plan",
            "Plan plain text extraction for later capsule storage.",
            ("extract_text",),
            ("text_preview", "keyword_candidates"),
        ),
        _phase(
            "extract_assets_plan",
            "Plan image and asset metadata extraction without downloads.",
            ("extract_images",),
            ("image_inventory", "asset_refs"),
        ),
        _phase(
            "extract_forms_plan",
            "Plan form and input inventory without submitting data.",
            ("extract_forms",),
            ("forms", "input_inventory"),
        ),
        _phase(
            "artifact_packaging",
            "Describe how scrape metadata will map into future knowledge capsules.",
            (),
            ("capsule_payload", "lineage_refs"),
        ),
    ]


def _active_phases() -> list[ScrapePhase]:
    return [
        _phase(
            "multi_page_expansion",
            "Plan bounded multi-page scraping follow-up without executing it.",
            ("scrape_multiple",),
            ("crawl_frontier", "page_queue"),
            risk="medium",
            requires_operator_review=True,
            notes=("requires explicit scope limit before execution",),
        ),
        _phase(
            "download_review",
            "Plan file download review as metadata only; no download is performed.",
            ("download",),
            ("download_candidates", "operator_review_notes"),
            risk="medium",
            requires_operator_review=True,
            notes=("requires explicit approval before any real download layer",),
        ),
    ]


def _selected_phases(mode: str) -> list[ScrapePhase]:
    phases = list(_passive_phases())
    if mode == "active":
        phases.extend(_active_phases())
    return phases


def build_web_scraper_plan(targets: Any = None, mode: str = DEFAULT_MODE) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    normalized_targets = _normalize_targets(targets)
    manifest = browser_pack.build_browser_pack_manifest()
    selected = _selected_phases(normalized_mode)

    return {
        "schema": SCRAPER_SCHEMA,
        "agent_name": AGENT_NAME,
        "agent_role": AGENT_ROLE,
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata_only": True,
        "local_only": True,
        "no_execution": True,
        "baseline_compatible": True,
        "mode": normalized_mode,
        "targets": normalized_targets,
        "required_tools": [
            {
                "name": "web_scraper",
                "purpose": "plan passive web scraping and parsing metadata",
                "load_policy": "default",
                "execution_allowed": False,
            }
        ],
        "capability_contracts": {
            "web_scraper": {
                "read_only_operations": list(manifest["operation_policy"]["web_scraper"]["read_only_operations"]),
                "network_operations": list(manifest["operation_policy"]["web_scraper"]["network_operations"]),
                "execution_allowed": False,
            }
        },
        "passive_phases": [phase.to_dict() for phase in _passive_phases()],
        "active_phases": [phase.to_dict() for phase in _active_phases()],
        "selected_phases": [phase.to_dict() for phase in selected],
        "capsule_hints": {
            "schema": "ana.os21.web_scrape_capsule_hint.v1",
            "capsule_type": "web_scrape_metadata",
            "target_count": len(normalized_targets),
            "artifact_keys": [
                "headers",
                "link_inventory",
                "text_preview",
                "forms",
                "asset_refs",
            ],
        },
        "reasoning_graph_hints": {
            "nodes": [
                f"agent:{AGENT_NAME}",
                "tool:web_scraper",
                "capsule_hint:web_scrape_metadata",
                f"context:mode:{normalized_mode}",
                *[f"context:target:{target}" for target in normalized_targets],
            ],
            "edges": [
                {"source": f"agent:{AGENT_NAME}", "target": "tool:web_scraper", "relation": "plans_with"},
                {"source": f"agent:{AGENT_NAME}", "target": "capsule_hint:web_scrape_metadata", "relation": "emits"},
                *[
                    {"source": f"agent:{AGENT_NAME}", "target": f"context:target:{target}", "relation": "plans_for"}
                    for target in normalized_targets
                ],
            ],
        },
    }


def validate_web_scraper_plan(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if plan.get("schema") != SCRAPER_SCHEMA:
        issues.append("schema_mismatch")
    if plan.get("agent_name") != AGENT_NAME:
        issues.append("agent_name_mismatch")
    if not plan.get("metadata_only"):
        issues.append("metadata_only_false")
    if not plan.get("no_execution"):
        issues.append("no_execution_false")
    if not plan.get("targets"):
        issues.append("missing_targets")
    if not plan.get("selected_phases"):
        issues.append("missing_selected_phases")

    phase_names = [phase.get("name", "") for phase in plan.get("selected_phases") or [] if isinstance(phase, dict)]
    if "scope_targets" not in phase_names:
        issues.append("missing_scope_targets")
    if "fetch_metadata_plan" not in phase_names:
        issues.append("missing_fetch_metadata_plan")
    if plan.get("mode") == "active" and "download_review" not in phase_names:
        issues.append("missing_download_review")

    return {
        "schema": SCRAPER_SCHEMA,
        "agent_name": AGENT_NAME,
        "success": not issues,
        "issues": issues,
        "target_count": len(plan.get("targets") or []),
        "selected_phase_count": len(plan.get("selected_phases") or []),
    }


def summarize_web_scraper_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCRAPER_SCHEMA,
        "agent_name": AGENT_NAME,
        "mode": plan.get("mode", DEFAULT_MODE),
        "metadata_only": bool(plan.get("metadata_only", False)),
        "target_count": len(plan.get("targets") or []),
        "phase_count": len(plan.get("selected_phases") or []),
        "tool_count": len(plan.get("required_tools") or []),
    }


class WebScraperAgent:
    """Metadata-only planner for web scraper tool usage."""

    def __init__(self, default_mode: str = DEFAULT_MODE) -> None:
        self.default_mode = _normalize_mode(default_mode)

    def build_plan(self, targets: Any = None, mode: str | None = None) -> dict[str, Any]:
        return build_web_scraper_plan(targets=targets, mode=mode or self.default_mode)

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        return validate_web_scraper_plan(plan)

    def summarize(self, plan: dict[str, Any]) -> dict[str, Any]:
        return summarize_web_scraper_plan(plan)

    def run_cycle(self, targets: Any = None, mode: str | None = None) -> dict[str, Any]:
        plan = self.build_plan(targets=targets, mode=mode)
        validation = self.validate(plan)
        return {
            "schema": SCRAPER_SCHEMA,
            "agent_name": AGENT_NAME,
            "plan": plan,
            "validation": validation,
            "summary": self.summarize(plan),
        }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "plan"))
    targets = args.get("targets", args.get("target", ""))
    mode = str(args.get("mode", DEFAULT_MODE) or DEFAULT_MODE)
    agent = WebScraperAgent(default_mode=mode)

    if action == "plan":
        plan = agent.build_plan(targets=targets, mode=mode)
        return {"success": True, "result": plan}
    if action == "validate":
        plan = agent.build_plan(targets=targets, mode=mode)
        result = agent.validate(plan)
        return {"success": result["success"], "result": result}
    if action == "summary":
        plan = agent.build_plan(targets=targets, mode=mode)
        return {"success": True, "result": agent.summarize(plan)}
    if action == "cycle":
        result = agent.run_cycle(targets=targets, mode=mode)
        return {"success": result["validation"]["success"], "result": result}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only web scraper agent plan.")
    parser.add_argument("--target", action="append", default=[], help="Target URL or asset to plan against")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["passive", "active"], help="Scrape planning mode")
    parser.add_argument("--plan", action="store_true", help="Print the scrape plan")
    parser.add_argument("--validate", action="store_true", help="Validate the scrape plan")
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

    output = run({"action": action, "targets": args.target, "mode": args.mode})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
