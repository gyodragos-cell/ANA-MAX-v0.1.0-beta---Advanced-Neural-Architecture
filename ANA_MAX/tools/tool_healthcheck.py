"""
ANA MAX - Tool Healthcheck
"""

from __future__ import annotations

import time
import importlib.util
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus, registry


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

        results = []
        ok = 0
        failed = 0

        for tool_name, params in checks:
            started = time.time()
            tool_result = registry.execute(tool_name, **params)
            elapsed = round(time.time() - started, 2)
            item = {
                "tool": tool_name,
                "success": tool_result.is_success,
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

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "scope": scope,
                "ok": ok,
                "failed": failed,
                "results": results,
                "dependencies": dependencies,
            },
            message=f"Healthcheck finalizat: {ok} OK / {failed} FAIL",
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
