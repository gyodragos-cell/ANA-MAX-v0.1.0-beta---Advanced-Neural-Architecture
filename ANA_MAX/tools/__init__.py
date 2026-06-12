"""
A.N.A. MAX - Tools Package.

The package must stay cheap and safe to import. Tool modules are loaded lazily
so one missing optional dependency cannot break `from tools.base import ...` or
the direct bridge startup path.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .base import Tool, ToolRegistry, ToolResult

_CLASS_TO_MODULE: dict[str, str] = {
    "ADBTool": "adb_tool",
    "AdvancedScannerTool": "advanced_scanner",
    "AgentCoachTool": "agent_coach_tool",
    "AnaContextTool": "ana_context_tool",
    "APKAnalyzerTool": "apk_analyzer",
    "AutonomousTool": "autonomous_tool",
    "BashExecTool": "verdent_tools",
    "BinaryMapTool": "binary_map_tool",
    "BrowserControlTool": "browser_control",
    "CodebaseUnderstandingTool": "codebase_understanding_tool",
    "CodeContextPackTool": "code_context_pack_tool",
    "CodeSearchTool": "code_search",
    "CodeTool": "code",
    "ConversationLearningTool": "conversation_learning_tool",
    "DebuggerTool": "debugger_tool",
    "DesktopCaptureTool": "desktop_capture",
    "DesktopControlTool": "desktop_control_tool",
    "EdgeTTSVoice": "edge_tts_voice",
    "EditTool": "edit_tool",
    "ErrorRadarTool": "error_radar_tool",
    "EventStreamTool": "event_stream_tool",
    "FilePatchTool": "file_patch_tool",
    "FilesTool": "files",
    "ForegroundUISnapshotTool": "foreground_ui_snapshot",
    "FridaTool": "frida_automation",
    "GlobSearchTool": "verdent_tools",
    "GraphContextPackTool": "graph_context_pack_tool",
    "GrepContentTool": "verdent_tools",
    "GrepFileTool": "verdent_tools",
    "HardwareScannerTool": "hardware_scanner_tool",
    "InputApiProbeTool": "input_api_probe_tool",
    "LiveDesktopViewerTool": "live_desktop_viewer",
    "MemoryTool": "memory_tool",
    "MITMAnalyzerTool": "mitm_analyzer_tool",
    "NetworkPentestTool": "network_pentest_tool",
    "NetworkTool": "network_tool",
    "OcrTool": "ocr_tool",
    "PrivacyTool": "privacy",
    "ProjectNavigatorTool": "project_navigator_tool",
    "QATool": "qa_tool",
    "RemoteControlTool": "remote_control_tool",
    "ScienceTool": "science_tool",
    "SecurityTool": "security_tool",
    "SessionAuditTool": "session_audit_tool",
    "SessionCheckpointTool": "session_checkpoint_tool",
    "SessionLogMinerTool": "session_log_miner_tool",
    "SessionRemSleepTool": "session_rem_sleep_tool",
    "SmartSearchTool": "smart_search_tool",
    "SwarmTool": "swarm_tool",
    "SystemOptimizationTool": "system_optimization_tool",
    "SystemTool": "system",
    "TaskTool": "task_tool",
    "TerminalTool": "terminal_tool",
    "TodoWriteTool": "todo_tool",
    "ToolHealthcheckTool": "tool_healthcheck",
    "ToolRouterTool": "tool_router_tool",
    "UiaClickTool": "uia_click_tool",
    "UiaTypeTool": "uia_type_tool",
    "VectorMemoryTool": "vector_memory_tool",
    "VisionFallbackTool": "vision_fallback_tool",
    "VisionFindElementTool": "vision_find_element_tool",
    "VisionRegionCaptureTool": "vision_region_capture_tool",
    "WatchdogTool": "watchdog",
    "WebAIBridgeTool": "web_ai_bridge",
    "WebFetchTool": "verdent_tools",
    "WebScraperTool": "web_scraper",
    "WebTool": "web",
    "WindowManagerTool": "window_manager",
    "WindowsDeepSightTool": "windows_deep_sight",
    "WindowsInsightTool": "windows_insight_tool",
    "WindowsUiaBridgeTool": "windows_uia_bridge",
}

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "load_tool",
    *_CLASS_TO_MODULE.keys(),
]


def load_tool(name: str) -> Any:
    """Lazy-load a tool module from this package."""
    try:
        return import_module(f"{__name__}.{name}")
    except ImportError as exc:
        raise ImportError(f"Tool module '{name}' is not available in {__name__}") from exc


def __getattr__(name: str) -> Any:
    module_name = _CLASS_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = load_tool(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
