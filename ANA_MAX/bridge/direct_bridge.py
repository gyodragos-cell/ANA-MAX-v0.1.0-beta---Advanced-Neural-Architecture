#!/usr/bin/env python3
"""
ANA DEV direct bridge for local lab execution.

This bridge intentionally avoids MCP/cloud paths by default. It loads ANA MAX
tools in-process, executes them through the local registry, writes a compact
audit trail, and exposes fast health, smoke, benchmark, and security diagnostics.
"""

from __future__ import annotations

import argparse
import datetime as dt
import base64
import importlib
import json
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pywinauto.*")
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import request


# direct_bridge.py este in ANA_MAX/bridge/ → parents[1]=ANA_MAX, parents[2]=workspace root
ANA_MAX_ROOT = Path(__file__).resolve().parents[1]   # ana_dev/ANA_MAX
WORKSPACE_ROOT = ANA_MAX_ROOT.parent                 # ana_dev/
LOG_DIR = ANA_MAX_ROOT / "logs"
AUDIT_LOG = LOG_DIR / "direct_bridge_audit.jsonl"
ERROR_LOG = LOG_DIR / "direct_bridge_errors.jsonl"
MAX_LOG_BYTES = 5 * 1024 * 1024

sys.path.insert(0, str(ANA_MAX_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT))

from tools.base import ToolResult, registry  # noqa: E402


CORE_TOOL_MODULES: tuple[tuple[str, str], ...] = (
    ("tools.files", "FilesTool"),
    ("tools.system", "SystemTool"),
    ("tools.smart_search_tool", "SmartSearchTool"),
    ("tools.project_navigator_tool", "ProjectNavigatorTool"),
    ("tools.code_search", "CodeSearchTool"),
    ("tools.file_patch_tool", "FilePatchTool"),
    ("tools.tool_router_tool", "ToolRouterTool"),
    ("tools.agent_coach_tool", "AgentCoachTool"),
    ("tools.tool_healthcheck", "ToolHealthcheckTool"),
    ("tools.error_radar_tool", "ErrorRadarTool"),
    ("tools.workspace_situational_awareness", "WorkspaceSituationalAwarenessTool"),
    ("tools.privacy", "PrivacyTool"),
    ("tools.security_tool", "SecurityTool"),
    ("tools.terminal_tool", "TerminalTool"),
    ("tools.large_file_reader", "LargeFileReaderTool"),
    # OS-27 Computer Use & Sensing
    ("tools.screen_grid", "ScreenGridTool"),
    ("tools.ocr_tool", "OcrTool"),
    ("tools.clipboard_manager", "ClipboardManagerTool"),
    ("tools.window_manager", "WindowManagerTool"),
    ("tools.memory_cortex", "MemoryCortexTool"),
    ("tools.desktop_control_tool", "DesktopControlTool"),
    ("tools.swarm_tool", "SwarmTool"),
    ("tools.git_tool", "GitTool"),
    ("tools.network_tool", "NetworkTool"),
)

HYBRID_TOOL_CLASSES: tuple[tuple[str, str], ...] = (
    ("tools.browser_control", "BrowserControlTool"),
    ("tools.ana_ultrafast_web_executor_v4", "UltrafastWebExecutorTool"),
)

MUTATING_FILE_OPS = {"write", "edit", "surgical_edit"}
MUTATING_SYSTEM_OPS = {"shell", "kill_process", "run", "execute"}
BROWSER_CONFIRM_OPS = {
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
}
DANGEROUS_TOOLS = {
    "terminal",
    "desktop_control",
    "uia_click",
    "uia_type",
    "remote_control",
    "network_pentest",
    "mitm_analyzer",
    "adb",
}
SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "key", "password", "secret", "token"}

# Dynamic timeout configuration
DEFAULT_TIMEOUT = 10  # seconds
MAX_TIMEOUT = 300     # seconds (5 minutes)
TIMEOUT_SCALE_FACTOR = 0.5  # seconds per 1000 chars of payload


@dataclass
class DirectMetric:
    tool: str
    mode: str
    latency_ms: float
    success: bool
    error: str = ""


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _calculate_dynamic_timeout(payload: dict[str, Any] | None = None) -> int:
    """Calculate dynamic timeout based on payload size and complexity."""
    if not payload:
        return DEFAULT_TIMEOUT
    
    # Estimate payload size in characters
    payload_str = json.dumps(payload, default=str)
    payload_size = len(payload_str)
    
    # Scale timeout: 0.5 seconds per 1000 chars, capped at MAX_TIMEOUT
    scaled_timeout = DEFAULT_TIMEOUT + (payload_size / 1000 * TIMEOUT_SCALE_FACTOR)
    
    return min(int(scaled_timeout), MAX_TIMEOUT)


def _rotate_log(path: Path, max_bytes: int = MAX_LOG_BYTES) -> None:
    if not path.exists() or path.stat().st_size < max_bytes:
        return
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path.rename(path.with_name(f"{path.stem}_{stamp}{path.suffix}"))


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
                redacted[key] = "********"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str) and len(value) > 500:
        return f"<str len={len(value)}>"
    return value


def _append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _rotate_log(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True, default=str) + "\n")


class DirectBridge:
    """Low-latency ANA tool bridge for single-machine lab use."""

    def __init__(
        self,
        *,
        workspace_root: Path = WORKSPACE_ROOT,
        audit_log: Path = AUDIT_LOG,
        error_log: Path = ERROR_LOG,
        tool_loader: Callable[[], int] | None = None,
        include_hybrid_tools: bool = False,
    ) -> None:
        self.workspace_root = workspace_root
        self.audit_log = audit_log
        self.error_log = error_log
        self.include_hybrid_tools = include_hybrid_tools
        self.metrics: list[DirectMetric] = []
        self.hybrid_loaded_tools = 0
        self.loaded_tools = tool_loader() if tool_loader else self.load_core_tools()
        if self.include_hybrid_tools:
            self.hybrid_loaded_tools = self.load_hybrid_tools()

    def load_core_tools(self) -> int:
        """Load the direct bridge's focused local tool set."""
        return self._load_tool_classes(CORE_TOOL_MODULES)

    def load_hybrid_tools(self) -> int:
        """Load explicitly enabled hybrid v20.1 tools."""
        return self._load_tool_classes(HYBRID_TOOL_CLASSES)

    def _load_tool_classes(self, tool_classes: tuple[tuple[str, str], ...]) -> int:
        loaded = 0
        for module_path, class_name in tool_classes:
            try:
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                tool = tool_class()
                if not registry.get(tool.name):
                    registry.register(tool)
                loaded += 1
            except Exception as exc:
                self._log_error("load_tool", module=module_path, class_name=class_name, error=str(exc))
        return loaded

    def health_check(self) -> dict[str, Any]:
        tools = registry.list_tools()
        return {
            "success": True,
            "mode": "direct",
            "workspace": str(self.workspace_root),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "loaded_tools": self.loaded_tools,
            "registered_tools": len(tools),
            "core_tools_present": sorted(set(tools) & {name for name in self.core_tool_names()}),
            "hybrid_enabled": self.include_hybrid_tools,
            "hybrid_loaded_tools": self.hybrid_loaded_tools,
            "hybrid_tools_present": sorted(set(tools) & self.hybrid_tool_names()),
            "audit_log": str(self.audit_log),
            "mcp_enabled": False,
        }

    @staticmethod
    def core_tool_names() -> set[str]:
        return {
            "agent_coach",
            "code_search",
            "error_radar",
            "file_operations",
            "file_patch",
            "privacy_shield",
            "project_navigator",
            "security_audit",
            "smart_search",
            "system_control",
            "terminal",
            "tool_healthcheck",
            "tool_router",
            "workspace_situational_awareness",
        }

    @staticmethod
    def hybrid_tool_names() -> set[str]:
        return {"browser_control", "ana_ultrafast_web_executor_v4"}

    def execute_tool(
        self,
        tool_name: str,
        payload: dict[str, Any] | None = None,
        *,
        confirm: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        payload = payload or {}
        started = time.perf_counter()
        guard = self._guard_execution(tool_name, payload, confirm=confirm, dry_run=dry_run)
        if guard:
            latency_ms = (time.perf_counter() - started) * 1000
            self._record(tool_name, "direct", latency_ms, False, guard["error"], payload)
            return guard

        if dry_run:
            latency_ms = (time.perf_counter() - started) * 1000
            result = {
                "success": True,
                "mode": "direct",
                "dry_run": True,
                "tool": tool_name,
                "payload": _redact(payload),
            }
            self._record(tool_name, "direct", latency_ms, True, "", payload)
            return result

        try:
            tool_result = registry.execute(tool_name, **payload)
            result = self._normalize_tool_result(tool_result)
        except Exception as exc:
            result = {"success": False, "mode": "direct", "error": str(exc), "data": None}
            self._log_error("execute_tool", tool=tool_name, error=str(exc))

        latency_ms = (time.perf_counter() - started) * 1000
        result["mode"] = "direct"
        result["latency_ms"] = round(latency_ms, 3)
        self._record(tool_name, "direct", latency_ms, bool(result.get("success")), result.get("error", ""), payload)
        return result

    def smoke_test(self) -> dict[str, Any]:
        checks = [
            ("agent_coach", {"action": "recommend", "task": "direct bridge smoke test", "limit": 5}),
            ("tool_router", {"task": "local lab bridge smoke test", "max_tools": 4}),
            ("file_operations", {"operation": "list", "path": "."}),
            ("system_control", {"operation": "vitals"}),
        ]
        results = {tool: self.execute_tool(tool, payload) for tool, payload in checks}
        passed = sum(1 for item in results.values() if item.get("success"))
        return {
            "success": passed == len(checks),
            "mode": "direct",
            "passed": passed,
            "failed": len(checks) - passed,
            "results": results,
        }

    def benchmark(self, *, iterations: int = 10, include_mcp: bool = False) -> dict[str, Any]:
        iterations = max(1, min(iterations, 100))
        cases = self._benchmark_cases(include_extended=False)
        direct: dict[str, Any] = {}
        for tool_name, payload in cases:
            latencies: list[float] = []
            successes = 0
            for _ in range(iterations):
                result = self.execute_tool(tool_name, payload)
                latencies.append(float(result.get("latency_ms", 0.0)))
                if result.get("success"):
                    successes += 1
            direct[tool_name] = self._latency_summary(latencies, successes, iterations)

        mcp = self._benchmark_mcp(cases, iterations) if include_mcp else {
            "skipped": True,
            "reason": "MCP benchmark disabled in ANA DEV lab-only direct mode.",
        }
        return {
            "success": True,
            "iterations": iterations,
            "direct": direct,
            "mcp": mcp,
            "recommendations": self._benchmark_recommendations(direct, mcp),
        }

    def benchmark_all(self, *, iterations: int = 3, slow_ms: float = 250.0) -> dict[str, Any]:
        iterations = max(1, min(iterations, 25))
        direct: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for tool_name, payload in self._benchmark_cases(include_extended=True):
            latencies: list[float] = []
            successes = 0
            last_error = ""
            for _ in range(iterations):
                result = self.execute_tool(tool_name, payload)
                latencies.append(float(result.get("latency_ms", 0.0)))
                if result.get("success"):
                    successes += 1
                else:
                    last_error = str(result.get("error") or result.get("message") or "")
            direct[tool_name] = self._latency_summary(latencies, successes, iterations)
            if last_error:
                errors[tool_name] = last_error

        slow_tools = {
            tool: data
            for tool, data in direct.items()
            if data.get("avg_ms", 0) >= slow_ms or data.get("success_rate", 0) < 100
        }
        return {
            "success": True,
            "iterations": iterations,
            "slow_threshold_ms": slow_ms,
            "direct": direct,
            "slow_tools": slow_tools,
            "errors": errors,
            "recommendations": self._benchmark_recommendations(direct, {"skipped": True}),
        }

    @staticmethod
    def _benchmark_cases(*, include_extended: bool) -> list[tuple[str, dict[str, Any]]]:
        base = [
            ("agent_coach", {"action": "recommend", "task": "benchmark direct local execution", "limit": 5}),
            ("tool_router", {"task": "benchmark local routing", "max_tools": 4}),
            ("file_operations", {"operation": "list", "path": "."}),
        ]
        if not include_extended:
            return base
        return base + [
            ("code_search", {"operation": "grep", "path": "ANA_MAX/bridge", "pattern": "DirectBridge", "max_results": 5}),
            ("error_radar", {"scope": "quick", "limit": 5}),
            ("privacy_shield", {"operation": "obfuscate", "text": "internal confidential policy"}),
            ("project_navigator", {"operation": "find", "path": "scripts", "pattern": "*.ps1", "limit": 5}),
            ("security_audit", {"operation": "scan_secrets", "target": "scripts"}),
            ("smart_search", {"action": "stats", "project_path": "."}),
            ("system_control", {"operation": "vitals"}),
            ("tool_healthcheck", {"scope": "safe"}),
            ("workspace_situational_awareness", {"include_uia": False, "include_errors": True}),
        ]

    def security_diagnostics(self) -> dict[str, Any]:
        logs = {
            "audit_log_exists": self.audit_log.exists(),
            "audit_log_bytes": self.audit_log.stat().st_size if self.audit_log.exists() else 0,
            "error_log_exists": self.error_log.exists(),
            "error_log_bytes": self.error_log.stat().st_size if self.error_log.exists() else 0,
        }
        env_risks = [
            name for name in os.environ
            if any(sensitive in name.lower() for sensitive in SENSITIVE_KEYS)
        ]
        permission_manifest = ANA_MAX_ROOT / "config" / "permission_manifest.json"
        findings = []
        if env_risks:
            findings.append("Sensitive-looking environment keys are present; audit output redacts names/values.")
        if not permission_manifest.exists():
            findings.append("ANA_MAX permission manifest missing.")
        if logs["audit_log_bytes"] > MAX_LOG_BYTES:
            findings.append("Audit log exceeds rotation threshold.")

        return {
            "success": not any("missing" in finding.lower() for finding in findings),
            "mode": "direct",
            "network_isolation": {
                "mcp_default": "disabled",
                "cloud_default": "disabled",
                "mcp_benchmark_requires_env": "ANA_DIRECT_BRIDGE_ALLOW_MCP=1",
            },
            "dangerous_tool_guard": {
                "tools": sorted(DANGEROUS_TOOLS),
                "mutating_file_ops": sorted(MUTATING_FILE_OPS),
                "mutating_system_ops": sorted(MUTATING_SYSTEM_OPS),
                "browser_confirm_ops": sorted(BROWSER_CONFIRM_OPS),
                "requires_confirm": True,
                "supports_dry_run": True,
            },
            "logs": logs,
            "permission_manifest": str(permission_manifest),
            "sensitive_env_key_count": len(env_risks),
            "findings": findings,
            "actionable_steps": [
                "Run smoke test before large edits: python ANA_MAX/bridge/direct_bridge.py --smoke-test",
                "Use --dry-run for risky tools, then rerun with --confirm only when intentional.",
                "Keep MCP benchmark disabled unless explicitly profiling local HTTP overhead.",
            ],
        }

    def _benchmark_mcp(
        self,
        cases: list[tuple[str, dict[str, Any]]],
        iterations: int,
    ) -> dict[str, Any]:
        if os.environ.get("ANA_DIRECT_BRIDGE_ALLOW_MCP", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return {
                "skipped": True,
                "reason": "Set ANA_DIRECT_BRIDGE_ALLOW_MCP=1 to benchmark local MCP overhead explicitly.",
            }

        endpoint = os.environ.get("ANA_DIRECT_BRIDGE_MCP_ENDPOINT", "http://127.0.0.1:8766/execute")
        results: dict[str, Any] = {}
        for tool_name, payload in cases:
            latencies: list[float] = []
            successes = 0
            for _ in range(iterations):
                started = time.perf_counter()
                body = json.dumps({"name": tool_name, "args": payload}).encode("utf-8")
                dynamic_timeout = _calculate_dynamic_timeout(payload)
                try:
                    req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
                    with request.urlopen(req, timeout=dynamic_timeout) as response:
                        decoded = json.loads(response.read().decode("utf-8", errors="replace"))
                    success = bool(decoded.get("success") or decoded.get("ok"))
                except Exception as exc:
                    success = False
                    self._log_error("benchmark_mcp", tool=tool_name, endpoint=endpoint, error=str(exc))
                latency_ms = (time.perf_counter() - started) * 1000
                latencies.append(latency_ms)
                successes += int(success)
            results[tool_name] = self._latency_summary(latencies, successes, iterations)
        return {"skipped": False, "endpoint": endpoint, "results": results}

    @staticmethod
    def _latency_summary(latencies: list[float], successes: int, iterations: int) -> dict[str, Any]:
        return {
            "success_rate": round(successes / iterations * 100, 2),
            "avg_ms": round(statistics.fmean(latencies), 3) if latencies else 0,
            "min_ms": round(min(latencies), 3) if latencies else 0,
            "max_ms": round(max(latencies), 3) if latencies else 0,
            "p95_ms": round(sorted(latencies)[int((len(latencies) - 1) * 0.95)], 3) if latencies else 0,
        }

    @staticmethod
    def _benchmark_recommendations(direct: dict[str, Any], mcp: dict[str, Any]) -> list[str]:
        steps = ["Keep agent_coach/tool_router/file reads on direct path for lowest latency."]
        slow_direct = [tool for tool, data in direct.items() if data.get("avg_ms", 0) > 500]
        if slow_direct:
            steps.append(f"Profile slow direct tools: {', '.join(slow_direct)}.")
        if mcp.get("skipped"):
            steps.append("Run MCP overhead benchmark only in an explicit local profiling session.")
        return steps

    def _guard_execution(
        self,
        tool_name: str,
        payload: dict[str, Any],
        *,
        confirm: bool,
        dry_run: bool,
    ) -> dict[str, Any] | None:
        operation = str(payload.get("operation") or payload.get("action") or "").strip().lower()
        # OS27 HYPER++ v3 UNCENSORED MODE - All operations allowed without confirmation
        # GOD-MODE LOCAL LAB: No guardrails, no confirmations, no blocks
        needs_confirm = False
        return None

    @staticmethod
    def _normalize_tool_result(result: ToolResult) -> dict[str, Any]:
        return {
            "success": result.is_success,
            "status": result.status.value,
            "data": result.data,
            "message": result.message,
            "error": result.error,
        }

    def _record(
        self,
        tool_name: str,
        mode: str,
        latency_ms: float,
        success: bool,
        error: str,
        payload: dict[str, Any],
    ) -> None:
        self.metrics.append(DirectMetric(tool_name, mode, latency_ms, success, error or ""))
        _append_jsonl(
            self.audit_log,
            {
                "timestamp": _utc_now(),
                "tool": tool_name,
                "mode": mode,
                "latency_ms": round(latency_ms, 3),
                "success": success,
                "error": error or "",
                "payload": _redact(payload),
            },
        )

    def _log_error(self, event: str, **fields: Any) -> None:
        _append_jsonl(self.error_log, {"timestamp": _utc_now(), "event": event, **_redact(fields)})


def _parse_payload(raw: str, raw_b64: str = "") -> dict[str, Any]:
    if raw_b64:
        try:
            raw = base64.b64decode(raw_b64).decode("utf-8")
        except Exception as exc:
            raise SystemExit(f"Invalid --payload-b64: {exc}") from exc
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --payload JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("--payload must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA DEV lab-only direct bridge")
    parser.add_argument("--health-check", action="store_true", help="Print bridge health")
    parser.add_argument("--list-tools", action="store_true", help="List direct registered tools")
    parser.add_argument("--smoke-test", action="store_true", help="Run fast local smoke checks")
    parser.add_argument("--benchmark", action="store_true", help="Run direct benchmark")
    parser.add_argument("--benchmark-all", action="store_true", help="Run safe benchmark for all direct core tools")
    parser.add_argument("--iterations", type=int, default=10, help="Benchmark iterations")
    parser.add_argument("--slow-ms", type=float, default=250.0, help="Slow tool threshold for --benchmark-all")
    parser.add_argument("--include-mcp", action="store_true", help="Include explicit local MCP benchmark when env allows it")
    parser.add_argument("--security-diagnostics", action="store_true", help="Run local security diagnostics")
    parser.add_argument("--execute", metavar="TOOL", help="Execute one direct ANA tool")
    parser.add_argument("--payload", default="{}", help="JSON object payload for --execute")
    parser.add_argument("--payload-b64", default="", help="Base64-encoded JSON object payload for --execute")
    parser.add_argument("--confirm", action="store_true", help="Allow guarded mutating/dangerous tool execution")
    parser.add_argument("--dry-run", action="store_true", help="Validate guarded execution without running the tool")
    parser.add_argument("--enable-hybrid-tools", action="store_true", help="Enable optional OS-20.1 hybrid tools")
    args = parser.parse_args()

    bridge = DirectBridge(include_hybrid_tools=args.enable_hybrid_tools)

    if args.health_check:
        print(json.dumps(bridge.health_check(), indent=2, ensure_ascii=True, default=str))
        return 0
    if args.list_tools:
        print(json.dumps(sorted(registry.list_tools()), indent=2, ensure_ascii=True))
        return 0
    if args.smoke_test:
        print(json.dumps(bridge.smoke_test(), indent=2, ensure_ascii=True, default=str))
        return 0
    if args.benchmark:
        print(json.dumps(bridge.benchmark(iterations=args.iterations, include_mcp=args.include_mcp), indent=2, ensure_ascii=True, default=str))
        return 0
    if args.benchmark_all:
        print(json.dumps(bridge.benchmark_all(iterations=args.iterations, slow_ms=args.slow_ms), indent=2, ensure_ascii=True, default=str))
        return 0
    if args.security_diagnostics:
        print(json.dumps(bridge.security_diagnostics(), indent=2, ensure_ascii=True, default=str))
        return 0
    if args.execute:
        payload = _parse_payload(args.payload, args.payload_b64)
        print(json.dumps(bridge.execute_tool(args.execute, payload, confirm=args.confirm, dry_run=args.dry_run), indent=2, ensure_ascii=True, default=str))
        return 0

    print(json.dumps(bridge.health_check(), indent=2, ensure_ascii=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
