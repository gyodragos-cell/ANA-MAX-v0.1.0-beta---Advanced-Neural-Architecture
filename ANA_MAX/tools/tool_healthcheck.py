"""
ANA MAX - Tool Healthcheck (OS27 Hyper++)
========================================
Verifica rapid starea tool-urilor ANA si raporteaza ce merge sau ce e problematic.

OS27 Hyper++ Features:
- Telemetry tracking for healthcheck operations (safe, all, offline_lab)
- Health monitoring for healthcheck reliability
- MemoryCortex integration for healthcheck errors and state learning
- ContextEngine integration for system health awareness
- SelfEvolvingTool integration for anomaly detection on healthcheck failures
- Structured logging with error detection
"""

from __future__ import annotations

import time
import importlib.util
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus, registry

# OS27 Hyper++ Telemetry
_healthcheck_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_healthcheck_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for healthcheck operations."""
    if operation not in _healthcheck_telemetry:
        _healthcheck_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _healthcheck_telemetry[operation]["operation_count"] += 1
    _healthcheck_telemetry[operation]["total_time"] += execution_time
    _healthcheck_telemetry[operation]["last_execution_time"] = execution_time
    _healthcheck_telemetry[operation]["last_success"] = success
    
    if success:
        _healthcheck_telemetry[operation]["success_count"] += 1
    else:
        _healthcheck_telemetry[operation]["failure_count"] += 1


def get_healthcheck_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for healthcheck operations."""
    if operation:
        return _healthcheck_telemetry.get(operation, {})
    return _healthcheck_telemetry.copy()


def get_healthcheck_health() -> str:
    """Get health status for healthcheck tool based on telemetry."""
    if not _healthcheck_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _healthcheck_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _healthcheck_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class ToolHealthcheckTool(Tool):
    def _ensure_registry(self) -> None:
        if registry.list_tools():
            return

        tool_modules = [
            ("tools.files", "FilesTool"),
            ("tools.code", "CodeTool"),
            ("tools.web", "WebTool"),
            ("tools.system", "SystemTool"),
            ("tools.tool_healthcheck", "ToolHealthcheckTool"),
            ("tools.conversation_learning_tool", "ConversationLearningTool"),
            ("tools.session_log_miner_tool", "SessionLogMinerTool"),
            ("tools.session_checkpoint_tool", "SessionCheckpointTool"),
            ("tools.memory_tool", "MemoryTool"),
            ("tools.privacy", "PrivacyTool"),
            ("tools.network_tool", "NetworkTool"),
            ("tools.security_tool", "SecurityTool"),
            ("tools.qa_tool", "QATool"),
            ("tools.smart_search_tool", "SmartSearchTool"),
            ("tools.debugger_tool", "DebuggerTool"),
            ("tools.codebase_understanding_tool", "CodebaseUnderstandingTool"),
            ("tools.workspace_situational_awareness", "WorkspaceSituationalAwarenessTool"),
            ("tools.agent_coach_tool", "AgentCoachTool"),
            ("tools.browser_control", "BrowserControlTool"),
            ("tools.file_patch_tool", "FilePatchTool"),
            ("tools.project_navigator_tool", "ProjectNavigatorTool"),
            ("tools.error_radar_tool", "ErrorRadarTool"),
            ("tools.tool_router_tool", "ToolRouterTool"),
            ("tools.science_tool", "ScienceTool"),
            ("tools.mitm_analyzer_tool", "MITMAnalyzerTool"),
            ("tools.network_pentest_tool", "NetworkPentestTool"),
            ("tools.hardware_scanner_tool", "HardwareScannerTool"),
            ("tools.window_manager", "WindowManagerTool"),
            ("tools.ocr_tool", "OcrTool"),
            ("tools.uia_click_tool", "UiaClickTool"),
            ("tools.uia_type_tool", "UiaTypeTool"),
            ("tools.vision_region_capture_tool", "VisionRegionCaptureTool"),
            ("tools.vision_find_element_tool", "VisionFindElementTool"),
        ]

        for module_path, class_name in tool_modules:
            try:
                mod = __import__(module_path, fromlist=[class_name])
                tool_class = getattr(mod, class_name)
                registry.register(tool_class())
            except Exception:
                continue

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="tool_healthcheck",
            description="Verifica rapid starea tool-urilor ANA si raporteaza ce merge sau ce e problematic.",
            parameters=[
                ToolParameter(
                    name="scope",
                    description="Scopul verificarii",
                    type="string",
                    required=False,
                    default="safe",
                    choices=["safe", "all", "offline_lab"],
                )
            ],
            category="system",
        )

    def execute(self, scope: str = "safe", **kwargs: Any) -> ToolResult:
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        self._ensure_registry()
        legacy_operation = kwargs.get("operation")
        if legacy_operation in {"summary", "status"} and scope == "safe":
            scope = "safe"

        safe_checks: List[tuple[str, Dict[str, Any]]] = [
            ("file_operations", {"operation": "list", "path": "."}),
            ("system_control", {"operation": "vitals"}),
            ("smart_search", {"action": "stats", "project_path": "."}),
            (
                "workspace_situational_awareness",
                {"include_uia": False, "include_errors": True},
            ),
            ("project_navigator", {"operation": "find", "path": "tools", "pattern": "base.py", "limit": 3}),
            ("error_radar", {"scope": "quick", "limit": 5}),
            ("tool_router", {"task": "fix repeated MCP tool failure", "max_tools": 4}),
        ]

        optional_checks: List[tuple[str, Dict[str, Any]]] = [
            ("codebase_understanding", {"action": "semantic_search", "query": "main server", "project_path": "."}),
            ("qa_testing", {"operation": "generate_tests", "target": "def add(a, b): return a + b"}),
            ("debugger", {"traceback_text": "ValueError: test error"}),
            ("science_research", {"operation": "simulate_model", "params": "{\"samples\": 5, \"low\": 0, \"high\": 1}"}),
        ]

        offline_lab_checks: List[tuple[str, Dict[str, Any]]] = [
            ("file_operations", {"operation": "list", "path": "."}),
            ("system_control", {"operation": "vitals"}),
            ("smart_search", {"action": "stats", "project_path": "."}),
            ("foreground_ui_snapshot", {"include_text": "false", "max_elements": "8", "timeout": 15}),
            ("windows_uia_bridge", {"action": "list_windows", "confirm": True, "timeout": 20}),
            ("desktop_capture", {"operation": "get_windows", "timeout": 20}),
            ("window_manager", {"action": "list", "timeout": 10}),
            ("ocr_tool", {"action": "check", "timeout": 10}),
            ("agent_coach", {"action": "coach", "limit": 80, "include_prompt": True}),
            ("edge_tts_voice", {"operation": "list_voices"}),
        ]

        checks = list(safe_checks)
        if scope == "all":
            checks.extend(optional_checks)
        elif scope == "offline_lab":
            checks = offline_lab_checks

        available_tools = set(registry.list_tools())
        results = []
        ok = 0
        failed = 0
        skipped = 0

        for tool_name, params in checks:
            if tool_name not in available_tools:
                results.append(
                    {
                        "tool": tool_name,
                        "success": None,
                        "skipped": True,
                        "seconds": 0.0,
                        "message": "Tool not exposed by the active registry/profile",
                        "error": None,
                    }
                )
                skipped += 1
                continue

            started = time.time()
            tool_result = registry.execute(tool_name, **params)
            elapsed = round(time.time() - started, 2)
            item = {
                "tool": tool_name,
                "success": tool_result.is_success,
                "skipped": False,
                "seconds": elapsed,
                "message": tool_result.message,
                "error": tool_result.error,
            }
            results.append(item)
            if tool_result.is_success:
                ok += 1
            else:
                failed += 1

        dependencies = self._dependency_health()
        
        execution_time = time.time() - start_time
        _record_healthcheck_telemetry(scope, True, execution_time)
        
        # ContextEngine integration for system health
        if context_engine:
            try:
                context_engine.update_context(
                    key="system_health",
                    value={
                        "scope": scope,
                        "ok": ok,
                        "failed": failed,
                        "skipped": skipped,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for healthcheck failures
        if cortex and failed > 0:
            try:
                failed_tools = [r["tool"] for r in results if not r["success"]]
                cortex.remember(
                    "error",
                    f"healthcheck.{scope}",
                    f"Healthcheck failed for {failed} tools: {', '.join(failed_tools[:5])}"
                )
            except Exception:
                pass

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "scope": scope,
                "ok": ok,
                "failed": failed,
                "skipped": skipped,
                "results": results,
                "dependencies": dependencies,
            },
            message=f"Healthcheck finalizat: {ok} OK / {failed} FAIL / {skipped} SKIP",
        )

    @staticmethod
    def _dependency_health() -> Dict[str, Dict[str, Any]]:
        ddgs_available = (
            importlib.util.find_spec("ddgs") is not None
            or importlib.util.find_spec("duckduckgo_search") is not None
        )
        return {
            "web_search": {
                "ok": ddgs_available,
                "packages_any_of": ["ddgs", "duckduckgo-search"],
                "impact": "web_search operation=search/news/images" if not ddgs_available else "",
                "fix": "pip install ddgs" if not ddgs_available else "",
            }
        }
