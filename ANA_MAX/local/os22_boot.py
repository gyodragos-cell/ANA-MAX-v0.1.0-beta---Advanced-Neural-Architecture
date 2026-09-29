"""OS-22 boot and health metadata for the local LLM core."""

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
from ANA_MAX.local.agent_foundation import get_agent_foundation_status
from ANA_MAX.local.agent_self_healing import get_self_healing_status
from ANA_MAX.local.local_llm_backend import LocalLLMBackend
from ANA_MAX.local.prompt_engine import compose_system_prompt, get_tool_specs
from ANA_MAX.local.prompt_profiles import available_prompt_profiles, get_system_prompt
from ANA_MAX.local.rag_bridge import get_rag_bridge
from ANA_MAX.tools.tool_manifest_loader import get_tool_manifest


BOOT_SCHEMA = "ana.os22.boot_sequence.v1"
DEFAULT_REPORT_PATH = ROOT / "ANA_MAX" / "memory" / "os22_boot_report.json"


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_ascii_text(item) for item in value]
    return []


def _health_score(*, backend_info: Mapping[str, Any], tool_count: int, rag_ready: bool, agent_ready: bool) -> int:
    score = 30
    if tool_count > 0:
        score += 30
    if rag_ready:
        score += 20
    if agent_ready:
        score += 10
    if bool(backend_info.get("available")):
        score += 10
    if bool(backend_info.get("loaded")):
        score += 5
    return min(score, 100)


class OS22BootSequence:
    """Build a deterministic OS-22 boot and health report."""

    def __init__(
        self,
        backend: LocalLLMBackend | None = None,
        agent: LocalBrainAgent | None = None,
        rag_bridge: Any | None = None,
        report_path: Path | str | None = None,
        boot_profile: str = "codex",
    ) -> None:
        self.backend = backend or LocalLLMBackend()
        self.rag_bridge = rag_bridge or get_rag_bridge()
        self.boot_profile = str(boot_profile or "codex").strip() or "codex"
        self.agent = agent or LocalBrainAgent(
            backend=self.backend,
            enable_inference=False,
            prompt_profile=self.boot_profile,
            rag_bridge=self.rag_bridge,
            use_rag=True,
            tool_aware=True,
        )
        self.report_path = Path(report_path) if report_path is not None else DEFAULT_REPORT_PATH
        self._last_report: dict[str, Any] | None = None

    def _profile_layer(self) -> dict[str, Any]:
        profiles = available_prompt_profiles()
        return {
            "schema": "ana.os22.profile_layer.v1",
            "available": True,
            "profile_count": len(profiles),
            "profiles": list(profiles),
            "default_profile": "default",
            "boot_profile": self.boot_profile,
            "selected_profile": self.boot_profile,
            "system_prompt_preview": _ascii_text(get_system_prompt(self.boot_profile))[:240],
        }

    def _prompt_engine_status(self) -> dict[str, Any]:
        tool_specs = get_tool_specs()
        prompt_preview = compose_system_prompt(get_system_prompt(self.boot_profile))
        return {
            "schema": "ana.os22.prompt_engine_status.v1",
            "available": True,
            "tool_call_instruction": "TOOL_CALL: <tool_name> <json_arguments>",
            "tool_spec_count": tool_specs.count("- "),
            "tool_specs_preview": _ascii_text(tool_specs)[:480],
            "prompt_preview": prompt_preview[:480],
        }

    def _rag_status(self) -> dict[str, Any]:
        try:
            status = dict(self.rag_bridge.get_status())
        except Exception as exc:
            return {
                "schema": "ana.local.rag_bridge.v1",
                "ready": False,
                "local_only": True,
                "error": _ascii_text(exc),
            }
        status.setdefault("schema", "ana.local.rag_bridge.v1")
        status["ready"] = bool(status.get("ready", False))
        status["local_only"] = True
        return status

    def _tool_bridge_status(self) -> dict[str, Any]:
        manifest = get_tool_manifest()
        tools = manifest.get("tools", [])
        tool_count = len(tools) if isinstance(tools, list) else 0
        return {
            "schema": "ana.os22.tool_bridge_status.v1",
            "available": True,
            "manifest": {
                "schema": _ascii_text(manifest.get("schema", "")),
                "description": _ascii_text(manifest.get("description", "")),
                "version": _ascii_text(manifest.get("version", "")),
                "tool_count": tool_count,
                "tool_names": _safe_list([tool.get("name", "") for tool in tools if isinstance(tool, Mapping)]),
            },
            "dispatcher": {
                "available": True,
                "tool_call_format": "TOOL_CALL: <tool_name> <json_arguments>",
                "telemetry": "append-only-jsonl",
                "local_only": True,
            },
        }

    def build_boot_report(self) -> dict[str, Any]:
        backend_info = self.backend.get_backend_info()
        rag_status = self._rag_status()
        tool_bridge = self._tool_bridge_status()
        prompt_engine = self._prompt_engine_status()
        agent_summary = self.agent.summarize_agent()
        foundation = get_agent_foundation_status()
        self_healing = get_self_healing_status()
        health_score = _health_score(
            backend_info=backend_info,
            tool_count=int(tool_bridge["manifest"]["tool_count"]),
            rag_ready=bool(rag_status.get("ready")),
            agent_ready=bool(agent_summary.get("backend_available", False)) or bool(agent_summary.get("tool_aware", False)),
        )
        overall_success = bool(
            prompt_engine.get("available")
            and tool_bridge.get("available")
            and rag_status.get("ready") is True
            and agent_summary.get("schema") == "ana.os21.local_brain_agent.v1"
            and backend_info.get("schema") == "ana.os21.local_llm_backend.v1"
        )
        status = "READY" if overall_success else "DEGRADED"
        report = {
            "schema": BOOT_SCHEMA,
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "overall_success": overall_success,
            "health_score": health_score,
            "profile_layer": self._profile_layer(),
            "prompt_engine": prompt_engine,
            "rag_bridge": rag_status,
            "tool_bridge": tool_bridge,
            "agent_foundation": foundation,
            "self_healing": self_healing,
            "backend": backend_info,
            "agent": agent_summary,
            "launch_profile": self.boot_profile,
            "next_step": "Run LocalLLMBackend.infer_with_rag() smoke checks with the manifest-backed tool bridge.",
        }
        self._last_report = report
        return report

    def validate_boot_report(self, report: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(report or self._last_report or self.build_boot_report())
        issues: list[str] = []
        if payload.get("schema") != BOOT_SCHEMA:
            issues.append("schema_mismatch")
        if payload.get("metadata_only") is not True:
            issues.append("metadata_only_false")
        if payload.get("local_only") is not True:
            issues.append("local_only_false")
        profile_layer = payload.get("profile_layer", {})
        selected_profile = profile_layer.get("selected_profile")
        boot_profile = profile_layer.get("boot_profile") or self.boot_profile
        available_profiles = set(profile_layer.get("profiles") or [])
        if selected_profile != boot_profile:
            issues.append("selected_profile_mismatch")
        if available_profiles and selected_profile not in available_profiles:
            issues.append("selected_profile_unavailable")
        if payload.get("prompt_engine", {}).get("available") is not True:
            issues.append("prompt_engine_unavailable")
        if payload.get("tool_bridge", {}).get("available") is not True:
            issues.append("tool_bridge_unavailable")
        if payload.get("rag_bridge", {}).get("ready") is not True:
            issues.append("rag_unavailable")
        if payload.get("agent", {}).get("schema") != "ana.os21.local_brain_agent.v1":
            issues.append("agent_schema_mismatch")
        if payload.get("agent_foundation", {}).get("ready") is not True:
            issues.append("agent_foundation_unavailable")
        if payload.get("self_healing", {}).get("ready") is not True:
            issues.append("self_healing_unavailable")
        return {
            "schema": BOOT_SCHEMA,
            "success": not issues,
            "issues": issues,
            "health_score": payload.get("health_score", 0),
            "status": payload.get("status", ""),
        }

    def write_report(self) -> dict[str, Any]:
        report = self.build_boot_report()
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return report

    def run(self) -> dict[str, Any]:
        return self.build_boot_report()

    def summarize_boot(self) -> dict[str, Any]:
        report = self._last_report or self.build_boot_report()
        return {
            "schema": BOOT_SCHEMA,
            "status": report.get("status", ""),
            "health_score": report.get("health_score", 0),
            "overall_success": report.get("overall_success", False),
            "selected_profile": report.get("profile_layer", {}).get("selected_profile", "codex"),
            "tool_count": report.get("tool_bridge", {}).get("manifest", {}).get("tool_count", 0),
            "rag_ready": report.get("rag_bridge", {}).get("ready", False),
            "foundation_ready": report.get("agent_foundation", {}).get("ready", False),
            "self_healing_ready": report.get("self_healing", {}).get("ready", False),
        }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = dict(args or {})
    action = str(args.get("action", "summary"))
    boot = OS22BootSequence(
        report_path=args.get("report_path"),
        boot_profile=str(args.get("profile") or "codex"),
    )

    if action == "write":
        report = boot.write_report()
        return {"success": report["overall_success"], "result": report}
    report = boot.build_boot_report()
    if action == "validate":
        validation = boot.validate_boot_report(report)
        return {"success": validation["success"], "result": validation}
    if action == "summary":
        return {"success": True, "result": boot.summarize_boot()}
    if action in {"report", "cycle"}:
        return {"success": report["overall_success"], "result": report}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the OS-22 local brain boot and health report.")
    parser.add_argument("--summary", action="store_true", help="Print compact boot summary")
    parser.add_argument("--validate", action="store_true", help="Validate the boot report")
    parser.add_argument("--write", action="store_true", help="Write the boot report to ANA_MAX/memory/")
    parser.add_argument("--cycle", action="store_true", help="Print the full boot report")
    parser.add_argument("--report-path", default="", help="Optional output path for --write")
    parser.add_argument("--profile", default="codex", help="Boot profile to validate or report")
    args = parser.parse_args(argv)

    action = "summary"
    if args.validate:
        action = "validate"
    elif args.write:
        action = "write"
    elif args.cycle:
        action = "cycle"
    elif args.summary:
        action = "summary"

    output = run({"action": action, "report_path": args.report_path or None, "profile": args.profile})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
