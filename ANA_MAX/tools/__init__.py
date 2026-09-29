"""
A.N.A. MAX - Tools Package (OS27 Hyper++ Registry)

The package must stay cheap and safe to import. Tool modules are loaded lazily
so one missing optional dependency cannot break `from tools.base import ...` or
the direct bridge startup path.

OS27 Hyper++ Features:
- Tool capability metadata (category, health, version)
- Loading telemetry (load count, time, failures)
- Health tracking (healthy/degraded/broken)
- AI Core integration hooks
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys
import time
import logging
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .base import Tool, ToolRegistry, ToolResult

logger = logging.getLogger("ANA.ToolsRegistry")

_CLASS_TO_MODULE: dict[str, str] = {
    "ADBTool": "adb_tool",
    "AdvancedScannerTool": "advanced_scanner",
    "AdvancedSwarmTool": "advanced_swarm_tool",
    "AdaLTool": "adal_tool",
    "AgentCoachTool": "agent_coach_tool",
    "AnaContextTool": "ana_context_tool",
    "EngineerPlatformTool": "engineer_platform_tool",
    "APKAnalyzerTool": "apk_analyzer",
    "ArtifactTool": "artifact_tool",
    "AutonomousTool": "autonomous_tool",
    "BashExecTool": "verdent_tools",
    "BinaryMapTool": "binary_map_tool",
    "BlackBoxRecorderTool": "black_box_recorder",
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
    "GraphMetricsTool": "graph_tool_router",
    "GrepContentTool": "verdent_tools",
    "GrepFileTool": "verdent_tools",
    "GitTool": "git_tool",
    "HardwareScannerTool": "hardware_scanner_tool",
    "InputApiProbeTool": "input_api_probe_tool",
    "LiveDebugConsoleTool": "live_debug_console",
    "LiveDesktopViewerTool": "live_desktop_viewer",
    "LargeFileReaderTool": "large_file_reader",
    "LargeFileReaderHyperTool": "large_file_reader_ultimate",
    "MemoryTool": "memory_tool",
    "MITMAnalyzerTool": "mitm_analyzer_tool",
    "NetworkPentestTool": "network_pentest_tool",
    "NetworkTool": "network_tool",
    "OcrTool": "ocr_tool",
    "OllamaLiveLoggerTool": "ollama_live_logger",
    "PrivacyTool": "privacy",
    "ProcmonMonitorTool": "procmon_monitor",
    "ProjectAnalyzerTool": "project_reader_tool",
    "ProjectNavigatorTool": "project_navigator_tool",
    "QATool": "qa_tool",
    "RemoteControlTool": "remote_control_tool",
    "ScienceTool": "science_tool",
    "SecurityTool": "security_tool",
    "SessionAuditTool": "session_audit_tool",
    "SessionCheckpointTool": "session_checkpoint_tool",
    "SessionLifecycleTool": "session_lifecycle_tool",
    "SessionLogMinerTool": "session_log_miner_tool",
    "SessionRemSleepTool": "session_rem_sleep_tool",
    "SmartSearchTool": "smart_search_tool",
    "SwarmTool": "swarm_tool",
    "SystemOptimizationTool": "system_optimization_tool",
    "SystemTool": "system",
    "TaskTool": "task_tool",
    "TerminalTool": "terminal_tool",
    "TextToSpeechTool": "text_to_speech",
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
    "WindowsFridaTelemetryTool": "windows_frida_telemetry",
    "WindowsInsightTool": "windows_insight_tool",
    "WindowsUiaBridgeTool": "windows_uia_bridge",
    "DLLInjectionTool": "dll_injection_tool",
    "MemoryPatchingTool": "memory_patching_tool",
    "ProcessSecurityTool": "process_security_tool",
    "NetworkProtocolTool": "network_protocol_tool",
    "ContinualLearningTool": "continual_learning_tool",
    "SelfEvolvingTool": "self_evolving_tool",
    "SystemInspectorTool": "system_inspector_tool",
    "TerminalMonitorTool": "terminal_monitor",
    "UniversalTaskOrchestratorTool": "universal_task_orchestrator",
    "AutoRecoveryTool": "auto_recovery",
    "UnlimitedOCRTool": "unlimited_ocr_tool",
    "WorkspaceSituationalAwarenessTool": "workspace_situational_awareness",
    "SystemIntegrityCheckTool": "system_integrity_tool",
    "LiveToolHealer": "live_tool_healer",
    "ToolContractValidator": "tool_contract_validator",
    "SchemaDiff": "schema_diff",
    "AnaRuntimeInspector": "ana_runtime_inspector",
    "GraphToolRouterTool": "graph_tool_router",
    "GraphStatsTool": "graph_tool_router",
    "AgentContextInjectorTool": "agent_context_injector",
    "ClipboardManagerTool": "clipboard_manager",
    "ProjectReaderTool": "project_reader_tool",
    "ProjectSearchTool": "project_reader_tool",
    "SkillTool": "skill_tool",
    "SystemRepairTool": "system_inspector_tool",
    "SystemIntegrityHyperTool": "system_integrity_hyper",
    "UnlimitedOCRHealthTool": "unlimited_ocr_tool",
    "UnlimitedOCRStartTool": "unlimited_ocr_tool",
    "WatchdogBusTool": "watchdog_bus",
    "AgentOmniscientEyeTool": "agent_omniscient_eye_tool",
    # AI Core Adapters
    "ContextEngineAdapter": "tool_adapters",
    "MemoryCortexAdapter": "tool_adapters",
    "ProactiveInterruptAdapter": "tool_adapters",
    "SelfEvolvingToolAdapter": "tool_adapters",
    "AnaOrchestratorAdapter": "tool_adapters",
    "ContextBridgeAdapter": "tool_adapters",
    "WindowManagerAdapter": "tool_adapters",
    "ClipboardManagerAdapter": "tool_adapters",
    "WatchdogAdapter": "tool_adapters",
    "NativeTelemetryAdapter": "tool_adapters",
    "OcrToolAdapter": "tool_adapters",
    "HyperFileReaderAdapter": "tool_adapters",
    "SystemIntegrityHyperAdapter": "tool_adapters",
    # Tool Brain Modules
    "ToolPriorityMap": "tool_priority_map",
    "ToolHealthDashboard": "tool_health_dashboard",
    "ToolAutoDiscovery": "tool_auto_discovery",
    "ToolSmokeTest": "tool_smoke_test",
    "ToolAutoFix": "tool_auto_fix",
    "ToolManifestLoader": "tool_manifest_loader",
    "ToolMapper": "tool_mapper",
    "ToolchainDiscovery": "toolchain_discovery",
    # AI Core Direct Tools (Phase 1 repair)
    "ContextEngineTool": "context_engine",
    "ProactiveInterruptTool": "proactive_interrupt",
    "OS27NervousSystem": "os27_nervous_system",
    # Core Infrastructure
    "MemoryCortex": "memory_cortex",
    "ContextBridge": "context_bridge",
    "ReflexDispatcher": "reflex_dispatcher",
    "ReflexCore": "reflex_core",
    # SmartSearchTool already mapped to smart_search_tool (line 94)
    "DashboardModuleUnifier": "dashboard_module_unifier",
    "DevToolsManager": "devtools_manager",
    "LiveVoiceBridge": "live_voice_bridge",
    "KokoroVoice": "kokoro_voice",
    "WhisperSTT": "whisper_stt",
    "VoiceCommentary": "voice_commentary",
    "MitmLiveAnalyzer": "mitmproxy_live_analyzer",
}

# OS27 Hyper++ Tool Metadata (capability, category, health tracking)
_TOOL_METADATA: dict[str, dict[str, Any]] = {
    "LargeFileReaderHyperTool": {
        "category": "file_analysis",
        "description": "OS27 Hyper Enterprise streaming reader for massive files",
        "version": "1.0.0",
        "capabilities": ["compression-aware", "semantic-chunking", "anomaly-detection", "mcp-ready"],
        "health": "healthy",
    },
    "SystemIntegrityCheckTool": {
        "category": "system",
        "description": "OS27 Hyper++ System Integrity Auditor for ANA MAX",
        "version": "1.0.0",
        "capabilities": ["registry-check", "backend-check", "config-check", "dependency-check", "log-analysis", "temp-scan", "ai-core-check", "telemetry", "health-scoring"],
        "health": "healthy",
    },
    # AI Core Adapters
    "ContextEngineAdapter": {
        "category": "ai_core",
        "description": "Context Engine Adapter - observes, classifies, predicts intentions",
        "version": "1.0.0",
        "capabilities": ["context-observation", "intent-prediction", "pattern-learning", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "MemoryCortexAdapter": {
        "category": "ai_core",
        "description": "Memory Cortex Adapter - 4 types of memory (episodic, semantic, procedural, error log)",
        "version": "1.0.0",
        "capabilities": ["episodic-memory", "semantic-memory", "procedural-memory", "error-injection", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ProactiveInterruptAdapter": {
        "category": "ai_core",
        "description": "Proactive Interrupt Adapter - 5 active detectors (STUCK, SEQUENCE, CLIPBOARD INTENT, REPEAT, CONTEXT SHIFT)",
        "version": "1.0.0",
        "capabilities": ["stuck-detection", "sequence-detection", "clipboard-intent", "repeat-detection", "context-shift", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "SelfEvolvingToolAdapter": {
        "category": "ai_core",
        "description": "Self-Evolving Tool Adapter - auto-fix, auto-improve, auto-install",
        "version": "1.0.0",
        "capabilities": ["auto-fix", "auto-improve", "auto-install", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "AnaOrchestratorAdapter": {
        "category": "ai_core",
        "description": "ANA Orchestrator Adapter - task orchestrator for complex multi-step operations",
        "version": "1.0.0",
        "capabilities": ["task-planning", "tool-coordination", "batch-processing", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ContextBridgeAdapter": {
        "category": "ai_core",
        "description": "Context Bridge Adapter - session persistence and context restoration",
        "version": "1.0.0",
        "capabilities": ["session-persistence", "context-restoration", "event-tracking", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "WindowManagerAdapter": {
        "category": "ai_core",
        "description": "Window Manager Adapter - window control and management",
        "version": "1.0.0",
        "capabilities": ["window-list", "window-snap", "window-move", "window-tile", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ClipboardManagerAdapter": {
        "category": "ai_core",
        "description": "Clipboard Manager Adapter - clipboard operations",
        "version": "1.0.0",
        "capabilities": ["clipboard-read", "clipboard-write", "clipboard-history", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "WatchdogAdapter": {
        "category": "ai_core",
        "description": "Watchdog Adapter - workspace monitoring and file change detection",
        "version": "1.0.0",
        "capabilities": ["file-monitoring", "change-detection", "workspace-awareness", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "NativeTelemetryAdapter": {
        "category": "ai_core",
        "description": "Native Telemetry Adapter - system telemetry collection",
        "version": "1.0.0",
        "capabilities": ["system-vitals", "performance-metrics", "resource-monitoring", "telemetry"],
        "health": "unknown",
        "os27_hyper": True,
    },
    # Tool Brain Modules
    "ToolPriorityMap": {
        "category": "tool_brain",
        "description": "Tool Priority Map - categorizes tools by priority (P0/P1/P2)",
        "version": "1.0.0",
        "capabilities": ["priority-classification", "tool-categorization"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolHealthDashboard": {
        "category": "tool_brain",
        "description": "Tool Health Dashboard - computes health scores and generates dashboard",
        "version": "1.0.0",
        "capabilities": ["health-scoring", "dashboard-generation", "telemetry-aggregation"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolAutoDiscovery": {
        "category": "tool_brain",
        "description": "Tool Auto Discovery - auto-discovers tools and checks integrity",
        "version": "1.0.0",
        "capabilities": ["auto-discovery", "integrity-check", "discovery-report"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolSmokeTest": {
        "category": "tool_brain",
        "description": "Tool Smoke Test - runs smoke tests on tools",
        "version": "1.0.0",
        "capabilities": ["smoke-testing", "telemetry-check", "test-report"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolAutoFix": {
        "category": "tool_brain",
        "description": "Tool Auto Fix - auto-fixes broken tools",
        "version": "1.0.0",
        "capabilities": ["auto-fix", "failure-analysis", "fix-report"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolManifestLoader": {
        "category": "tool_brain",
        "description": "Tool Manifest Loader - loads tool manifests",
        "version": "1.0.0",
        "capabilities": ["manifest-loading", "tool-metadata"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolMapper": {
        "category": "tool_brain",
        "description": "Tool Mapper - maps tools to capabilities",
        "version": "1.0.0",
        "capabilities": ["capability-mapping", "tool-discovery"],
        "health": "unknown",
        "os27_hyper": True,
    },
    "ToolchainDiscovery": {
        "category": "tool_brain",
        "description": "Toolchain Discovery - discovers toolchains and workflows",
        "version": "1.0.0",
        "capabilities": ["toolchain-discovery", "workflow-analysis"],
        "health": "unknown",
        "os27_hyper": True,
    },
}

# OS27 Hyper++ Loading Telemetry
_tool_load_stats: dict[str, dict[str, Any]] = {}

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "load_tool",
    "get_tool_metadata",
    "get_tool_load_stats",
    "get_all_tool_stats",
    "get_tool_health",
    "get_all_tool_health",
    *_CLASS_TO_MODULE.keys(),
]


def load_tool(name: str) -> Any:
    """
    Lazy-load a tool module from this package with OS27 Hyper++ telemetry.
    
    Args:
        name: Module name to load (e.g., "large_file_reader_ultimate")
    
    Returns:
        The loaded module
    
    Raises:
        ImportError: If tool module is not available
    """
    start_time = time.time()
    try:
        module = import_module(f"{__name__}.{name}")
        load_time = time.time() - start_time
        
        # Record telemetry
        if name not in _tool_load_stats:
            _tool_load_stats[name] = {
                "load_count": 0,
                "total_load_time": 0.0,
                "failures": 0,
                "last_load_time": 0.0,
            }
        _tool_load_stats[name]["load_count"] += 1
        _tool_load_stats[name]["total_load_time"] += load_time
        _tool_load_stats[name]["last_load_time"] = load_time
        
        logger.debug(f"Tool '{name}' loaded in {load_time:.3f}s")
        return module
    except ImportError as exc:
        # Record failure
        if name not in _tool_load_stats:
            _tool_load_stats[name] = {
                "load_count": 0,
                "total_load_time": 0.0,
                "failures": 0,
                "last_load_time": 0.0,
            }
        _tool_load_stats[name]["failures"] += 1
        logger.warning(f"Tool '{name}' load failed: {exc}")
        _report_tool_load_failure_to_ai_core(name, exc)
        raise ImportError(f"Tool module '{name}' is not available in {__name__}") from exc


def __getattr__(name: str) -> Any:
    """Lazy-load tool class via __getattr__ with telemetry."""
    module_name = _CLASS_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = load_tool(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


# OS27 Hyper++ Health Check Functions
def get_tool_metadata(tool_name: str) -> dict[str, Any] | None:
    """
    Get OS27 Hyper++ metadata for a tool.
    
    Args:
        tool_name: Tool class name (e.g., "LargeFileReaderHyperTool")
    
    Returns:
        Metadata dict or None if not found
    """
    return _TOOL_METADATA.get(tool_name)


def get_tool_load_stats(tool_name: str) -> dict[str, Any] | None:
    """
    Get loading telemetry for a tool module.
    
    Args:
        tool_name: Module name (e.g., "large_file_reader_ultimate")
    
    Returns:
        Stats dict or None if not found
    """
    return _tool_load_stats.get(tool_name)


def get_all_tool_stats() -> dict[str, dict[str, Any]]:
    """
    Get loading telemetry for all tools.
    
    Returns:
        Dict mapping tool names to their stats
    """
    return _tool_load_stats.copy()


def get_tool_health(tool_name: str) -> str:
    """
    Get health status for a tool.
    
    Args:
        tool_name: Tool class name
    
    Returns:
        Health status: "healthy", "degraded", "broken", or "unknown"
    """
    metadata = _TOOL_METADATA.get(tool_name)
    if metadata:
        return metadata.get("health", "unknown")
    
    # Infer health from load stats using failure rate pattern
    stats = _tool_load_stats.get(tool_name)
    if stats:
        total_loads = stats["load_count"] + stats["failures"]
        if total_loads == 0:
            return "unknown"
        failure_rate = stats["failures"] / total_loads
        if failure_rate > 0.5:
            return "broken"
        if failure_rate > 0.1:
            return "degraded"
        if stats["load_count"] > 0:
            return "healthy"
    
    return "unknown"


def get_all_tool_health() -> dict[str, str]:
    """
    Get health status for all registered tools.
    
    Returns:
        Dict mapping tool class names to health status
    """
    health_dict = {}
    for tool_name in _CLASS_TO_MODULE.keys():
        health_dict[tool_name] = get_tool_health(tool_name)
    return health_dict


# OS27 Hyper++ AI Core Integration Hooks
def _report_tool_load_failure_to_ai_core(module_name: str, error: ImportError) -> None:
    """
    Best-effort reporting of tool load failures to AI Core components.
    
    Args:
        module_name: Module name that failed to load
        error: The ImportError that occurred
    """
    try:
        from tools.memory_cortex import MemoryCortex
        cortex = MemoryCortex(db_path=str(ROOT / "ana_memory.db"))
        cortex.remember(
            key=f"tool_load_error:{module_name}",
            value={
                "module_name": module_name,
                "error": str(error),
                "timestamp": time.time(),
            },
            memory_type="error",
        )
    except Exception:
        pass  # MemoryCortex integration is optional

    try:
        from tools.self_evolving_tool import SelfEvolvingTool
        evolver = SelfEvolvingTool(
            project_root=str(ROOT),
            db_path=str(ROOT / "ana_memory.db"),
            llm_url="http://localhost:11434/api/generate",
            llm_model="mistral",
            auto_improve=False,
        )
        if hasattr(evolver, "_log_change"):
            evolver._log_change(
                file_path=f"tools/{module_name}.py",
                change_type="tool_load_error",
                description=f"Import error: {str(error)[:200]}",
                diff_summary="",
                success=False,
            )
    except Exception:
        pass  # SelfEvolvingTool integration is optional

    try:
        from tools.context_engine import ContextEngine
        ctx = ContextEngine(db_path=str(ROOT / "ana_memory.db"))
        ctx.apply_feedback(
            context_key=f"tool_health:{module_name}",
            feedback="negative",
            reason="tool_load_failed"
        )
    except Exception:
        pass  # ContextEngine integration is optional
