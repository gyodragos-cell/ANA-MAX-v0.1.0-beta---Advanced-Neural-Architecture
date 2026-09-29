#!/usr/bin/env python3
"""
ANA MAX - Arhitectura Neurala Avansata
======================================
Mod MCP: OpenCode este creierul, ANA este corpul cu 20+ tools.
Fara Ollama. Fara API keys. Doar MCP server local.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import signal
import sys
import unicodedata
from pathlib import Path
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from core.event_stream import get_event_stream
from core.workspace_watchdog import WorkspaceWatchdog
from core.native_telemetry import NativeTelemetry
from core.session_logger import get_session_logger, log_action, log_result, log_error, log_next_step
from core.tool_graph import initialize_default_graph


def _signal_handler(signum, frame):
    """Handler pentru inchidere cand se opreste terminalul."""
    print("\n[ANA MAX] Se opreste...")
    logging.getLogger(__name__).info("ANA MAX oprit de utilizator")
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)





BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.chdir(BASE_DIR)

from core.config import config  # noqa: E402
from core.voice_command_router import (  # noqa: E402
    detect_voice_command,
    handle_voice_command,
    cleanup_stale_pid as cleanup_voice_stale_pid,
)

config.load(str(CONFIG_PATH))

# La startup: curatam PID-uri moarte ale live_voice_agent (anti-zombie)
try:
    cleanup_voice_stale_pid()
except Exception as _e:
    logging.getLogger(__name__).warning("voice pid cleanup failed: %s", _e)


def _is_vscode_agent_session() -> bool:
    """Return True when VS Code marks this terminal command as agent-run."""
    value = os.environ.get("VSCODE_AGENT", "")
    return value.strip().lower() not in {"", "0", "false", "no"}


def _compact_agent_output() -> bool:
    return _is_vscode_agent_session()


def _print_tool_load(message: str) -> None:
    if not _compact_agent_output():
        print(message)


def _load_tool_class(module_path: str, class_name: str):
    mod = __import__(module_path, fromlist=[class_name])
    return getattr(mod, class_name)


def _build_runtime_agent():
    from core.agent import ANAAgent

    # ANA_BACKEND env var override — allows START_ANA_OPENROUTER.bat to force backend
    backend = os.environ.get("ANA_BACKEND") or config.get("ai.primary_backend", "none")

    log_action(f"Building ANA Agent with backend: {backend}", {"backend": backend})

    try:
        agent = ANAAgent(backend=backend)
        log_result(f"ANA Agent built successfully with backend: {backend}", success=True)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Falling back to tools-only ANAAgent during tool registration: %s",
            exc,
        )
        log_error(f"Failed to build agent with backend {backend}, falling back to tools-only", exc)
        agent = ANAAgent(backend="none")
        log_result("ANA Agent built with tools-only fallback", success=True)

    # Store agent in globals for loop detection access
    globals()['agent'] = agent

    try:
        from core.memory import get_memory
        agent.memory = get_memory()
        log_result("Memory cortex attached successfully", success=True)
    except Exception as exc:
        logging.getLogger(__name__).warning("core.memory unavailable, skipping memory attach: %s", exc)
        log_error("Failed to attach memory cortex", exc)
    
    agent.session_id = getattr(agent, "_session_id", "ana_http")
    agent.engineer_platform = SimpleNamespace(workspace_root=BASE_DIR)
    
    log_action(f"Agent session configured: {agent.session_id}", {"session_id": agent.session_id})
    return agent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ANA MAX - MCP Server cu release-ready tools, AI Desktop Control, AI Core Intelligence pentru OpenCode"
    )
    parser.add_argument("--port", "-p", type=int, default=8765, help="Port MCP server (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Host MCP server (default: 127.0.0.1)")
    parser.add_argument("--debug", "-d", action="store_true", help="Activeaza logging debug")
    parser.add_argument("--list-tools", action="store_true", help="Listeaza toate tool-urile si iese")
    parser.add_argument("--test", action="store_true", help="Ruleaza teste rapide pe tool-uri")
    parser.add_argument("--watchdog", action="store_true", help="Start workspace watchdog (implicit fara acest flag)")
    parser.add_argument("--telemetry", action="store_true", help="Start native telemetry with Frida")
    return parser


def _print_banner() -> None:
    print(
        """
====================================================================
     A.N.A. MAX - Arhitectura Neurala Avansata
     MCP Server | Release Tools | AI Desktop Control | OpenCode Ready
     AI Core: Context Engine, Memory Cortex, Orchestrator
====================================================================
""".strip()
    )


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ana_max.log"

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Color codes for terminal output
    class ColoredFormatter(logging.Formatter):
        """Formatter cu culori pentru terminal"""
        COLORS = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Green
            'WARNING': '\033[33m',    # Yellow
            'ERROR': '\033[31m',      # Red
            'CRITICAL': '\033[35m',   # Magenta
        }
        RESET = '\033[0m'

        def format(self, record):
            if record.levelname in self.COLORS:
                record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            return super().format(record)

    class _AsciiLogFilter(logging.Filter):
        """Fold every log record to plain ASCII so emoji/diacritics never show up
        as mojibake (e.g. a UTF-8 check-mark logged as garbled bytes) and never
        crash a cp1252 console or log file."""
        def filter(self, record):
            try:
                msg = record.getMessage()
            except Exception:
                msg = str(record.msg)
            decomposed = unicodedata.normalize("NFKD", msg)
            stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
            record.msg = stripped.encode("ascii", "ignore").decode("ascii")
            record.args = ()
            return True

    ascii_filter = _AsciiLogFilter()

    # Plain formatter for file
    plain_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s")

    # Colored formatter for console (improved format with better spacing)
    colored_formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s")

    # Stream handler pe stderr doar in modul debug
    # In modul normal log-urile merg doar in fisier (evita exit code 1 in PowerShell)
    if debug:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(colored_formatter)
        root_logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=15 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(plain_formatter)
    file_handler.addFilter(ascii_filter)
    if debug:
        stream_handler.addFilter(ascii_filter)

    try:
        from core.correlation_id import CorrelationIdFilter
        corr_filter = CorrelationIdFilter()
        file_handler.addFilter(corr_filter)
        if debug:
            stream_handler.addFilter(corr_filter)
    except ImportError:
        pass

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)


def _register_all_tools():
    """Inregistreaza TOATE tool-urile ANA in registry."""
    from tools.base import registry
    
    log_action("Starting tool registration process", {"registry": str(registry)})

    tool_modules = [
        ("tools.ana_context_tool", "AnaContextTool"),
        ("tools.files", "FilesTool"),
        ("tools.code", "CodeTool"),
        ("tools.web", "WebTool"),
        ("tools.system", "SystemTool"),
        ("tools.tool_healthcheck", "ToolHealthcheckTool"),
        ("tools.conversation_learning_tool", "ConversationLearningTool"),
        ("tools.session_log_miner_tool", "SessionLogMinerTool"),
        ("tools.session_checkpoint_tool", "SessionCheckpointTool"),
        ("tools.session_rem_sleep_tool", "SessionRemSleepTool"),
        ("tools.session_audit_tool", "SessionAuditTool"),
        ("tools.session_lifecycle_tool", "SessionLifecycleTool"),
        ("tools.memory_tool", "MemoryTool"),
        ("tools.privacy", "PrivacyTool"),
        ("tools.network_tool", "NetworkTool"),
        ("tools.security_tool", "SecurityTool"),
        ("tools.qa_tool", "QATool"),
        ("tools.smart_search_tool", "SmartSearchTool"),
        ("tools.debugger_tool", "DebuggerTool"),
        ("tools.codebase_understanding_tool", "CodebaseUnderstandingTool"),
        ("tools.browser_control", "BrowserControlTool"),
        ("tools.terminal_tool", "TerminalTool"),
        ("tools.file_patch_tool", "FilePatchTool"),
        ("tools.project_navigator_tool", "ProjectNavigatorTool"),
        ("tools.error_radar_tool", "ErrorRadarTool"),
        ("tools.tool_router_tool", "ToolRouterTool"),
        ("tools.code_context_pack_tool", "CodeContextPackTool"),
        ("tools.graph_context_pack_tool", "GraphContextPackTool"),
        ("tools.input_api_probe_tool", "InputApiProbeTool"),
        ("tools.binary_map_tool", "BinaryMapTool"),
        ("tools.todo_tool", "TodoWriteTool"),
        ("tools.edit_tool", "EditTool"),
        ("tools.system_optimization_tool", "SystemOptimizationTool"),
    ]

    optional_modules = [
        ("tools.autonomous_tool", "AutonomousTool"),
        ("tools.task_tool", "TaskTool"),
        ("tools.science_tool", "ScienceTool"),
        ("tools.web_ai_bridge", "WebAIBridgeTool"),
        ("tools.engineer_platform_tool", "EngineerPlatformTool"),
        ("tools.advanced_swarm_tool", "AdvancedSwarmTool"),
        ("tools.advanced_scanner", "AdvancedScannerTool"),
        ("tools.mitm_analyzer_tool", "MITMAnalyzerTool"),
        ("tools.network_pentest_tool", "NetworkPentestTool"),
        ("tools.hardware_scanner_tool", "HardwareScannerTool"),
        ("tools.verdent_tools", "BashExecTool"),
        ("tools.verdent_tools", "GlobSearchTool"),
        ("tools.verdent_tools", "GrepContentTool"),
        ("tools.verdent_tools", "GrepFileTool"),
        ("tools.verdent_tools", "WebFetchTool"),
    ]

    # Mobile tools (2026-05-12)
    new_tools = [
        ("tools.adb_tool", "ADBTool"),
        ("tools.frida_automation", "FridaTool"),
        ("tools.apk_analyzer", "APKAnalyzerTool"),
        ("tools.code_search", "CodeSearchTool"),
        ("tools.web_scraper", "WebScraperTool"),
    ]

    # AI Desktop Control tools (2026-05-13) - KILLER FEATURE
    desktop_tools = [
        ("tools.desktop_capture", "DesktopCaptureTool"),
        ("tools.live_desktop_viewer", "LiveDesktopViewerTool"),
        ("tools.desktop_control_tool", "DesktopControlTool"),
        ("tools.windows_insight_tool", "WindowsInsightTool"),
        ("tools.windows_uia_bridge", "WindowsUiaBridgeTool"),
        ("tools.window_manager", "WindowManagerTool"),
        ("tools.ocr_tool", "OcrTool"),
        ("tools.uia_click_tool", "UiaClickTool"),
        ("tools.uia_type_tool", "UiaTypeTool"),
        ("tools.foreground_ui_snapshot", "ForegroundUISnapshotTool"),  # NEW: Structural Eyes
        ("tools.workspace_situational_awareness", "WorkspaceSituationalAwarenessTool"),  # NEW: Structural Awareness
        ("tools.vision_region_capture_tool", "VisionRegionCaptureTool"),
        ("tools.vision_find_element_tool", "VisionFindElementTool"),
    ]

    # Live Tool Healer (2026-05-19) - intelligent supervision
    healing_tools = [
        ("tools.live_tool_healer", "LiveToolHealer"),
        ("tools.agent_coach_tool", "AgentCoachTool"),
    ]

    # Universal Tool Layer (2026-09-28) - Platform-agnostic tools for all coding agents
    universal_tools = [
        ("tools.terminal_monitor", "TerminalMonitorTool"),
        ("tools.universal_task_orchestrator", "UniversalTaskOrchestratorTool"),
        ("tools.auto_recovery", "AutoRecoveryTool"),
    ]

    # Enterprise System Intelligence (2026-09-28) - DLL injection & memory patching (Frida-based)
    system_intelligence_tools = [
        ("tools.dll_injection_tool", "DLLInjectionTool"),
        ("tools.memory_patching_tool", "MemoryPatchingTool"),
        ("tools.process_security_tool", "ProcessSecurityTool"),
        ("tools.network_protocol_tool", "NetworkProtocolTool"),
        ("tools.continual_learning_tool", "ContinualLearningTool"),
    ]

    # Voice tools (2026-05-14) - JARVIS STYLE
    voice_tools = [
        ("tools.edge_tts_voice", "EdgeTTSVoice"),  # Natural voice commentary
    ]
    runtime_agent = _build_runtime_agent()

    loaded = 0
    for module_path, class_name in tool_modules:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name}")
        except Exception as e:
            _print_tool_load(f"  [!] {class_name} skip: {e}")

    for module_path, class_name in optional_modules:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            if class_name in {"AutonomousTool", "TaskTool"}:
                tool_instance = tool_class(runtime_agent)
            else:
                tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (optional)")
        except Exception as e:
            logging.getLogger(__name__).warning("Optional tool skipped %s.%s: %s", module_path, class_name, e)

    # Incarca noile tool-uri (2026-05-12)
    for module_path, class_name in new_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (NEW)")
        except Exception as e:
            _print_tool_load(f"  [!] {class_name} skip: {e}")

    # Windows Deep Sight tool (2026-05-13)
    try:
        tool_class = _load_tool_class("tools.windows_deep_sight", "WindowsDeepSightTool")
        tool_instance = tool_class()
        registry.register(tool_instance)
        loaded += 1
        _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (GOD VIEW)")
    except Exception as e:
        logging.getLogger(__name__).warning("Deep Sight tool skipped: %s", e)

    # Incarca AI Desktop Control tools (2026-05-13)
    for module_path, class_name in desktop_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (DESKTOP CONTROL)")
        except Exception as e:
            logging.getLogger(__name__).warning("Desktop tool skipped %s.%s: %s", module_path, class_name, e)

    # Load Live Tool Healer (2026-05-19)
    for module_path, class_name in healing_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (INTELLIGENT SUPERVISION)")
        except Exception as e:
            logging.getLogger(__name__).warning("Healing tool skipped %s.%s: %s", module_path, class_name, e)

    # Incarca Voice tools (2026-05-14) - JARVIS STYLE
    for module_path, class_name in voice_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (JARVIS VOICE)")
        except Exception as e:
            logging.getLogger(__name__).warning("Voice tool skipped %s.%s: %s", module_path, class_name, e)

    # Load Universal Tool Layer (2026-09-28) - Platform-agnostic tools for all coding agents
    for module_path, class_name in universal_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (UNIVERSAL TOOL LAYER)")
        except Exception as e:
            logging.getLogger(__name__).warning("Universal tool skipped %s.%s: %s", module_path, class_name, e)

    # Load Enterprise System Intelligence (2026-09-28) - DLL injection & memory patching (Frida-based)
    for module_path, class_name in system_intelligence_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (ENTERPRISE SYSTEM INTELLIGENCE)")
        except Exception as e:
            logging.getLogger(__name__).warning("System intelligence tool skipped %s.%s: %s", module_path, class_name, e)

    # Ruflo-inspired: Vector Memory & Swarm (2026-05-19)
    advanced_tools = [
        ("tools.vector_memory_tool", "VectorMemoryTool"),  # Vector search 150x+ faster
        ("tools.swarm_tool", "SwarmTool"),  # Multi-agent swarm orchestration
    ]

    # UI-TARS inspired: Vision, Remote Control, Event Stream (2026-05-19)
    uitars_tools = [
        ("tools.vision_fallback_tool", "VisionFallbackTool"),  # Vision-based GUI fallback
        ("tools.remote_control_tool", "RemoteControlTool"),  # Remote machine control
        ("tools.event_stream_tool", "EventStreamTool"),  # Event stream debugging
    ]

    # Incarca Advanced tools (Vector Memory + Swarm) (2026-05-19)
    for module_path, class_name in advanced_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (RUFLO-INTEGRATION)")
        except Exception as e:
            logging.getLogger(__name__).warning("Advanced tool skipped %s.%s: %s", module_path, class_name, e)

    # Incarca UI-TARS tools (Vision, Remote, Event Stream) (2026-05-19)
    for module_path, class_name in uitars_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (UI-TARS-INTEGRATION)")
        except Exception as e:
            logging.getLogger(__name__).warning("UI-TARS tool skipped %s.%s: %s", module_path, class_name, e)

    # AI Core adapters (context_engine, proactive_interrupt, self_evolving,
    # memory_cortex, orchestrator, context_bridge, window_manager)
    try:
        from tools.tool_adapters import ANA_ADAPTER_CLASSES
        for AdapterClass in ANA_ADAPTER_CLASSES:
            try:
                instance = AdapterClass()
                registry.register(instance)
                loaded += 1
                _print_tool_load(f"  [OK] {instance.get_definition().name} (AI CORE)")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "AI Core adapter skipped %s: %s", AdapterClass.__name__, e
                )
    except ImportError as e:
        logging.getLogger(__name__).warning("tool_adapters.py nu a putut fi incarcat: %s", e)


    # PATCH_START v19_phase3
    try:
        from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

        class _V19RunTool(Tool):
            def __init__(self, module_path: str, name: str, description: str, parameters):
                self._module_path = module_path
                self._definition = ToolDefinition(
                    name=name,
                    description=description,
                    parameters=parameters,
                    category="diagnostics",
                    requires_confirmation=False,
                )

            def get_definition(self):
                return self._definition

            def execute(self, **kwargs):
                module = __import__(self._module_path, fromlist=["run"])
                result = module.run(dict(kwargs))
                if not isinstance(result, dict):
                    return ToolResult(status=ToolStatus.ERROR, error="diagnostic returned non-dict response")
                if result.get("success") is False:
                    return ToolResult(status=ToolStatus.ERROR, error=str(result.get("error") or "success=false"))
                return ToolResult(status=ToolStatus.SUCCESS, data=result, message=str(result.get("message", "ok")))

        v19_tools = [
            _V19RunTool(
                "tools.ana_runtime_inspector",
                "ana_runtime_inspector",
                "Read-only runtime snapshot and environment comparison diagnostics.",
                [
                    ToolParameter("action", "snapshot or compare_envs", "string", False, "snapshot"),
                    ToolParameter("dev_path", "Development workspace path for compare_envs", "string", False),
                    ToolParameter("release_path", "Release workspace path for compare_envs", "string", False),
                    ToolParameter("max_files", "Maximum files to compare", "integer", False, 5000),
                ],
            ),
            _V19RunTool(
                "tools.tool_contract_validator",
                "tool_contract_validator",
                "Read-only validation of safe tool response contracts.",
                [
                    ToolParameter("action", "validate_tool or validate_all", "string", False, "validate_all"),
                    ToolParameter("tool_name", "Tool name for validate_tool", "string", False),
                ],
            ),
            _V19RunTool(
                "tools.schema_diff",
                "schema_diff",
                "Read-only schema and response diff diagnostic.",
                [
                    ToolParameter("expected_schema", "Expected response schema", "object", True),
                    ToolParameter("actual_response", "Actual response object", "object", True),
                ],
            ),
        ]
        for tool_instance in v19_tools:
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (V19 DIAGNOSTICS)")
    except Exception as e:
        logging.getLogger(__name__).warning("v19 diagnostics skipped: %s", e)
    # PATCH_END v19_phase3

    # PATCH_START v20_phase2
    try:
        from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

        class _V20RunTool(Tool):
            def __init__(self, module_path: str, name: str, description: str, parameters):
                self._module_path = module_path
                self._definition = ToolDefinition(
                    name=name,
                    description=description,
                    parameters=parameters,
                    category="diagnostics",
                    requires_confirmation=False,
                )

            def get_definition(self):
                return self._definition

            def execute(self, **kwargs):
                module = __import__(self._module_path, fromlist=["run"])
                result = module.run(dict(kwargs))
                if not isinstance(result, dict):
                    return ToolResult(status=ToolStatus.ERROR, error="v20 tool returned non-dict response")
                if result.get("success") is False:
                    return ToolResult(status=ToolStatus.ERROR, error=str(result.get("error") or "success=false"))
                return ToolResult(status=ToolStatus.SUCCESS, data=result, message=str(result.get("message", "ok")))

        v20_tools = [
            _V20RunTool(
                "tools.v20.ana_health_check",
                "ana_health_check",
                "Manual read-only aggregate runtime health report.",
                [ToolParameter("include_contracts", "Include tool contract validation", "boolean", False, False)],
            ),
            _V20RunTool(
                "tools.v20.baseline_update_suggester",
                "baseline_update_suggester",
                "Suggest baseline updates without applying changes.",
                [
                    ToolParameter("baseline", "Expected baseline values", "object", False),
                    ToolParameter("current", "Current runtime values", "object", False),
                ],
            ),
            _V20RunTool(
                "tools.v20.docs_generator",
                "docs_generator",
                "Generate documentation text previews without writing files.",
                [
                    ToolParameter("document", "Optional generated document name", "string", False),
                    ToolParameter("generated_at", "Deterministic generated timestamp label", "string", False, "static-preview"),
                ],
            ),
            _V20RunTool(
                "tools.v20.ana_patch_suggester",
                "ana_patch_suggester",
                "Suggest patch diffs and risk without applying patches.",
                [
                    ToolParameter("issue", "Single issue descriptor", "object", False),
                    ToolParameter("issues", "Issue descriptor list", "array", False),
                ],
            ),
            _V20RunTool(
                "tools.v20.runtime_guard",
                "runtime_guard",
                "Manual read-only runtime consistency guard checks.",
                [ToolParameter("expected_root", "Expected repository root path", "string", False)],
            ),
            _V20RunTool(
                "dashboard.autonomy_dashboard",
                "autonomy_dashboard",
                "Render a read-only HTML dashboard for v20 autonomy outputs.",
                [ToolParameter("outputs", "Optional precomputed dashboard outputs", "object", False)],
            ),
        ]
        for tool_instance in v20_tools:
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (V20 FOUNDATION)")
    except Exception as e:
        logging.getLogger(__name__).warning("v20 foundation tools skipped: %s", e)
    # PATCH_END v20_phase2
    
    # Graph-based tool routing tools (inspired from self-healing-router GitHub)
    try:
        from tools.graph_tool_router import GraphToolRouterTool, GraphMetricsTool, GraphStatsTool
        for tool_class in [GraphToolRouterTool, GraphMetricsTool, GraphStatsTool]:
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (GRAPH ROUTING)")
    except Exception as e:
        logging.getLogger(__name__).warning("Graph routing tools skipped: %s", e)
    
    # Unlimited-OCR integration tools ("umplem tevile cu apa")
    try:
        from tools.unlimited_ocr_tool import UnlimitedOCRTool, UnlimitedOCRHealthTool, UnlimitedOCRStartTool
        for tool_class in [UnlimitedOCRTool, UnlimitedOCRHealthTool, UnlimitedOCRStartTool]:
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (UNLIMITED-OCR)")
    except Exception as e:
        logging.getLogger(__name__).warning("Unlimited-OCR tools skipped: %s", e)
    
    # System inspector tools ("vizibilitate sub capota")
    try:
        from tools.system_inspector_tool import SystemInspectorTool, SystemRepairTool
        for tool_class in [SystemInspectorTool, SystemRepairTool]:
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (SYSTEM INSPECTOR)")
    except Exception as e:
        logging.getLogger(__name__).warning("System inspector tools skipped: %s", e)
    
    # Project reader tools ("magia" - citeste tot proiectul)
    try:
        from tools.project_reader_tool import ProjectReaderTool, ProjectAnalyzerTool, ProjectSearchTool
        for tool_class in [ProjectReaderTool, ProjectAnalyzerTool, ProjectSearchTool]:
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (PROJECT READER)")
    except Exception as e:
        logging.getLogger(__name__).warning("Project reader tools skipped: %s", e)
    
    # Self-Evolving Garage: Auto-Fabricator de tool-uri live (2026-09-21)
    try:
        from tools.tool_factory import ToolFactoryTool
        tool_instance = ToolFactoryTool()
        registry.register(tool_instance)
        loaded += 1
        _print_tool_load(f"  [OK] {tool_instance.get_definition().name} (SELF-EVOLVING GARAGE)")
    except Exception as e:
        logging.getLogger(__name__).warning("ToolFactory skipped: %s", e)

    # Frontier Research Tools (2026-09-21)
    try:
        from tools.world_model_tool import WorldModelTool
        from tools.causal_engine_tool import CausalEngineTool
        from tools.neuromorphic_scheduler import NeuromorphicSchedulerTool
        from tools.speculative_executor import SpeculativeExecutorTool
        from tools.continual_learning_tool import ContinualLearningTool

        frontier_tools = [
            (WorldModelTool, "EMBODIED WORLD MODEL"),
            (CausalEngineTool, "CAUSAL REASONING"),
            (NeuromorphicSchedulerTool, "NEUROMORPHIC SCHEDULER"),
            (SpeculativeExecutorTool, "PREDICTIVE PRE-EXECUTION"),
            (ContinualLearningTool, "CONTINUAL LEARNING (LoRA)"),
        ]

        for ToolClass, label in frontier_tools:
            try:
                instance = ToolClass()
                registry.register(instance)
                loaded += 1
                _print_tool_load(f"  [OK] {instance.get_definition().name} ({label})")
            except Exception as inner_e:
                logging.getLogger(__name__).warning(f"Frontier tool {ToolClass.__name__} skipped: {inner_e}")
    except Exception as e:
        logging.getLogger(__name__).warning("Frontier tools skipped globally: %s", e)

    # Black Mesa Protocols (Extreme Labs 2026-09-21)
    try:
        from tools.latent_telepathy_tool import LatentTelepathyTool
        from tools.temporal_branching_tool import TemporalBranchingTool
        from tools.polymorphic_core_tool import PolymorphicCoreTool
        from tools.win32_telepathy_tool import Win32TelepathyTool
        
        black_mesa_tools = [
            (LatentTelepathyTool, "LATENT SPACE TELEPATHY"),
            (TemporalBranchingTool, "TEMPORAL BRANCHING"),
            (PolymorphicCoreTool, "POLYMORPHIC CORE"),
            (Win32TelepathyTool, "WIN32 GUI TELEPATHY"),
        ]
        for ToolClass, label in black_mesa_tools:
            try:
                instance = ToolClass()
                registry.register(instance)
                loaded += 1
                _print_tool_load(f"  [OK] {instance.get_definition().name} ({label})")
            except Exception as inner_e:
                logging.getLogger(__name__).warning(f"Black Mesa tool {ToolClass.__name__} skipped: {inner_e}")
    except Exception as e:
        logging.getLogger(__name__).warning("Black Mesa tools skipped globally: %s", e)

    # Aegis Protocols (Immune System 10/10)
    try:
        from tools.digital_immune_system import DigitalImmuneSystemTool
        instance = DigitalImmuneSystemTool()
        registry.register(instance)
        loaded += 1
        _print_tool_load(f"  [OK] {instance.get_definition().name} (DIGITAL IMMUNE SYSTEM)")
    except Exception as e:
        logging.getLogger(__name__).warning("Aegis tools skipped: %s", e)

    log_result(f"Tool registration completed: {loaded} tools loaded", success=True, context={"loaded": loaded})
    log_next_step("Starting MCP server with registered tools", priority="HIGH")

    
    return loaded
def _list_tools():
    """Afiseaza toate tool-urile disponibile."""
    from tools.base import registry

    tools = registry.list_tools()
    print(f"\n  Tool-uri ANA MAX ({len(tools)} disponibile):")
    print("  " + "-" * 50)
    for tool_name in sorted(tools):
        tool = registry.get(tool_name)
        if tool:
            definition = tool.get_definition()
            print(f"  - {tool_name}: {definition.description[:60]}")
        else:
            print(f"  - {tool_name}")
    print()


def _run_tests():
    """Teste rapide pe tool-uri."""
    from tools.base import registry

    print("\n  Teste rapide ANA MAX:")
    print("  " + "-" * 50)

    tests = [
        ("file_operations", {"operation": "list", "path": "."}),
        ("system_control", {"operation": "vitals"}),
    ]

    passed = 0
    failed = 0
    for tool_name, params in tests:
        try:
            result = registry.execute(tool_name, **params)
            status = "PASS" if result.is_success else "FAIL"
            if result.is_success:
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {tool_name}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {tool_name}: {e}")

    print(f"\n  Rezultat: {passed} PASS / {failed} FAIL\n")
    return failed == 0


def _start_mcp_server(host: str, port: int):
    """Porneste MCP server cu TOATE tool-urile expuse."""
    from flask import Flask, request, jsonify
    from tools.base import registry

    app = Flask(__name__)
    runtime = {"agent": None, "multi_agent": None}

    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    @app.after_request
    def add_local_cors_headers(response):
        """Allow local HTML demos to call the local MCP server (same-origin only)."""
        response.headers["Access-Control-Allow-Origin"] = response.headers.get("Origin", "http://127.0.0.1:8766")
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "false"
        return response

    @app.route('/', methods=['GET'])
    def index():
        return """<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ANA MAX - Professional MCP Server</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --accent: #8b5cf6;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --surface: rgba(15, 23, 42, 0.6);
        }
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            width: 95%;
            max-width: 1000px;
            margin: 40px auto;
            padding: 32px;
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 24px;
            border: 1px solid var(--glass-border);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.6s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            margin-top: 0;
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(to right, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        p.subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-bottom: 32px;
        }
        .grid {
            display: grid;
            gap: 24px;
            grid-template-columns: 1fr 1fr;
        }
        .full { grid-column: 1 / -1; }
        .card {
            padding: 24px;
            background: var(--surface);
            border-radius: 16px;
            border: 1px solid var(--glass-border);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        h2 {
            margin-top: 0;
            font-size: 1.25rem;
            color: #e2e8f0;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        pre {
            background: rgba(0, 0, 0, 0.3);
            color: #cbd5e1;
            padding: 16px;
            border-radius: 12px;
            overflow-x: auto;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #e2e8f0;
        }
        textarea {
            width: 100%;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0, 0, 0, 0.2);
            color: #f8fafc;
            padding: 16px;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            resize: vertical;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }
        button {
            margin-top: 16px;
            width: 100%;
            cursor: pointer;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border: none;
            color: white;
            font-weight: 700;
            font-size: 1.1rem;
            padding: 16px;
            border-radius: 12px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
        }
        button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        .footer {
            margin-top: 32px;
            color: var(--text-muted);
            font-size: 0.9rem;
            text-align: center;
            border-top: 1px solid var(--glass-border);
            padding-top: 16px;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ANA MAX</h1>
        <p class="subtitle">Professional MCP Server Dashboard</p>

        <div class="grid">
            <div class="card">
                <h2><span class="status-dot"></span> System Status</h2>
                <pre id="status">Connecting...</pre>
            </div>
            <div class="card">
                <h2>Endpoints</h2>
                <pre>/health
/tools
/mcp
/mcp/stream
/execute
</pre>
            </div>
            <div class="card full">
                <h2>Command Interface</h2>
                <label for="prompt">Execute Task or Query</label>
                <textarea id="prompt" rows="4" placeholder="Enter a task, command, or query...">System status check</textarea>
                <button id="send">Initialize Sequence</button>
            </div>
            <div class="card full">
                <h2>Execution Result</h2>
                <pre id="result">Awaiting input...</pre>
            </div>
        </div>

        <div class="footer">
            Powered by OS27 Intelligence &bull; Endpoint: <code>/mcp</code> (ana.execute_task)
        </div>
    </div>

    <script>
        async function loadStatus() {
            try {
                const resp = await fetch('/health');
                const health = await resp.json();
                document.getElementById('status').textContent = JSON.stringify(health, null, 2);
                document.querySelector('.status-dot').style.backgroundColor = '#10b981';
                document.querySelector('.status-dot').style.boxShadow = '0 0 10px #10b981';
            } catch (err) {
                document.getElementById('status').textContent = 'Error fetching status: ' + err;
                document.querySelector('.status-dot').style.backgroundColor = '#ef4444';
                document.querySelector('.status-dot').style.boxShadow = '0 0 10px #ef4444';
            }
        }

        async function sendPrompt() {
            const promptEl = document.getElementById('prompt');
            const resultEl = document.getElementById('result');
            const sendBtn = document.getElementById('send');
            const text = promptEl.value.trim();
            if (!text) return;
            
            sendBtn.disabled = true;
            sendBtn.textContent = 'Processing...';
            resultEl.textContent = 'Executing sequence. Please wait...';
            
            try {
                const resp = await fetch('/mcp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        jsonrpc: '2.0', id: Date.now(), method: 'ana.chat',
                        params: { message: text }
                    })
                });
                const data = await resp.json();
                
                if (data.error) {
                    resultEl.textContent = 'Error: ' + JSON.stringify(data.error, null, 2);
                } else if (data.result) {
                    if (typeof data.result === 'string') {
                        resultEl.textContent = data.result;
                    } else {
                        const res = data.result;
                        let out = '';
                        if (res.output) out += res.output + '\\n\\n';
                        if (res.response) out += res.response + '\\n\\n';
                        if (res.content) out += res.content + '\\n\\n';
                        out += 'Success: ' + (res.success === true);
                        if (res.completed_steps !== undefined && res.total_steps !== undefined) {
                            out += '\\nProgress: ' + res.completed_steps + '/' + res.total_steps;
                        }
                        if (res.elapsed_time !== undefined) {
                            out += '\\nElapsed: ' + (res.elapsed_time.toFixed ? res.elapsed_time.toFixed(2) : res.elapsed_time) + 's';
                        }
                        if (!res.success || (res.output && String(res.output).toLowerCase().startsWith('eroare'))) {
                            out += '\\n\\n[DETAILS]\\n' + JSON.stringify(res, null, 2);
                        }
                        resultEl.textContent = out || JSON.stringify(res, null, 2);
                    }
                } else {
                    resultEl.textContent = JSON.stringify(data, null, 2);
                }
            } catch (err) {
                resultEl.textContent = 'Request failed: ' + err;
            }
            
            sendBtn.disabled = false;
            sendBtn.textContent = 'Initialize Sequence';
        }

        document.getElementById('send').addEventListener('click', sendPrompt);
        document.getElementById('prompt').addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') sendPrompt();
        });
        
        loadStatus();
        setInterval(loadStatus, 10000);
    </script>
</body>
</html>
"""

    def _get_runtime_agent():
        # The launcher may intentionally pin a local backend (for example
        # ANA_BACKEND=foundry).  Keep the HTTP chat path aligned with startup
        # rather than silently reverting to settings.yaml.
        backend = os.environ.get("ANA_BACKEND") or config.get("ai.primary_backend", "gemini")
        backend = str(backend or "none").strip().lower()
        logging.getLogger(__name__).info("[AGENT] _get_runtime_agent backend=%s", backend)
        
        if backend == "none":
            logging.getLogger(__name__).warning("[AGENT] Backend is 'none', returning None")
            return None
        
        if runtime["agent"] is None:
            logging.getLogger(__name__).info("[AGENT] Creating new ANAAgent with backend=%s", backend)
            from core.agent import ANAAgent
            try:
                runtime["agent"] = ANAAgent(backend=backend)
                logging.getLogger(__name__).info("[AGENT] ANAAgent created successfully")
            except Exception as e:
                logging.getLogger(__name__).exception("[AGENT] Failed to create ANAAgent")
                return None
        else:
            logging.getLogger(__name__).info("[AGENT] Reusing existing agent")
            
        return runtime["agent"]

    @app.route('/events', methods=['GET'])
    def rest_events():
        """REST endpoint: returneaza evenimentele God View necitite."""
        try:
            ds = registry.get("windows_deep_sight")
            if ds and hasattr(ds, '_get_events'):
                # Access the internal method's logic
                events = []
                while not ds._event_queue.empty():
                    try:
                        events.append(ds._event_queue.get_nowait())
                    except Exception:
                        break
                return jsonify({"events": events, "count": len(events), "god_view": True})
        except Exception:
            pass
        return jsonify({"events": [], "count": 0, "god_view": False})

    voice_messages = []

    @app.route('/voice/push', methods=['POST'])
    def voice_push():
        data = request.json
        voice_messages.append(data)
        return jsonify({"status": "ok"})

    @app.route('/voice/poll', methods=['GET'])
    def voice_poll():
        if voice_messages:
            return jsonify(voice_messages.pop(0))
        return jsonify({})

    @app.route('/dashboard', methods=['GET'])
    def god_view_dashboard():
        """Serve the OS-27 God View Dashboard HTML."""
        dashboard_path = BASE_DIR / "dashboard" / "os27_dashboard.html"
        if dashboard_path.exists():
            return dashboard_path.read_text(encoding='utf-8')
        return "Dashboard HTML not found.", 404

    @app.route('/local_image')
    def serve_local_image():
        """Serve a local image from absolute path (e.g., screenshots)."""
        from flask import send_file
        path = request.args.get('path')
        if not path or not os.path.exists(path):
            return "File not found", 404
        return send_file(path)

    @app.route('/dashboard/stream', methods=['GET'])
    def dashboard_stream():
        """SSE stream for OS-27 Dashboard, hooked into watchdog_bus."""
        from flask import Response, stream_with_context
        from tools.watchdog_bus import bus
        import json
        import queue

        q = queue.Queue(maxsize=100)

        def _bus_subscriber(event):
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

        def generate():
            bus.subscribe(_bus_subscriber)
            try:
                while True:
                    try:
                        event = q.get(timeout=5)
                        yield f"data: {json.dumps(event)}\n\n"
                    except queue.Empty:
                        yield "data: {\"type\": \"ping\"}\n\n"
            finally:
                bus.unsubscribe(_bus_subscriber)

        return Response(stream_with_context(generate()),
                        mimetype='text/event-stream',
                        headers={
                            'Cache-Control': 'no-cache',
                            'X-Accel-Buffering': 'no',
                            'Connection': 'keep-alive'
                        })

    @app.route('/chat', methods=['GET'])
    def chat_ui():
        from flask import request
        backend = os.environ.get("ANA_BACKEND") or config.get("ai.primary_backend", "none")
        backend = str(backend or "none").strip().lower()
        is_openrouter = backend == "openrouter"
        is_foundry = backend == "foundry"
        if is_foundry:
            model_name = os.environ.get("FOUNDRY_MODEL", "qwen3.5-4b") + " via Foundry Local"
            sender_name = "ANA MAX (Foundry Local)"
        elif is_openrouter:
            model_name = "qwen/qwen3-coder via OpenRouter"
            sender_name = "ANA MAX (OpenRouter)"
        else:
            model_name = "Qwen 2.5 7B via Ollama"
            sender_name = "ANA MAX (Ollama)"
        port = request.host.split(':')[-1] if ':' in request.host else "8766"

        html = r"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ANA MAX - Enterprise Chat</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400&display=swap');
  :root {
    --bg-main: #0b0c10;
    --bg-panel: rgba(26, 28, 35, 0.7);
    --border: rgba(255, 255, 255, 0.08);
    --accent: #45f3ff;
    --accent-dim: rgba(69, 243, 255, 0.15);
    --text-primary: #e0e6ed;
    --text-sec: #8a94a6;
    --user-msg: rgba(69, 243, 255, 0.1);
    --ana-msg: rgba(30, 32, 40, 0.8);
    --error: #ff4a4a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg-main) radial-gradient(circle at 50% 0%, rgba(20, 30, 50, 0.8), var(--bg-main) 70%);
    color: var(--text-primary);
    height: 100vh;
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  header {
    background: rgba(11, 12, 16, 0.8);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px; display: flex; align-items: center; gap: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    z-index: 10;
  }
  header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: 1px; }
  header h1 span { color: var(--accent); }
  header .badge {
    background: var(--accent-dim); color: var(--accent);
    font-size: 0.75rem; padding: 4px 10px; border-radius: 20px;
    font-weight: 600; font-family: 'JetBrains Mono', monospace;
    border: 1px solid rgba(69, 243, 255, 0.3);
  }
  header .model { color: var(--text-sec); font-size: 0.85rem; margin-left: auto; font-family: 'JetBrains Mono', monospace; }
  
  #log {
    flex: 1; overflow-y: auto; padding: 24px;
    display: flex; flex-direction: column; gap: 16px;
    scroll-behavior: smooth;
  }
  .msg-wrapper { display: flex; flex-direction: column; max-width: 85%; animation: fadeIn 0.3s ease-out; }
  .msg-wrapper.user { align-self: flex-end; align-items: flex-end; }
  .msg-wrapper.ana { align-self: flex-start; align-items: flex-start; }
  .msg-wrapper.system { align-self: center; align-items: center; max-width: 90%; }
  
  .sender { font-size: 0.75rem; color: var(--text-sec); margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
  
  .msg {
    padding: 14px 20px; border-radius: 12px;
    line-height: 1.6; font-size: 0.95rem;
    white-space: pre-wrap; word-break: break-word;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  }
  .msg.user { background: var(--user-msg); border: 1px solid rgba(69, 243, 255, 0.2); border-bottom-right-radius: 4px; color: #fff; }
  .msg.ana { background: var(--ana-msg); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
  .msg.system { background: rgba(0,0,0,0.4); border: 1px solid var(--border); font-size: 0.8rem; color: var(--text-sec); border-radius: 20px; padding: 8px 16px; text-align: center; }
  .msg.error { background: rgba(255, 74, 74, 0.1); border: 1px solid var(--error); color: var(--error); }
  
  .thinking { display: flex; gap: 4px; padding: 4px 0; }
  .thinking span { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; }
  .thinking span:nth-child(1) { animation-delay: -0.32s; }
  .thinking span:nth-child(2) { animation-delay: -0.16s; }
  @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  
  footer {
    padding: 20px 24px; background: rgba(11, 12, 16, 0.85); backdrop-filter: blur(10px);
    border-top: 1px solid var(--border); display: flex; gap: 12px; align-items: flex-end;
  }
  .input-wrap { flex: 1; position: relative; }
  #inp {
    width: 100%; background: var(--bg-panel); border: 1px solid var(--border);
    color: var(--text-primary); border-radius: 12px; padding: 14px 16px;
    font-size: 0.95rem; font-family: inherit; resize: none;
    height: 52px; max-height: 150px; outline: none; transition: all 0.3s;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
  }
  #inp:focus { border-color: var(--accent); box-shadow: inset 0 2px 4px rgba(0,0,0,0.2), 0 0 10px var(--accent-dim); }
  #btn {
    background: var(--accent); color: #000; border: none; border-radius: 12px;
    padding: 0 24px; height: 52px; font-size: 1rem; font-weight: 700;
    cursor: pointer; transition: all 0.2s; white-space: nowrap;
    box-shadow: 0 4px 15px var(--accent-dim);
  }
  #btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(69, 243, 255, 0.3); }
  #btn:disabled { background: var(--border); color: var(--text-sec); cursor: not-allowed; transform: none; box-shadow: none; }
  
  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
</head>
<body>
<header>
  <h1>ANA <span>MAX</span></h1>
  <span class="badge">ENTERPRISE</span>
  <span class="model">""" + model_name + """</span>
</header>
<div id="log"></div>
<footer>
  <div class="input-wrap">
    <textarea id="inp" placeholder="Descrie task-ul tau (Enter = trimite, Shift+Enter = linie noua)..."></textarea>
  </div>
  <button id="btn">Trimite</button>
</footer>
<script>
const log = document.getElementById('log');
const inp = document.getElementById('inp');
const btn = document.getElementById('btn');
let activeThinkingWrapper = null;

// Load tools count
async function loadToolsCount() {
  try {
    const res = await fetch('/tools');
    const data = await res.json();
    const count = data.count || 0;
    const badge = document.querySelector('.badge');
    if (badge) {
      badge.textContent = `ENTERPRISE - ${count} TOOLS`;
    }
  } catch (e) {
    console.error('Failed to load tools count:', e);
  }
}

loadToolsCount();
setInterval(loadToolsCount, 30000);

const evtSource = new EventSource("/dashboard/stream");
evtSource.onmessage = function(event) {
  try {
    const ev = JSON.parse(event.data);
    if (ev.source === "OllamaLive" || ev.type === "LLM_LOG") {
      let text = typeof ev.data === 'string' ? ev.data : JSON.stringify(ev.data);
      if (text.indexOf('[') === 0) {
        const bracketEnd = text.indexOf(']');
        if (bracketEnd !== -1) {
          text = text.substring(bracketEnd + 1).trim();
        }
      }
      if (text === "Inference started" || text.startsWith("Done (")) return;
      
      if (btn.disabled && activeThinkingWrapper) {
         const contentDiv = activeThinkingWrapper.querySelector('.stream-content');
         if (contentDiv) {
             contentDiv.style.display = 'block';
             const loaders = activeThinkingWrapper.querySelector('.thinking');
             if(loaders) loaders.style.display = 'none';
             contentDiv.innerHTML += escHtml(text);
             log.scrollTop = log.scrollHeight;
         }
      }
    }
  } catch(e) {}
};

function addMsgWrapper(role, senderName) {
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper ' + role;
  if(senderName) {
    const sender = document.createElement('div');
    sender.className = 'sender';
    sender.textContent = senderName;
    wrapper.appendChild(sender);
  }
  const msg = document.createElement('div');
  msg.className = 'msg ' + role;
  wrapper.appendChild(msg);
  log.appendChild(wrapper);
  log.scrollTop = log.scrollHeight;
  return { wrapper, msg };
}

function addSystemMsg(text) {
  const { msg } = addMsgWrapper('system', null);
  msg.innerHTML = text;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').split('\\n').join('<br>');
}

async function sendMsg() {
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  inp.style.height = '52px';
  btn.disabled = true;

  const { msg: userMsg } = addMsgWrapper('user', 'Tu');
  userMsg.textContent = text;

  const { wrapper: anaWrapper, msg: anaMsg } = addMsgWrapper('ana', 'ANA MAX');
  activeThinkingWrapper = anaWrapper;
  anaMsg.innerHTML = '<div class="thinking"><span></span><span></span><span></span></div><div class="stream-content" style="display:none; color:#45f3ff; font-family: monospace; font-size: 0.85rem;"></div>';

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 360000); 

    const resp = await fetch('/mcp', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        jsonrpc: '2.0', id: Date.now(), method: 'ana.chat',
        params: { message: text }
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if(!resp.ok) {
        throw new Error(`HTTP Eroare: ${resp.status}`);
    }
    
    const data = await resp.json();
    let answer = '';
    
    if (data.result) {
      if (typeof data.result === 'string') answer = data.result;
      else if (data.result.response) answer = data.result.response;
      else if (data.result.output) answer = data.result.output;
      else if (data.result.content) answer = data.result.content;
      else answer = JSON.stringify(data.result, null, 2);
    } else if (data.error) {
      anaMsg.className = 'msg error';
      anaMsg.innerHTML = escHtml(JSON.stringify(data.error));
      btn.disabled = false;
      activeThinkingWrapper = null;
      return;
    }
    
    anaMsg.innerHTML = escHtml(answer);
  } catch(e) {
    anaMsg.className = 'msg error';
    if(e.name === 'AbortError') {
        anaMsg.innerHTML = 'Timpul de raspuns a expirat. Backend-ul ar putea fi oprit sau suprasolicitat.';
    } else {
        anaMsg.innerHTML = 'Eroare de conexiune: ' + escHtml(String(e.message || e));
    }
  }
  
  btn.disabled = false;
  activeThinkingWrapper = null;
  log.scrollTop = log.scrollHeight;
  inp.focus();
}

btn.addEventListener('click', sendMsg);
inp.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { 
    e.preventDefault(); 
    if(!btn.disabled) sendMsg(); 
  }
});
inp.addEventListener('input', () => {
  inp.style.height = '52px';
  inp.style.height = Math.min(inp.scrollHeight, 150) + 'px';
});

setInterval(async () => {
  try {
    const res = await fetch('/voice/poll');
    const data = await res.json();
    if (data && data.user) {
      const { msg: uMsg } = addMsgWrapper('user', 'Tu (Microfon)');
      uMsg.textContent = data.user;
      const { msg: aMsg } = addMsgWrapper('ana', 'ANA MAX');
      aMsg.textContent = data.ana;
    }
  } catch (e) {}
}, 1500);

addSystemMsg('Conexiune stabilita &bull; ' + '""" + model_name + """' + ' &bull; Sistem Securizat');
</script>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route('/health', methods=['GET'])
    def health():
        try:
            from core.agent import ANAAgent
            # Try to get the global agent instance if it exists
            agent_instance = globals().get('agent')
        except:
            agent_instance = None

        tools = registry.list_tools()
        backend = os.environ.get("ANA_BACKEND", "none")
        model = os.environ.get("FOUNDRY_MODEL") or os.environ.get("OLLAMA_MODEL") or os.environ.get("GEMINI_MODEL") or "unknown"
        
        return jsonify({
            "status": "online",
            "agent": "A.N.A. MAX",
            "version": "18.0-MAX",
            "tools_count": len(tools),
            "tools": sorted(tools),
            "mcp_ready": True,
            "vscode_agent": _is_vscode_agent_session(),
            "output_profile": "compact" if _compact_agent_output() else "normal",
            "active_backend": backend,
            "active_model": model,
        })

    @app.route('/api/reload-dashboard-feeder', methods=['POST'])
    def reload_dashboard_feeder():
        """Reload the active dashboard feeder during development."""
        try:
            import importlib

            module_name = "dashboard.dashboard_data_feeder_v2"
            feeder_module = importlib.import_module(module_name)
            
            # Stop existing feeder instance if running
            if hasattr(feeder_module, '_feeder_instance') and feeder_module._feeder_instance:
                feeder_module._feeder_instance.stop()
                feeder_module._feeder_instance = None
            
            # Reload module
            feeder_module = importlib.reload(feeder_module)
            
            # Start new feeder instance
            feeder_module.start_feeder()

            return jsonify({"success": True, "message": "Active dashboard feeder reloaded"}), 200
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to reload active dashboard feeder: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/tools', methods=['GET'])
    def list_tools_endpoint():
        tools = registry.list_tools()
        tool_list = []
        for name in sorted(tools):
            tool = registry.get(name)
            if tool:
                definition = tool.get_definition()
                tool_list.append({
                    "name": name,
                    "description": definition.description,
                    "category": definition.category,
                    "parameters": definition.to_dict().get("parameters", {})
                })
        return jsonify({"tools": tool_list, "count": len(tool_list)})

    @app.route('/execute', methods=['POST'])
    def execute_tool():
        data = request.json
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        tool_name = data.get("tool")
        params = data.get("args") or data.get("params") or {}

        if not tool_name:
            return jsonify({"error": "Missing 'tool' field"}), 400

        try:
            logging.getLogger(__name__).info(
                "HTTP /execute tool=%s args=%s",
                tool_name,
                list(params.keys()),
            )
            result = registry.execute(tool_name, **params)
            logging.getLogger(__name__).info(
                "HTTP /execute done tool=%s success=%s",
                tool_name,
                result.is_success,
            )
            return jsonify({
                "success": result.is_success,
                "data": result.data if result.is_success else None,
                "message": result.message,
                "error": result.error
            })
        except Exception as e:
            logging.getLogger(__name__).exception("HTTP /execute failed tool=%s", tool_name)
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/mcp', methods=['GET', 'POST', 'OPTIONS'])
    def mcp_handler():
        """MCP JSON-RPC endpoint - suporta si GET pentru health check."""
        if request.method == 'OPTIONS':
            return ("", 204)

        if request.method == 'GET':
            return jsonify({
                "status": "mcp_online",
                "server": "A.N.A. MAX",
                "version": "18.0-MAX",
                "endpoints": ["/mcp (POST)"]
            })

        data = request.json
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id', 1)

        try:
            logging.getLogger(__name__).info("HTTP /mcp method=%s id=%s", method, request_id)
            if method and str(method).startswith("notifications/"):
                logging.getLogger(__name__).info("HTTP /mcp notification accepted method=%s", method)
                return jsonify({"jsonrpc": "2.0", "id": request_id, "result": None})

            if method == "initialize":
                tools = registry.list_tools()
                logging.getLogger(__name__).info("HTTP /mcp initialize tools=%s", len(tools))
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "A.N.A. MAX", "version": "18.0-MAX"},
                        "capabilities": {"tools": {}, "resources": {}},
                        "tools_count": len(tools)
                    }
                })

            elif method == "tools/list":
                tools = registry.list_tools()
                tool_list = []
                for name in sorted(tools):
                    tool = registry.get(name)
                    if tool:
                        definition = tool.get_definition()
                        schema = definition.get_ollama_format()
                        tool_list.append({
                            "name": name,
                            "description": definition.description,
                            "inputSchema": schema.get("function", {}).get("parameters", {})
                        })
                logging.getLogger(__name__).info("HTTP /mcp tools/list count=%s", len(tool_list))
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tool_list}
                })

            elif method == "resources/list":
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": []},
                })

            elif method == "resources/templates/list":
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resourceTemplates": []},
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if not tool_name:
                    return jsonify({"jsonrpc": "2.0", "id": request_id,
                                    "error": {"code": -32602, "message": "Missing tool name"}}), 400

                # Loop Detection Check - DISABLED
                # # Get agent from globals (set during _build_runtime_agent)
                # agent_instance = globals().get("agent")
                # if agent_instance and hasattr(agent_instance, '_check_loop_detection'):
                #     is_loop, reason = agent_instance._check_loop_detection(tool_name, arguments)
                #     if is_loop:
                #         logging.getLogger(__name__).warning(
                #             "HTTP /mcp tools/call LOOP DETECTED name=%s reason=%s",
                #             tool_name,
                #             reason,
                #         )
                #         return jsonify({
                #             "jsonrpc": "2.0",
                #             "id": request_id,
                #             "result": {
                #                 "content": [{
                #                     "type": "text",
                #                     "text": json.dumps({
                #                         "success": False,
                #                         "error": f"Loop detection: {reason}",
                #                         "message": "Tool call blocked to prevent infinite loop"
                #                     }, indent=2)
                #                 }]
                #             }
                #         })

                #     # Record the tool call
                #     agent_instance._record_tool_call(tool_name, arguments)

                logging.getLogger(__name__).info(
                    "HTTP /mcp tools/call start name=%s id=%s args=%s",
                    tool_name,
                    request_id,
                    list(arguments.keys()),
                )
                result = registry.execute(tool_name, **arguments)
                payload = {
                    "success": result.is_success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                }
                if isinstance(result.data, dict) and isinstance(result.data.get("guidance_summary"), dict):
                    payload["guidance_summary"] = result.data["guidance_summary"]
                logging.getLogger(__name__).info(
                    "HTTP /mcp tools/call end name=%s id=%s success=%s",
                    tool_name,
                    request_id,
                    result.is_success,
                )
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps(payload, indent=2, default=str)
                        }]
                    }
                })

            elif method == "ana.execute_task":
                task_desc = params.get("task") or params.get("query") or ""
                if not task_desc:
                    return jsonify({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Missing task"},
                    }), 400

                try:
                    agent = _get_runtime_agent()

                    if agent is None:
                        return jsonify({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "output": (
                                    "ANA MAX ruleaza in modul tools-only. "
                                    "Backend-ul AI intern este dezactivat in settings.yaml "
                                    "(ai.primary_backend: none). "
                                    "Pentru rationament intern seteaza gemini, hybrid sau alt backend suportat."
                                ),
                                "success": True,
                            }
                        })

                    if runtime["multi_agent"] is None:
                        try:
                            from core.multi_agent_system import get_multi_agent_system

                            runtime["multi_agent"] = get_multi_agent_system(agent)
                        except Exception:
                            runtime["multi_agent"] = False

                    if runtime["multi_agent"]:
                        result = runtime["multi_agent"].execute_with_audit(task_desc)
                        return jsonify({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result if isinstance(result, dict) else {"output": str(result), "success": True},
                        })

                    planner_cfg = config.get("planner", {}) or {}
                    planner_enabled = bool(planner_cfg.get("enabled", True))
                    prefer_tools = bool(planner_cfg.get("prefer_tools_over_llm", True))

                    planner_result = None
                    planner_cfg_fallback_error = ""
                    if planner_enabled and prefer_tools:
                        try:
                            from core.memory_cortex import get_memory_cortex
                            from core.context_bridge import get_context_bridge
                            from core.planner import get_planner

                            mem_cfg = config.get("memory_cortex", {}) or {}
                            ctx_cfg = config.get("context_bridge", {}) or {}

                            memory = get_memory_cortex(mem_cfg)
                            if bool(mem_cfg.get("write_episodic", True)):
                                memory.record_event("task_started", {"task": task_desc, "source": "mcp_ana_execute_task", "request_id": request_id})

                            bridge = get_context_bridge(ctx_cfg)
                            include_mem = bool(ctx_cfg.get("include_memory_hits", True))
                            context = bridge.build_context(task_desc, memory_cortex=memory if include_mem else None)

                            planner = get_planner(planner_cfg)
                            planner_result = planner.execute_task(
                                task_desc,
                                context_snapshot=context,
                                memory_state={"memory_enabled": bool(mem_cfg.get("enabled", True))},
                            )

                            try:
                                tid = planner_result.get("task_id") or f"req_{request_id}"
                                memory.set_task_state(tid, {
                                    "task_desc": task_desc,
                                    "status": "success" if planner_result.get("success") else "failed",
                                    "planner_result": planner_result,
                                    "request_id": request_id,
                                })
                                if bool(mem_cfg.get("write_episodic", True)):
                                    memory.record_event(
                                        "task_finished",
                                        {
                                            "task": task_desc,
                                            "task_id": tid,
                                            "success": bool(planner_result.get("success")),
                                            "errors": planner_result.get("errors"),
                                            "request_id": request_id,
                                        },
                                    )
                            except Exception:
                                pass
                        except Exception as exc:
                            logging.getLogger(__name__).exception("Planner pipeline failed; falling back to agent.send_message")
                            planner_result = None
                            planner_cfg_fallback_error = f"[planner-pipeline-failed:{exc}]"
                    else:
                        planner_cfg_fallback_error = ""

                    if planner_result is not None:
                        output_text = str(planner_result.get("output") or "")
                        if planner_cfg_fallback_error:
                            output_text = planner_cfg_fallback_error + " " + output_text
                        return jsonify({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "output": output_text[:4000],
                                "success": bool(planner_result.get("success")),
                                "steps": planner_result.get("steps", []),
                                "errors": planner_result.get("errors", []),
                                "task_id": planner_result.get("task_id"),
                                "engine": "ana_planner",
                            }
                        })

                    response_text = agent.send_message(task_desc)
                except Exception as e:
                    logging.getLogger(__name__).exception("ana.execute_task failed")
                    response_text = f"ANA execute_task failed safely: {e}"

                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "output": response_text[:4000] if response_text else "",
                        "success": not response_text.startswith("ANA execute_task failed safely:"),
                    }
                })

            elif method == "ana.chat":
                message = params.get("message") or params.get("task") or ""
                logging.getLogger(__name__).info("[CHAT] ana.chat received message='%s' id=%s", message[:50], request_id)
                
                if not message:
                    logging.getLogger(__name__).warning("[CHAT] ana.chat missing message")
                    return jsonify({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Missing message"},
                    }), 400

                # Voice command hook: detecteaza "activeaza/opreste vocea" si
                # executa direct, fara sa mai treaca prin LLM (raspuns instant).
                try:
                    voice_cmd = detect_voice_command(message)
                    logging.getLogger(__name__).info("[CHAT] Voice command detected: %s", voice_cmd)
                except Exception as e:
                    logging.getLogger(__name__).exception("[CHAT] Voice command detection failed")
                    voice_cmd = None
                    
                if voice_cmd:
                    logging.getLogger(__name__).info("[CHAT] Handling voice command: %s", voice_cmd)
                    vc_result = handle_voice_command(voice_cmd, message)
                    return jsonify({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "output": vc_result.get("output", ""),
                            "success": bool(vc_result.get("success")),
                            "voice_command": voice_cmd,
                        }
                    })

                try:
                    logging.getLogger(__name__).info("[CHAT] Getting runtime agent...")
                    agent = _get_runtime_agent()
                    if agent is None:
                        logging.getLogger(__name__).error("[CHAT] Runtime agent is None")
                        return jsonify({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {"output": "Internal AI backend is disabled.", "success": False}
                        })
                    
                    logging.getLogger(__name__).info("[CHAT] Agent found, sending message...")
                    response_text = agent.send_message(message)
                    logging.getLogger(__name__).info("[CHAT] Agent response received, length=%d", len(response_text))
                except Exception as e:
                    logging.getLogger(__name__).exception("[CHAT] ana.chat failed with exception")
                    response_text = f"ANA chat failed safely: {e}"

                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "output": response_text,
                        "success": not response_text.startswith("ANA chat failed safely:"),
                    }
                })

            elif method == "ana.ping":
                return jsonify({"jsonrpc": "2.0", "id": request_id, "result": "pong"})

            else:
                return jsonify({"jsonrpc": "2.0", "id": request_id,
                                "error": {"code": -32601, "message": f"Method not found: {method}"}}), 404

        except Exception as e:
            return jsonify({"jsonrpc": "2.0", "id": request_id,
                            "error": {"code": -32603, "message": str(e)}}), 500

    @app.route('/mcp/stream', methods=['GET'])
    def mcp_stream():
        """SSE endpoint pentru God View live streaming."""
        from flask import Response, stream_with_context
        import json

        def generate():
            import time as _time
            _time.sleep(0.2)

            # Incearca subscribe la God View events
            ds = None
            sub_q = None
            try:
                ds = registry.get("windows_deep_sight")
                if ds and hasattr(ds, 'subscribe_events'):
                    sub_q = ds.subscribe_events()
            except Exception:
                pass

            try:
                yield "event: connected\ndata: {\"status\":\"ok\",\"god_view\":" + json.dumps(sub_q is not None) + "}\n\n"

                if sub_q:
                    # Stream live events from God View
                    while True:
                        try:
                            event = sub_q.get(timeout=5)
                            yield f"event: event\ndata: {json.dumps(event, default=str)}\n\n"
                        except Exception:
                            yield "event: heartbeat\ndata: {}\n\n"
                else:
                    # No God View - just keep connection alive
                    while True:
                        yield "event: heartbeat\ndata: {}\n\n"
                        _time.sleep(10)
            finally:
                if ds and sub_q and hasattr(ds, 'unsubscribe_events'):
                    try:
                        ds.unsubscribe_events(sub_q)
                    except Exception:
                        pass

        return Response(stream_with_context(generate()),
                        mimetype='text/event-stream',
                        headers={
                            'Cache-Control': 'no-cache',
                            'X-Accel-Buffering': 'no',
                            'Connection': 'keep-alive'
                        })

    print(f"\n  MCP Server: http://{host}:{port}")
    stealth = config.get("mcp.stealth_mode", True)
    if stealth:
        print(f"\n  ANA MAX running on http://{host}:{port}\n")
    else:
        print(f"\n  Health:     http://{host}:{port}/health")
        print(f"  Tools:      http://{host}:{port}/tools")
        print(f"  Execute:    POST http://{host}:{port}/execute")
        print(f"  MCP:        POST http://{host}:{port}/mcp")
        print(f"\n  Ctrl+C pentru oprire.\n")

    # Mod stealth - ascunde banner Flask
    if stealth:
        import werkzeug.serving
        werkzeug.serving.run_with_reloader = lambda f: f
        # Seteaza banner fals daca e configurat
        fake_banner = config.get("mcp.fake_banner", "")
        if fake_banner and not getattr(app, '_banner_patched', False):
            original_wsgi_app = app.wsgi_app
            app.wsgi_app = lambda environ, start_response: environ.update({'SERVER_SOFTWARE': fake_banner}) or original_wsgi_app(environ, start_response)
            app._banner_patched = True

    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


def main() -> int:
    import sys, os, tempfile
    if sys.platform == 'win32':
        import msvcrt
        lock_file = os.path.join(tempfile.gettempdir(), "ana_max_os27.lock")
        try:
            lock_fd = open(lock_file, 'w')
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            global _ana_max_lock
            _ana_max_lock = lock_fd
        except Exception:
            print("\n  [!] EROARE CRITICA: O alta instanta de ANA MAX ruleaza deja!")
            print("  [!] Protectie activa: Multi-session dezactivat pentru a preveni supraincarcarea (arderea) PC-ului.")
            print("  [!] Inchideti cealalta fereastra si incercati din nou.\n")
            import time; time.sleep(5)
            sys.exit(1)

    # Fix pentru UnicodeEncodeError pe Windows terminal
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    args = _build_parser().parse_args()
    _configure_logging(args.debug)
    agent_session = _is_vscode_agent_session()
    if agent_session:
        logging.getLogger(__name__).info("VS Code agent session detected; compact output enabled")
    else:
        _print_banner()

    # Creeaza directoare necesare
    for d in ["logs", "memory", "backups", "generated_bots"]:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)

    # Inregistreaza TOATE tool-urile
    if agent_session:
        print("ANA MAX: loading tools")
    else:
        print("\n  Incarcare tool-uri...")
    loaded = _register_all_tools()
    if agent_session:
        print(f"ANA MAX: {loaded} tools loaded")
    else:
        print(f"  {loaded} tool-uri incarcate.\n")

    if args.list_tools:
        _list_tools()
        return 0

    if args.test:
        success = _run_tests()
        return 0 if success else 1

    # Porneste MCP Server
    host = args.host or config.get("mcp.host", "127.0.0.1")
    port = args.port or config.get("mcp.port", 8765)

    # Initialize Watchdog if requested (or default enabled if we want)
    watchdog = None
    # We can default it to True, but lets start it unconditionally or based on a config
    # For OS-23 we start it.
    import os
    watchdog = WorkspaceWatchdog(
        watch_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        event_stream=get_event_stream()
    )
    watchdog.start()

    telemetry = NativeTelemetry(
        event_stream=get_event_stream(),
        target_process="explorer.exe" # User-mode bypass
    )
    telemetry.start()

    # OS-23 / OS-25 Autonomous Telemetry Engine Start
    try:
        from tools.watchdog_bus import bus
        bus.start()
        
        # Add console logger subscriber for debugging
        from tools.watchdog_bus import _console_logger_subscriber
        bus.subscribe(_console_logger_subscriber)
        
        from tools.reflex_core import reflex_engine
        reflex_engine.start()

        from tools.ollama_live_logger import OllamaLiveLoggerTool
        ollama_logger = OllamaLiveLoggerTool()
        ollama_result = ollama_logger.execute("start")
        if ollama_result.status.name == "SUCCESS":
            print(f"  [OK] Ollama live logger: {ollama_result.message}")
        else:
            print(f"  [!] Ollama live logger degraded: {ollama_result.error or ollama_result.message}")
            bus.publish(
                "OllamaLive",
                "LLM_LOG",
                f"Ollama logger startup degraded: {ollama_result.error or ollama_result.message}",
            )

        from tools.windows_frida_telemetry import WindowsFridaTelemetryTool
        frida_tool = WindowsFridaTelemetryTool()
        frida_tool.execute("start", target="notepad.exe")
        
        # Start Dashboard Data Feeder (populate dashboard with live system metrics)
        from dashboard.dashboard_data_feeder_v2 import start_feeder
        from core.omnisense import start_omnisense
        start_feeder()
        start_omnisense()
        
        print("  [OK] OS-27 Telemetry Engine started (Bus, Reflex Core, Ollama Logger, Frida, Dashboard Feeder)")
    except Exception as e:
        print(f"  [!] Failed to start OS-23 telemetry: {e}")

    try:
        _start_mcp_server(host, port)
    except KeyboardInterrupt:
        print("\n  ANA MAX oprita.")
    except Exception as e:
        print(f"\n  Eroare: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if watchdog:
            watchdog.stop()
        if telemetry:
            telemetry.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
