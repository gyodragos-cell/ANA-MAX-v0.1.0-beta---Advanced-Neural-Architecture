"""
OS-21 browser pack v1.

This module is metadata only. It describes browser-related tool contracts
without changing the existing OS-20.1 runtime behavior.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACK_SCHEMA = "ana.os21.browser_pack.v1"
PACK_NAME = "browser_pack_v1"
PACK_VERSION = "1.0"

BROWSER_CONTROL_OPERATIONS = (
    "open",
    "inspect",
    "navigate",
    "click",
    "type",
    "press",
    "read",
    "screenshot",
    "screenshot_base64",
    "debug_feedback",
    "close",
    "status",
    "evaluate",
    "evaluate_on_selector",
    "scroll",
    "hover",
    "select_option",
    "upload_file",
    "get_attribute",
    "wait_for_selector",
    "wait_for_url",
    "new_tab",
    "switch_tab",
    "close_tab",
    "list_tabs",
    "intercept_network",
    "stop_intercept",
    "get_network_log",
    "get_all_links",
    "get_page_info",
    "dom_refs",
    "page_snapshot",
)

WEB_SCRAPER_OPERATIONS = (
    "fetch",
    "parse",
    "extract_links",
    "extract_text",
    "extract_images",
    "scrape_multiple",
    "download",
    "extract_metadata",
    "extract_forms",
)

BROWSER_CONTROL_READ_ONLY = (
    "status",
    "inspect",
    "dom_refs",
    "page_snapshot",
    "read",
    "screenshot",
    "screenshot_base64",
    "get_page_info",
    "get_all_links",
    "list_tabs",
    "debug_feedback",
    "get_network_log",
)

BROWSER_CONTROL_STATEFUL = (
    "open",
    "navigate",
    "scroll",
    "hover",
    "select_option",
    "get_attribute",
    "wait_for_selector",
    "wait_for_url",
    "new_tab",
    "switch_tab",
)

BROWSER_CONTROL_CONFIRM_REQUIRED = (
    "click",
    "type",
    "press",
    "evaluate",
    "evaluate_on_selector",
    "upload_file",
    "intercept_network",
    "stop_intercept",
    "close",
    "close_tab",
)

WEB_SCRAPER_READ_ONLY = (
    "parse",
    "extract_links",
    "extract_text",
    "extract_images",
    "extract_metadata",
    "extract_forms",
)

WEB_SCRAPER_NETWORK = (
    "fetch",
    "scrape_multiple",
    "download",
)


@dataclass(frozen=True)
class ToolContract:
    name: str
    category: str
    load_policy: str
    operations: tuple[str, ...]
    read_only_operations: tuple[str, ...] = field(default_factory=tuple)
    stateful_operations: tuple[str, ...] = field(default_factory=tuple)
    confirm_required_operations: tuple[str, ...] = field(default_factory=tuple)
    network_operations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operations"] = list(self.operations)
        payload["read_only_operations"] = list(self.read_only_operations)
        payload["stateful_operations"] = list(self.stateful_operations)
        payload["confirm_required_operations"] = list(self.confirm_required_operations)
        payload["network_operations"] = list(self.network_operations)
        return payload


TOOL_CONTRACTS = (
    ToolContract(
        name="browser_control",
        category="browser",
        load_policy="hybrid_optional",
        operations=BROWSER_CONTROL_OPERATIONS,
        read_only_operations=BROWSER_CONTROL_READ_ONLY,
        stateful_operations=BROWSER_CONTROL_STATEFUL,
        confirm_required_operations=BROWSER_CONTROL_CONFIRM_REQUIRED,
        network_operations=("open", "navigate", "intercept_network", "get_network_log"),
    ),
    ToolContract(
        name="web_scraper",
        category="web",
        load_policy="default",
        operations=WEB_SCRAPER_OPERATIONS,
        read_only_operations=WEB_SCRAPER_READ_ONLY,
        stateful_operations=(),
        confirm_required_operations=(),
        network_operations=WEB_SCRAPER_NETWORK,
    ),
)


def _tool_contract_map() -> dict[str, ToolContract]:
    return {contract.name: contract for contract in TOOL_CONTRACTS}


def build_browser_pack_manifest() -> dict[str, Any]:
    tool_contracts = [contract.to_dict() for contract in TOOL_CONTRACTS]
    safe_operations = list(BROWSER_CONTROL_READ_ONLY)
    confirm_operations = list(BROWSER_CONTROL_CONFIRM_REQUIRED)
    manifest = {
        "schema": PACK_SCHEMA,
        "pack_name": PACK_NAME,
        "version": PACK_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_only": True,
        "baseline_compatible": True,
        "pillars": [
            "tools",
            "virtualization",
            "reasoning_graph",
        ],
        "contracts": tool_contracts,
        "summary": {
            "tool_count": len(tool_contracts),
            "browser_operation_count": len(BROWSER_CONTROL_OPERATIONS),
            "web_operation_count": len(WEB_SCRAPER_OPERATIONS),
            "safe_operation_count": len(safe_operations),
            "confirm_operation_count": len(confirm_operations),
        },
        "operation_policy": {
            "browser_control": {
                "read_only_operations": safe_operations,
                "confirm_required_operations": confirm_operations,
            },
            "web_scraper": {
                "read_only_operations": list(WEB_SCRAPER_READ_ONLY),
                "network_operations": list(WEB_SCRAPER_NETWORK),
            },
        },
    }
    return manifest


def validate_browser_pack() -> dict[str, Any]:
    issues: list[str] = []
    checks: dict[str, Any] = {}

    contracts = _tool_contract_map()
    expected_names = {"browser_control", "web_scraper"}
    missing = sorted(expected_names - set(contracts))
    if missing:
        issues.append(f"missing_contracts:{','.join(missing)}")

    for contract in contracts.values():
        ops = list(contract.operations)
        if len(ops) != len(set(ops)):
            issues.append(f"duplicate_operations:{contract.name}")
        if not set(contract.read_only_operations).issubset(contract.operations):
            issues.append(f"read_only_not_subset:{contract.name}")
        if not set(contract.confirm_required_operations).issubset(contract.operations):
            issues.append(f"confirm_not_subset:{contract.name}")
        if set(contract.read_only_operations) & set(contract.confirm_required_operations):
            issues.append(f"read_only_overlap_confirm:{contract.name}")

    checks["browser_control_operations"] = list(BROWSER_CONTROL_OPERATIONS)
    checks["web_scraper_operations"] = list(WEB_SCRAPER_OPERATIONS)
    checks["confirm_required_operations"] = list(BROWSER_CONTROL_CONFIRM_REQUIRED)

    try:
        from tools.browser_control import BrowserControlTool

        browser_ops = tuple(BrowserControlTool().get_definition().parameters[0].choices or [])
        checks["browser_control_definition"] = list(browser_ops)
        if browser_ops and set(browser_ops) != set(BROWSER_CONTROL_OPERATIONS):
            issues.append("browser_control_definition_mismatch")
    except Exception as exc:
        issues.append(f"browser_control_import_failed:{exc}")

    try:
        from tools.web_scraper import WebScraperTool

        scraper_ops = tuple(WebScraperTool().get_definition().parameters[0].choices or [])
        checks["web_scraper_definition"] = list(scraper_ops)
        if scraper_ops and set(scraper_ops) != set(WEB_SCRAPER_OPERATIONS):
            issues.append("web_scraper_definition_mismatch")
    except Exception as exc:
        issues.append(f"web_scraper_import_failed:{exc}")

    return {
        "schema": PACK_SCHEMA,
        "pack_name": PACK_NAME,
        "success": not issues,
        "issues": issues,
        "checks": checks,
        "manifest": build_browser_pack_manifest(),
    }


def summarize_browser_pack() -> dict[str, Any]:
    manifest = build_browser_pack_manifest()
    return {
        "schema": PACK_SCHEMA,
        "pack_name": PACK_NAME,
        "version": PACK_VERSION,
        "tool_count": manifest["summary"]["tool_count"],
        "safe_operation_count": manifest["summary"]["safe_operation_count"],
        "confirm_operation_count": manifest["summary"]["confirm_operation_count"],
    }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "manifest"))
    if action == "manifest":
        return {"success": True, "result": build_browser_pack_manifest()}
    if action == "validate":
        result = validate_browser_pack()
        return {"success": result["success"], "result": result}
    if action == "summary":
        return {"success": True, "result": summarize_browser_pack()}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the OS-21 browser pack metadata.")
    parser.add_argument("--manifest", action="store_true", help="Print the browser pack manifest")
    parser.add_argument("--validate", action="store_true", help="Validate browser and scraper contracts")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary")
    args = parser.parse_args(argv)

    action = "manifest"
    if args.validate:
        action = "validate"
    elif args.summary:
        action = "summary"

    output = run({"action": action})
    print(json.dumps(output, indent=2, ensure_ascii=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
