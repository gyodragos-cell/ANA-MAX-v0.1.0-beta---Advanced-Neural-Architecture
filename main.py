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
        description="ANA MAX - MCP Server cu 63 tools, AI Desktop Control, AI Core Intelligence pentru OpenCode"
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
     MCP Server | 63 Tools | AI Desktop Control | OpenCode Ready
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
        ("tools.memory_tool", "MemoryTool"),
        ("tools.privacy", "PrivacyTool"),
        ("tools.git_tool", "GitTool"),
        ("tools.network_tool", "NetworkTool"),
        ("tools.security_tool", "SecurityTool"),
        ("tools.qa_tool", "QATool"),
        ("tools.smart_search_tool", "SmartSearchTool"),
        ("tools.debugger_tool", "DebuggerTool"),
        ("tools.codebase_understanding_tool", "CodebaseUnderstandingTool"),
        ("tools.browser_control", "BrowserControlTool"),
        ("tools.terminal_tool", "TerminalTool"),
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
        ("tools.adal_tool", "AdaLTool"),
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
        ("tools.foreground_ui_snapshot", "ForegroundUISnapshotTool"),  # NEW: Structural Eyes
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
            print(f"  [OK] {tool_instance.get_definition().name}")
        except Exception as e:
            print(f"  [!] {class_name} skip: {e}")

    for module_path, class_name in optional_modules:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            if class_name in {"AutonomousTool", "TaskTool"}:
                tool_instance = tool_class(runtime_agent)
            else:
                tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            print(f"  [OK] {tool_instance.get_definition().name} (optional)")
        except Exception as e:
            logging.getLogger(__name__).warning("Optional tool skipped %s.%s: %s", module_path, class_name, e)

    # Incarca noile tool-uri (2026-05-12)
    for module_path, class_name in new_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            print(f"  [OK] {tool_instance.get_definition().name} (NEW)")
        except Exception as e:
            print(f"  [!] {class_name} skip: {e}")
    
    # Windows Deep Sight tool (2026-05-13)
    try:
        tool_class = _load_tool_class("tools.windows_deep_sight", "WindowsDeepSightTool")
        tool_instance = tool_class()
        registry.register(tool_instance)
        loaded += 1
        print(f"  [OK] {tool_instance.get_definition().name} (GOD VIEW)")
    except Exception as e:
        logging.getLogger(__name__).warning("Deep Sight tool skipped: %s", e)

    # Incarca AI Desktop Control tools (2026-05-13)
    for module_path, class_name in desktop_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            print(f"  [OK] {tool_instance.get_definition().name} (DESKTOP CONTROL)")
        except Exception as e:
            logging.getLogger(__name__).warning("Desktop tool skipped %s.%s: %s", module_path, class_name, e)
    
    # Incarca Voice tools (2026-05-14) - JARVIS STYLE
    for module_path, class_name in voice_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            print(f"  [OK] {tool_instance.get_definition().name} (JARVIS VOICE)")
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
            print(f"  [OK] {tool_instance.get_definition().name} (RUFLO-INTEGRATION)")
        except Exception as e:
            logging.getLogger(__name__).warning("Advanced tool skipped %s.%s: %s", module_path, class_name, e)
    
    # Incarca UI-TARS tools (Vision, Remote, Event Stream) (2026-05-19)
    for module_path, class_name in uitars_tools:
        try:
            tool_class = _load_tool_class(module_path, class_name)
            tool_instance = tool_class()
            registry.register(tool_instance)
            loaded += 1
            print(f"  [OK] {tool_instance.get_definition().name} (UI-TARS-INTEGRATION)")
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
                print(f"  [OK] {instance.get_definition().name} (AI CORE)")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "AI Core adapter skipped %s: %s", AdapterClass.__name__, e
                )
    except ImportError as e:
        logging.getLogger(__name__).warning("tool_adapters.py nu a putut fi incarcat: %s", e)

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

    @app.route('/health', methods=['GET'])
    def health():
        tools = registry.list_tools()
        return jsonify({
            "status": "online",
            "agent": "A.N.A. MAX",
            "version": "18.0-MAX",
            "tools_count": len(tools),
            "tools": sorted(tools),
            "mcp_ready": True
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

    @app.route('/mcp', methods=['GET', 'POST'])
    def mcp_handler():
        """MCP JSON-RPC endpoint - suporta si GET pentru health check."""
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
                            "text": json.dumps({
                                "success": result.is_success,
                                "data": result.data,
                                "message": result.message,
                                "error": result.error
                            }, indent=2, default=str)
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
    
    app.run(host=host, port=port, debug=False, use_reloader=False)


def main() -> int:
    # Fix pentru UnicodeEncodeError pe Windows terminal
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    args = _build_parser().parse_args()
    _configure_logging(args.debug)
    _print_banner()

    # Creeaza directoare necesare
    for d in ["logs", "memory", "backups", "generated_bots"]:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)

    # Inregistreaza TOATE tool-urile
    print("\n  Incarcare tool-uri...")
    loaded = _register_all_tools()
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


