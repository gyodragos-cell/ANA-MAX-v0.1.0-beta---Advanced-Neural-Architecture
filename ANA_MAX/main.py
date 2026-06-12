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
from pathlib import Path
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace
from dotenv import load_dotenv


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

config.load(str(CONFIG_PATH))


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
    from core.memory import get_memory

    backend = config.get("ai.primary_backend", "none")
    try:
        agent = ANAAgent(backend=backend)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Falling back to tools-only ANAAgent during tool registration: %s",
            exc,
        )
        agent = ANAAgent(backend="none")

    agent.memory = get_memory()
    agent.session_id = getattr(agent, "_session_id", "ana_http")
    agent.engineer_platform = SimpleNamespace(workspace_root=BASE_DIR)
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

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Stream handler pe stderr doar in modul debug
    # In modul normal log-urile merg doar in fisier (evita exit code 1 in PowerShell)
    if debug:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=15 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)


def _register_all_tools():
    """Inregistreaza TOATE tool-urile ANA in registry."""
    from tools.base import registry

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
        """Allow local HTML demos to call the local MCP server."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.route('/', methods=['GET'])
    def index():
        return """<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="utf-8" />
    <title>ANA MAX - MCP Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #121212; color: #f5f5f5; }
        .container { max-width: 900px; margin: 24px auto; padding: 24px; background: #1c1c1c; border-radius: 12px; box-shadow: 0 0 32px rgba(0,0,0,.45); }
        h1, h2 { margin-top: 0; color: #f1c40f; }
        pre { background: #0f1720; color: #d8dee9; padding: 12px; border-radius: 8px; overflow-x: auto; }
        label { display: block; margin-bottom: 8px; font-weight: 600; }
        input, textarea, button { width: 100%; border-radius: 8px; border: 1px solid #333; background: #0f1720; color: #f5f5f5; padding: 12px; box-sizing: border-box; }
        button { cursor: pointer; background: #2563eb; border: none; color: white; font-weight: 700; }
        button:hover { background: #1d4ed8; }
        .grid { display: grid; gap: 16px; grid-template-columns: 1fr 1fr; }
        .full { grid-column: 1 / -1; }
        .card { padding: 16px; background: #111827; border-radius: 12px; border: 1px solid #2d3748; }
        .footer { margin-top: 16px; color: #94a3b8; font-size: 0.93rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>ANA MAX - MCP Server</h1>
        <p>Acesta este un panou simplu de stare pentru <strong>ANA MAX</strong>. Foloseste comanda de mai jos ca un punct de plecare pentru conversatie si executia de task-uri.</p>

        <div class="grid">
            <div class="card">
                <h2>Status</h2>
                <pre id="status">Incarcare...</pre>
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
                <h2>Trimite o intrebare</h2>
                <label for="prompt">Task / intrebare</label>
                <textarea id="prompt" rows="5" placeholder="Scrie un task sau o comanda...">Salut, verifica starea sistemului.</textarea>
                <button id="send">Trimite</button>
            </div>
            <div class="card full">
                <h2>Rezultat</h2>
                <pre id="result">Trimite un task pentru a vedea raspunsul.</pre>
            </div>
        </div>

        <div class="footer">Acest UI local foloseste endpoint-ul <code>/mcp</code> cu metoda <code>ana.execute_task</code>.</div>
    </div>

    <script>
        async function loadStatus() {
            try {
                const resp = await fetch('/health');
                const health = await resp.json();
                document.getElementById('status').textContent = JSON.stringify(health, null, 2);
                if (data.error) {
                    result.textContent = 'Eroare: ' + JSON.stringify(data.error, null, 2);
                } else if (data.result) {
                    // If result is plain string, show it
                    if (typeof data.result === 'string') {
                        result.textContent = data.result;
                        return;
                    }

                    // Show structured output if present
                    const res = data.result;
                    let out = '';
                    if (res.output) out += res.output + '\n\n';
                    out += `Success: ${res.success === true}`;
                    if (typeof res.completed_steps !== 'undefined' && typeof res.total_steps !== 'undefined') {
                        out += `\nProgress: ${res.completed_steps}/${res.total_steps}`;
                    }
                    if (typeof res.elapsed_time !== 'undefined') {
                        out += `\nElapsed: ${res.elapsed_time.toFixed ? res.elapsed_time.toFixed(2) : res.elapsed_time}s`;
                    }

                    // If result looks like an error, surface raw details as well
                    if (!res.success || (res.output && String(res.output).toLowerCase().startsWith('eroare'))) {
                        out += '\n\n[DETAILS]\n' + JSON.stringify(res, null, 2);
                    }

                    result.textContent = out || JSON.stringify(res, null, 2);
                } else {
                    result.textContent = JSON.stringify(data, null, 2);
                }
                        result.textContent = data.result.output;
                    } else {
                        result.textContent = JSON.stringify(data.result, null, 2);
                    }
                } else {
                    result.textContent = JSON.stringify(data, null, 2);
                }
            } catch (err) {
                result.textContent = 'Eroare la cerere: ' + err;
            }
        }

        document.getElementById('send').addEventListener('click', sendPrompt);
        loadStatus();
        setInterval(loadStatus, 10000);
    </script>
</body>
</html>
"""

    def _get_runtime_agent():
        backend = config.get("ai.primary_backend", "gemini")
        if backend in (None, "", "none"):
            return None
        if runtime["agent"] is None:
            from core.agent import ANAAgent

            runtime["agent"] = ANAAgent(backend=backend)
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

    @app.route('/chat', methods=['GET'])
    def chat_ui():
        return """<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8"/>
<title>ANA MAX - Chat cu Qwen</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter',sans-serif;background:#0d1117;color:#e6edf3;height:100vh;display:flex;flex-direction:column}
  header{background:linear-gradient(135deg,#1a1f2e,#0d1117);border-bottom:1px solid #21262d;padding:14px 20px;display:flex;align-items:center;gap:12px}
  header h1{font-size:1.1rem;font-weight:700;color:#58a6ff}
  header .badge{background:#238636;color:#fff;font-size:.7rem;padding:2px 8px;border-radius:20px;font-weight:600}
  header .model{color:#8b949e;font-size:.8rem;margin-left:auto}
  #log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
  .msg{padding:12px 16px;border-radius:10px;max-width:80%;line-height:1.6;font-size:.9rem;white-space:pre-wrap;word-break:break-word}
  .msg.user{background:#1f6feb;color:#fff;align-self:flex-end;border-radius:10px 10px 2px 10px}
  .msg.ana{background:#161b22;border:1px solid #21262d;color:#e6edf3;align-self:flex-start;border-radius:2px 10px 10px 10px}
  .msg.system{background:#1a1f2e;color:#8b949e;align-self:center;font-size:.78rem;border:1px solid #21262d;border-radius:6px;padding:6px 12px}
  .msg.error{background:#2d1418;color:#f85149;border:1px solid #f85149;align-self:flex-start;border-radius:10px}
  .msg .sender{font-size:.7rem;font-weight:700;margin-bottom:4px;opacity:.7;text-transform:uppercase;letter-spacing:.05em}
  .thinking{color:#8b949e;font-style:italic;animation:pulse 1.5s infinite}
  @keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
  footer{padding:12px 16px;border-top:1px solid #21262d;background:#0d1117;display:flex;gap:8px}
  #inp{flex:1;background:#161b22;border:1px solid #30363d;color:#e6edf3;border-radius:8px;padding:10px 14px;font-size:.9rem;font-family:inherit;resize:none;height:44px;max-height:120px;outline:none;transition:border-color .2s}
  #inp:focus{border-color:#58a6ff}
  #btn{background:#238636;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:.9rem;font-weight:600;cursor:pointer;transition:background .2s;white-space:nowrap}
  #btn:hover{background:#2ea043}
  #btn:disabled{background:#21262d;cursor:not-allowed;color:#8b949e}
  #status{font-size:.75rem;color:#8b949e;text-align:center;padding:4px}
</style>
</head>
<body>
<header>
  <h1> ANA MAX</h1>
  <span class="badge">LIVE</span>
  <span class="model">Qwen 2.5 7B via Ollama</span>
</header>
<div id="log"></div>
<div id="status" id="status-bar">Conectat la ANA MAX &bull; http://127.0.0.1:8766</div>
<footer>
  <textarea id="inp" placeholder="Scrie un mesaj... (Enter = trimite, Shift+Enter = linie noua)"></textarea>
  <button id="btn">Trimite</button>
</footer>
<script>
const log = document.getElementById('log');
const inp = document.getElementById('inp');
const btn = document.getElementById('btn');
const statusBar = document.getElementById('status');

function addMsg(role, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  if (role === 'user') {
    d.innerHTML = '<div class="sender">Tu</div>' + escHtml(text);
  } else if (role === 'ana') {
    d.innerHTML = '<div class="sender">ANA MAX (Qwen)</div>' + escHtml(text);
  } else if (role === 'error') {
    d.innerHTML = '<div class="sender">Eroare</div>' + escHtml(text);
  } else {
    d.textContent = text;
  }
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>');
}

async function sendMsg() {
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  inp.style.height = '44px';
  btn.disabled = true;
  statusBar.textContent = 'ANA MAX se gandeste...';

  addMsg('user', text);
  const thinking = addMsg('ana', '');
  thinking.innerHTML = '<div class="sender">ANA MAX (Qwen)</div><span class="thinking">Se gandeste...</span>';

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
    let answer = '';
    if (data.result) {
      if (typeof data.result === 'string') answer = data.result;
      else if (data.result.response) answer = data.result.response;
      else if (data.result.output) answer = data.result.output;
      else if (data.result.content) answer = data.result.content;
      else answer = JSON.stringify(data.result, null, 2);
    } else if (data.error) {
      thinking.className = 'msg error';
      thinking.innerHTML = '<div class="sender">Eroare</div>' + escHtml(JSON.stringify(data.error));
      statusBar.textContent = 'Eroare de la server';
      btn.disabled = false;
      return;
    }
    thinking.innerHTML = '<div class="sender">ANA MAX (Qwen)</div>' + escHtml(answer);
    statusBar.textContent = 'Gata \u2022 ' + new Date().toLocaleTimeString();
  } catch(e) {
    thinking.className = 'msg error';
    thinking.innerHTML = '<div class="sender">Eroare retea</div>' + escHtml(e.toString());
    statusBar.textContent = 'Eroare de conectare';
  }
  btn.disabled = false;
  log.scrollTop = log.scrollHeight;
}

btn.addEventListener('click', sendMsg);
inp.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
  setTimeout(() => { inp.style.height = '44px'; inp.style.height = Math.min(inp.scrollHeight, 120) + 'px'; }, 0);
});

addMsg('system', 'ANA MAX conectat \u2022 Qwen 2.5 7B via Ollama \u2022 90 tools active');
</script>
</body>
</html>""", 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route('/health', methods=['GET'])
    def health():

        tools = registry.list_tools()
        return jsonify({
            "status": "online",
            "agent": "A.N.A. MAX",
            "version": "18.0-MAX",
            "tools_count": len(tools),
            "tools": sorted(tools),
            "mcp_ready": True,
            "vscode_agent": _is_vscode_agent_session(),
            "output_profile": "compact" if _compact_agent_output() else "normal",
        })

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
        params = data.get("params", {})

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
                if not message:
                    return jsonify({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Missing message"},
                    }), 400

                try:
                    agent = _get_runtime_agent()
                    if agent is None:
                        return jsonify({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {"output": "Internal AI backend is disabled.", "success": False}
                        })
                    
                    from core.autonomous_agent import AutonomousAgent
                    auto_agent = AutonomousAgent(agent)
                    result = auto_agent.execute_task(message)
                    response_text = result.get("output", "")
                except Exception as e:
                    logging.getLogger(__name__).exception("ana.chat failed")
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
