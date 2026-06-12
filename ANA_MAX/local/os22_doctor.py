"""OS-22 launch readiness doctor."""

from __future__ import annotations

import argparse
import json
import platform
from typing import Any

from ANA_MAX.local.agent_foundation import get_agent_foundation_status
from ANA_MAX.local.agent_self_healing import (
    diagnose_rag_context,
    diagnose_tool_request,
    get_self_healing_status,
    preflight_diagnostics,
    resolve_rag_conflicts,
    stabilize_reasoning_text,
)
from ANA_MAX.local.os22_boot import OS22BootSequence
from ANA_MAX.tools.tool_manifest_loader import get_tool_manifest


DOCTOR_SCHEMA = "ana.os22.doctor.v1"


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _check(name: str, success: bool, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "success": bool(success),
        "detail": detail or {},
    }


def run_os22_doctor(profile: str = "os22_core") -> dict[str, Any]:
    """Run in-process launch readiness checks without loading the LLM model."""
    checks: list[dict[str, Any]] = []

    boot = OS22BootSequence(boot_profile=profile).run()
    boot_result = boot.get("result", boot) if isinstance(boot, dict) else {}
    checks.append(
        _check(
            "boot_sequence",
            bool((boot.get("success") or boot.get("overall_success")) and boot_result.get("status") == "READY" and not boot_result.get("issues")),
            {
                "status": _ascii_text(boot_result.get("status", "")),
                "issues": boot_result.get("issues", []),
            },
        )
    )

    foundation = get_agent_foundation_status()
    checks.append(_check("agent_foundation", bool(foundation.get("ready")), foundation))

    healing = get_self_healing_status()
    checks.append(_check("self_healing", bool(healing.get("ready")), healing))

    manifest = get_tool_manifest()
    tools = {tool.get("name") for tool in manifest.get("tools", []) if isinstance(tool, dict)}
    checks.append(
        _check(
            "tool_manifest_web_learning",
            {"web_scrape", "rag_store_text"} <= tools,
            {"tool_count": len(tools), "web_learning_tools": sorted(tools & {"web_scrape", "rag_store_text"})},
        )
    )

    desktop_tools = {"desktop_list_items", "desktop_inspect_folder"}
    desktop_list_diag = diagnose_tool_request("desktop_list_items", {})
    desktop_inspect_diag = diagnose_tool_request("desktop_inspect_folder", {"folder_name": "ana_dev"})
    checks.append(
        _check(
            "desktop_visibility_tools",
            desktop_tools <= tools and desktop_list_diag.get("success") and desktop_inspect_diag.get("success"),
            {
                "tool_count": len(tools),
                "desktop_tools": sorted(tools & desktop_tools),
                "desktop_list_issue": desktop_list_diag.get("issue_class", ""),
                "desktop_inspect_issue": desktop_inspect_diag.get("issue_class", ""),
            },
        )
    )

    content_tools = {"desktop_read_text_file", "desktop_write_text_file", "web_learn_url", "web_learn_course"}
    desktop_read_diag = diagnose_tool_request("desktop_read_text_file", {"file_name": "lesson.py"})
    desktop_write_diag = diagnose_tool_request("desktop_write_text_file", {"file_name": "php", "content": "notes"})
    web_learn_diag = diagnose_tool_request("web_learn_url", {"url": "https://example.test/course"})
    web_course_diag = diagnose_tool_request("web_learn_course", {"start_url": "https://example.test/course"})
    checks.append(
        _check(
            "content_learning_tools",
            content_tools <= tools
            and desktop_read_diag.get("success")
            and desktop_write_diag.get("success")
            and web_learn_diag.get("success")
            and web_course_diag.get("success"),
            {
                "tool_count": len(tools),
                "content_tools": sorted(tools & content_tools),
                "desktop_read_issue": desktop_read_diag.get("issue_class", ""),
                "desktop_write_issue": desktop_write_diag.get("issue_class", ""),
                "web_learn_issue": web_learn_diag.get("issue_class", ""),
                "web_course_issue": web_course_diag.get("issue_class", ""),
            },
        )
    )

    invalid_tool = diagnose_tool_request("missing_os22_tool", {})
    checks.append(
        _check(
            "tool_diagnostic_invalid_tool",
            invalid_tool.get("issue_class") == "tool_missing",
            {"issue_class": invalid_tool.get("issue_class", "")},
        )
    )

    missing_args = diagnose_tool_request("read_file", {})
    checks.append(
        _check(
            "tool_diagnostic_missing_args",
            missing_args.get("issue_class") == "tool_args_missing",
            {"issue_class": missing_args.get("issue_class", "")},
        )
    )

    rag_empty = diagnose_rag_context("os22 launch", [])
    checks.append(
        _check(
            "rag_empty_diagnostic",
            rag_empty.get("issue_class") == "rag_empty",
            {"issue_class": rag_empty.get("issue_class", "")},
        )
    )

    rag_conflict = resolve_rag_conflicts(
        [
            {"memory_id": "old", "content": "old launch info", "importance": 0.1, "updated_at": 1},
            {"memory_id": "new", "content": "new launch info", "importance": 0.9, "updated_at": 2},
        ]
    )
    checks.append(
        _check(
            "rag_conflict_diagnostic",
            bool(rag_conflict.get("conflict_detected") and rag_conflict.get("selected_content") == "new launch info"),
            {"selected_content": rag_conflict.get("selected_content", "")},
        )
    )

    stabilized = stabilize_reasoning_text(" ".join(f"word{i}" for i in range(120)), max_words=40)
    checks.append(
        _check(
            "reasoning_stabilizer",
            stabilized.get("issue_class") == "reasoning_too_long" and stabilized.get("stabilized_word_count", 999) <= 40,
            {"issue_class": stabilized.get("issue_class", ""), "stabilized_word_count": stabilized.get("stabilized_word_count", 0)},
        )
    )

    preflight = preflight_diagnostics(tool_name="read_file", args={}, rag_items=[], text="TOOL_CALL: current_time {}\nTOOL_CALL: system_info {}")
    checks.append(
        _check(
            "preflight_diagnostics",
            preflight.get("issue_count", 0) >= 3,
            {"issue_count": preflight.get("issue_count", 0), "success": preflight.get("success", True)},
        )
    )

    failed = [item["name"] for item in checks if not item.get("success")]
    return {
        "schema": DOCTOR_SCHEMA,
        "profile": _ascii_text(profile),
        "success": not failed,
        "status": "READY" if not failed else "WARN",
        "metadata_only": True,
        "local_only": True,
        "python": platform.python_version(),
        "check_count": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "next_step": "Launch OS-22 agent for human testing." if not failed else "Inspect failed_checks before launch.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run OS-22 launch readiness doctor.")
    parser.add_argument("--profile", default="os22_core")
    args = parser.parse_args(argv)
    report = run_os22_doctor(profile=args.profile)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
