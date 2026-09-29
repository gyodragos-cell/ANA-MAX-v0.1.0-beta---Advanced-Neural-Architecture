"""
OS27 Hyper++ Universal MCP Server v3 (Real Backend)
====================================================
Expune TOATE componentele OS27 Core prin Model Context Protocol.
Backend-uri reale din ANA_MAX/tools/ — nu stubs.

Compatible cu: Antigravity, Devin, Cursor, Windsurf, Claude Code.
"""

import sys
import json
import os
import time
import traceback

# Fix Windows encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add ANA_MAX to path
ANA_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'ANA_MAX'))
if ANA_ROOT not in sys.path:
    sys.path.insert(0, ANA_ROOT)

# ============================================================================
# LAZY IMPORTS — loaded on first call to avoid startup overhead
# ============================================================================
_cache = {}

def _get_tool_auto_discovery():
    if 'discovery' not in _cache:
        from tools.tool_auto_discovery import (
            auto_discover_tools, discover_tool_files,
            validate_tool_integrity, generate_discovery_report
        )
        _cache['discovery'] = {
            'auto_discover': auto_discover_tools,
            'discover_files': discover_tool_files,
            'validate': validate_tool_integrity,
            'report': generate_discovery_report,
        }
    return _cache['discovery']

def _get_priority_map():
    if 'priority' not in _cache:
        from tools.tool_priority_map import get_all_priorities, get_priority, get_tools_by_priority
        _cache['priority'] = {
            'get_all': get_all_priorities,
            'get_one': get_priority,
            'by_level': get_tools_by_priority,
        }
    return _cache['priority']

def _get_smoke_test():
    if 'smoke' not in _cache:
        from tools.tool_smoke_test import smoke_test_tool
        _cache['smoke'] = {'run_one': smoke_test_tool}
    return _cache['smoke']

def _get_graph_router():
    if 'graph' not in _cache:
        try:
            from core.tool_graph import get_tool_graph, initialize_default_graph
            graph = get_tool_graph()
            if graph is None:
                initialize_default_graph()
                graph = get_tool_graph()
            _cache['graph'] = {'graph': graph, 'ok': True}
        except Exception as e:
            _cache['graph'] = {'graph': None, 'ok': False, 'error': str(e)}
    return _cache['graph']

def _get_context_engine():
    if 'context' not in _cache:
        from tools.context_engine import ContextEngineTool
        tool = ContextEngineTool()
        _cache['context'] = {'tool': tool, 'ok': True}
    return _cache['context']

def _get_self_evolving():
    if 'evolving' not in _cache:
        from tools.self_evolving_tool import SelfEvolvingTool
        tool = SelfEvolvingTool(auto_improve=False)
        _cache['evolving'] = {'tool': tool, 'ok': True}
    return _cache['evolving']

def _get_proactive_interrupt():
    if 'interrupt' not in _cache:
        from tools.proactive_interrupt import ProactiveInterruptTool
        tool = ProactiveInterruptTool()
        _cache['interrupt'] = {'tool': tool, 'ok': True}
    return _cache['interrupt']

def _get_reflex_dispatcher():
    if 'reflex' not in _cache:
        from tools.reflex_dispatcher import ReflexDispatcher
        _cache['reflex'] = {'dispatcher': ReflexDispatcher()}
    return _cache['reflex']

def _get_memory_cortex():
    if 'memory' not in _cache:
        from tools.memory_cortex import MemoryCortex, get_memory_telemetry, get_memory_health
        db_path = os.path.join(ANA_ROOT, 'ana_memory.db')
        cortex = MemoryCortex(db_path=db_path)
        _cache['memory'] = {
            'cortex': cortex,
            'telemetry': get_memory_telemetry,
            'health': get_memory_health,
        }
    return _cache['memory']

def _get_integrity_hyper():
    if 'integrity' not in _cache:
        from tools.system_integrity_tool import (
            SystemIntegrityCheckTool, get_system_integrity_telemetry, get_system_integrity_health
        )
        tool = SystemIntegrityCheckTool()
        _cache['integrity'] = {
            'tool': tool,
            'telemetry': get_system_integrity_telemetry,
            'health': get_system_integrity_health,
        }
    return _cache['integrity']

def _get_watchdog_bus():
    if 'watchdog' not in _cache:
        from tools.watchdog_bus import bus, WatchdogBusTool, _console_logger_subscriber
        _cache['watchdog'] = {
            'bus': bus,
            'tool': WatchdogBusTool(),
            'logger_sub': _console_logger_subscriber,
        }
    return _cache['watchdog']

def _get_health_dashboard():
    if 'dashboard' not in _cache:
        from tools.tool_health_dashboard import (
            get_tool_health_dashboard, get_critical_tools_health,
            get_broken_tools, get_degraded_tools
        )
        _cache['dashboard'] = {
            'full': get_tool_health_dashboard,
            'critical': get_critical_tools_health,
            'broken': get_broken_tools,
            'degraded': get_degraded_tools,
        }
    return _cache['dashboard']

def _get_error_radar():
    if 'radar' not in _cache:
        try:
            from tools.error_radar_tool import ErrorRadarTool
            _cache['radar'] = {'tool': ErrorRadarTool(), 'ok': True}
        except Exception as e:
            _cache['radar'] = {'tool': None, 'ok': False, 'error': str(e)}
    return _cache['radar']

def _get_self_heal():
    if 'heal' not in _cache:
        try:
            from tools.tool_auto_fix import auto_fix_tools
            _cache['heal'] = {'fix': auto_fix_tools, 'ok': True}
        except Exception as e:
            _cache['heal'] = {'fix': None, 'ok': False, 'error': str(e)}
    return _cache['heal']


def _get_omnisense():
    if 'omnisense' not in _cache:
        try:
            if ANA_ROOT not in sys.path:
                sys.path.insert(0, ANA_ROOT)
            import importlib.util
            root_dir = os.path.dirname(ANA_ROOT)
            spec = importlib.util.spec_from_file_location("omnisense", os.path.join(root_dir, "ANA_MAX", "core", "omnisense.py"))
            omni_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(omni_module)
            _cache['omnisense'] = {'module': omni_module, 'ok': True}
        except Exception as e:
            _cache['omnisense'] = {'module': None, 'ok': False, 'error': str(e)}
    return _cache['omnisense']

def _get_reactive_agent():
    if 'reactive' not in _cache:
        try:
            if ANA_ROOT not in sys.path:
                sys.path.insert(0, ANA_ROOT)
            import importlib.util
            root_dir = os.path.dirname(ANA_ROOT)
            spec = importlib.util.spec_from_file_location("reactive_agent", os.path.join(root_dir, "reactive_agent.py"))
            ra_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ra_module)
            _cache['reactive'] = {'agent': ra_module.ReactiveAgent(), 'ok': True}
        except Exception as e:
            _cache['reactive'] = {'agent': None, 'ok': False, 'error': str(e)}
    return _cache['reactive']


# ============================================================================
# TOOL DEFINITIONS (schema for tools/list)
# ============================================================================
TOOLS = [
    # --- Tool Brain ---
    {"name": "os27_tool_brain_discovery", "description": "Auto-discover all OS27 tools from filesystem. Returns tool files, registered tools, and integrity report.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_tool_brain_priority_map", "description": "Get the full tool priority map (critical/secondary/optional).", "inputSchema": {"type": "object", "properties": {"level": {"type": "string", "enum": ["critical", "secondary", "optional", "all"], "default": "all"}}}},
    {"name": "os27_tool_brain_smoke_test", "description": "Run smoke test on one or all tools. Tests: import, class discovery, instantiation.", "inputSchema": {"type": "object", "properties": {"tool_name": {"type": "string", "description": "Tool to test. Omit for all critical tools."}}}},
    {"name": "os27_tool_brain_graph", "description": "Read the OS27 tool interaction graph (Dijkstra-based routing).", "inputSchema": {"type": "object", "properties": {}}},

    # --- Context Engine ---
    {"name": "os27_context_engine_read_state", "description": "Read OS27 context engine state: telemetry, health, observer status.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_context_engine_reflexes", "description": "List all active reflex rules and recent alerts from the ReflexDispatcher.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_ai_core_context", "description": "AI Core: Context Engine trigger.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}}}},
    {"name": "os27_ai_core_evolving", "description": "AI Core: Self Evolving trigger.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}}}},
    {"name": "os27_ai_core_interrupt", "description": "AI Core: Proactive Interrupt trigger.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}}}},

    # --- Memory Cortex ---
    {"name": "os27_memory_cortex_save", "description": "Save a semantic or episodic memory entry.", "inputSchema": {"type": "object", "properties": {"category": {"type": "string", "enum": ["semantic", "episodic", "procedural"]}, "content": {"type": "string"}, "tags": {"type": "string"}}}},
    {"name": "os27_memory_cortex_load", "description": "Load recent memories, optionally filtered by category.", "inputSchema": {"type": "object", "properties": {"category": {"type": "string"}, "limit": {"type": "integer", "default": 10}}}},
    {"name": "os27_memory_cortex_reset", "description": "Reset memory cortex session context (does NOT delete DB).", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_memory_cortex_validate", "description": "Validate memory cortex: DB connectivity, table integrity, telemetry health.", "inputSchema": {"type": "object", "properties": {}}},

    # --- System Integrity Hyper ---
    {"name": "os27_system_integrity_hyper_scan", "description": "Full OS27 Hyper++ system integrity scan: registry, backends, config, deps, Ollama, logs, cleanup.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Watchdog Bus ---
    {"name": "os27_watchdog_bus_start", "description": "Start the OS27 event-driven watchdog bus.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_watchdog_bus_stop", "description": "Stop the OS27 watchdog bus.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_watchdog_bus_read", "description": "Read watchdog bus status: running, subscribers, recent events.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Telemetry Engine ---
    {"name": "os27_telemetry_engine_read", "description": "Read aggregated telemetry from all OS27 subsystems.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_telemetry_engine_save", "description": "Snapshot current telemetry to disk.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Dashboard Feeder ---
    {"name": "os27_dashboard_feeder_snapshot", "description": "Full health dashboard snapshot: all tools, health scores, broken/degraded lists.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Error Radar ---
    {"name": "os27_error_radar_scan", "description": "Scan for errors in logs and runtime.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Self Heal ---
    {"name": "os27_self_heal", "description": "Run OS27 auto-repair. Deep mode attempts full remediation.", "inputSchema": {"type": "object", "properties": {"deep": {"type": "boolean", "default": False}}}},

    # --- Reactive Agent ---
    {"name": "os27_reactive_agent_start", "description": "Start the reactive Qwen agent (background clipboard monitor).", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_reactive_agent_stop", "description": "Stop the reactive Qwen agent.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_reactive_agent_status", "description": "Get status of the reactive Qwen agent.", "inputSchema": {"type": "object", "properties": {}}},

    # --- Omni-Sense ---
    {"name": "os27_omnisense_start", "description": "Start the Omni-Sense proactive background vision agent.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_omnisense_stop", "description": "Stop the Omni-Sense proactive background vision agent.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "os27_omnisense_status", "description": "Get status of Omni-Sense.", "inputSchema": {"type": "object", "properties": {}}},
]


# ============================================================================
# TOOL EXECUTION (real backends)
# ============================================================================
def execute_tool(name, args):
    """Route tool call to real ANA_MAX backend."""
    t0 = time.time()

    # --- TOOL BRAIN ---
    if name == "os27_tool_brain_discovery":
        d = _get_tool_auto_discovery()
        report = d['report']()
        return _ok(report)

    if name == "os27_tool_brain_priority_map":
        p = _get_priority_map()
        level = args.get("level", "all")
        if level == "all":
            return _ok(p['get_all']())
        return _ok(p['by_level'](level))

    if name == "os27_tool_brain_smoke_test":
        s = _get_smoke_test()
        tool_name = args.get("tool_name")
        if tool_name:
            # Map class name to module name if necessary
            from tools import _CLASS_TO_MODULE
            mapped_name = _CLASS_TO_MODULE.get(tool_name, tool_name)
            return _ok(s['run_one'](mapped_name))
        # Run on critical tools
        p = _get_priority_map()
        critical = p['by_level']("critical")
        from tools import _CLASS_TO_MODULE
        results = {}
        for t in critical[:10]:  # cap at 10 for speed
            try:
                mapped_name = _CLASS_TO_MODULE.get(t, t)
                results[t] = s['run_one'](mapped_name)
            except Exception as e:
                results[t] = {"status": "error", "error": str(e)}
        return _ok(results)

    if name == "os27_tool_brain_graph":
        g = _get_graph_router()
        if not g['ok']:
            return _ok({"status": "graph_unavailable", "error": g.get('error', 'unknown')})
        graph = g['graph']
        return _ok({
            "nodes": len(graph.nodes) if hasattr(graph, 'nodes') else "unknown",
            "edges": len(graph.edges) if hasattr(graph, 'edges') else "unknown",
            "status": "loaded",
        })

    # --- CONTEXT ENGINE ---
    if name == "os27_context_engine_read_state":
        c = _get_context_engine()['tool']
        return _ok(c.execute(action="get_health").data)

    if name == "os27_ai_core_context":
        return _ok(_get_context_engine()['tool'].execute(action=args.get("action", "get_health")).__dict__)

    if name == "os27_ai_core_evolving":
        return _ok(_get_self_evolving()['tool'].execute(action=args.get("action", "health")).__dict__)

    if name == "os27_ai_core_interrupt":
        return _ok(_get_proactive_interrupt()['tool'].execute(action=args.get("action", "get_health")).__dict__)

    if name == "os27_context_engine_reflexes":
        r = _get_reflex_dispatcher()
        dispatcher = r['dispatcher']
        return _ok({
            "rules_count": len(dispatcher.rules),
            "rules": dispatcher.rules,
            "recent_alerts": dispatcher.alerts[-20:] if dispatcher.alerts else [],
        })

    # --- MEMORY CORTEX ---
    if name == "os27_memory_cortex_save":
        m = _get_memory_cortex()
        cortex = m['cortex']
        category = args.get("category", "semantic")
        content = args.get("content", "")
        tags = args.get("tags", "")
        cortex.remember(content, category=category, tags=tags)
        return _ok({"saved": True, "category": category})

    if name == "os27_memory_cortex_load":
        m = _get_memory_cortex()
        cortex = m['cortex']
        category = args.get("category")
        limit = args.get("limit", 10)
        memories = cortex.recall(category=category, limit=limit)
        return _ok({"memories": memories, "count": len(memories) if memories else 0})

    if name == "os27_memory_cortex_reset":
        m = _get_memory_cortex()
        cortex = m['cortex']
        cortex._session_context.clear()
        return _ok({"reset": True, "session_context_cleared": True})

    if name == "os27_memory_cortex_validate":
        m = _get_memory_cortex()
        import sqlite3
        validation = {"db_exists": False, "tables": [], "health": "unknown", "telemetry": {}}
        db_path = m['cortex'].db_path
        validation["db_exists"] = os.path.exists(db_path)
        if validation["db_exists"]:
            try:
                with sqlite3.connect(db_path) as conn:
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    validation["tables"] = [t[0] for t in tables]
            except Exception as e:
                validation["db_error"] = str(e)
        validation["health"] = m['health']()
        validation["telemetry"] = m['telemetry']()
        return _ok(validation)

    # --- SYSTEM INTEGRITY HYPER ---
    if name == "os27_system_integrity_hyper_scan":
        ih = _get_integrity_hyper()
        tool = ih['tool']
        result = tool.execute(mode="full")
        return _ok({
            "report": result.data if hasattr(result, 'data') else str(result),
            "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
            "message": result.message if hasattr(result, 'message') else "",
            "telemetry": ih['telemetry'](),
            "health": ih['health'](),
        })

    # --- WATCHDOG BUS ---
    if name == "os27_watchdog_bus_start":
        w = _get_watchdog_bus()
        w['bus'].subscribe(w['logger_sub'])
        w['bus'].start()
        return _ok({"started": True})

    if name == "os27_watchdog_bus_stop":
        w = _get_watchdog_bus()
        w['bus'].stop()
        return _ok({"stopped": True})

    if name == "os27_watchdog_bus_read":
        w = _get_watchdog_bus()
        bus = w['bus']
        is_running = bus._worker_thread is not None and bus._worker_thread.is_alive()
        # Drain recent events from queue (non-destructive peek via list)
        events = []
        try:
            q = bus._queue
            events = list(q.queue)[-20:]  # last 20 events
        except Exception:
            pass
        return _ok({
            "running": is_running,
            "subscribers": len(bus._subscribers),
            "queue_size": bus._queue.qsize(),
            "recent_events": events,
        })

    # --- REACTIVE AGENT ---
    if name == "os27_reactive_agent_start":
        ra = _get_reactive_agent()
        if not ra['ok']:
            return _err("Failed to load reactive agent", ra['error'])
        if ra['agent']._running:
            return _ok({"status": "already running"})
        ra['agent'].start()
        return _ok({"status": "started"})

    if name == "os27_reactive_agent_stop":
        ra = _get_reactive_agent()
        if not ra['ok']:
            return _err("Failed to load reactive agent", ra['error'])
        if not ra['agent']._running:
            return _ok({"status": "not running"})
        ra['agent'].stop()
        return _ok({"status": "stopped"})

    if name == "os27_reactive_agent_status":
        ra = _get_reactive_agent()
        if not ra['ok']:
            return _err("Failed to load reactive agent", ra['error'])
        status = ra['agent'].watcher.get_status()
        status['running'] = ra['agent']._running
        return _ok(status)

    # --- OMNI-SENSE ---
    if name == "os27_omnisense_start":
        om = _get_omnisense()
        if not om['ok']: return _err("Failed to load omnisense", om['error'])
        om['module'].start_omnisense()
        return _ok({"status": "started"})

    if name == "os27_omnisense_stop":
        om = _get_omnisense()
        if not om['ok']: return _err("Failed to load omnisense", om['error'])
        om['module'].stop_omnisense()
        return _ok({"status": "stopped"})

    if name == "os27_omnisense_status":
        om = _get_omnisense()
        if not om['ok']: return _err("Failed to load omnisense", om['error'])
        inst = om['module']._omnisense_instance
        if not inst:
            return _ok({"running": False})
        return _ok({
            "running": True,
            "vision_active": getattr(inst, '_running_vision', False),
            "last_alert": getattr(inst, '_last_alert_time', 0),
        })

    # --- TELEMETRY ENGINE ---
    if name == "os27_telemetry_engine_read":
        telemetry = {}
        try:
            from tools.context_engine import get_context_telemetry, get_context_health
            telemetry["context_engine"] = {"telemetry": get_context_telemetry(), "health": get_context_health()}
        except Exception as e:
            telemetry["context_engine"] = {"error": str(e)}
        try:
            mc = _get_memory_cortex()
            telemetry["memory_cortex"] = {"telemetry": mc['telemetry'](), "health": mc['health']()}
        except Exception as e:
            telemetry["memory_cortex"] = {"error": str(e)}
        try:
            ih = _get_integrity_hyper()
            telemetry["integrity"] = {"telemetry": ih['telemetry'](), "health": ih['health']()}
        except Exception as e:
            telemetry["integrity"] = {"error": str(e)}
        return _ok(telemetry)

    if name == "os27_telemetry_engine_save":
        telemetry_snapshot = {}
        try:
            from tools.context_engine import get_context_telemetry
            telemetry_snapshot["context_engine"] = get_context_telemetry()
        except: pass
        try:
            mc = _get_memory_cortex()
            telemetry_snapshot["memory_cortex"] = mc['telemetry']()
        except: pass
        try:
            ih = _get_integrity_hyper()
            telemetry_snapshot["integrity"] = ih['telemetry']()
        except: pass

        snapshot_path = os.path.join(ANA_ROOT, 'logs', f'telemetry_snapshot_{int(time.time())}.json')
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(telemetry_snapshot, f, indent=2, default=str)
        return _ok({"saved": True, "path": snapshot_path})

    # --- DASHBOARD FEEDER ---
    if name == "os27_dashboard_feeder_snapshot":
        d = _get_health_dashboard()
        full = d['full']()
        broken = d['broken']()
        degraded = d['degraded']()
        return _ok({
            "dashboard": full,
            "broken_tools": broken,
            "degraded_tools": degraded,
        })

    # --- ERROR RADAR ---
    if name == "os27_error_radar_scan":
        r = _get_error_radar()
        if not r['ok']:
            return _ok({"status": "error_radar_unavailable", "error": r.get('error', 'unknown')})
        result = r['tool'].execute()
        return _ok({
            "report": result.data if hasattr(result, 'data') else str(result),
            "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
        })

    # --- SELF HEAL ---
    if name == "os27_self_heal":
        h = _get_self_heal()
        deep = args.get("deep", False)
        if not h['ok']:
            return _ok({"status": "self_heal_unavailable", "error": h.get('error', 'unknown')})
        # auto_fix_tool expects a tool_name; in deep mode, fix all broken
        if deep:
            d = _get_health_dashboard()
            broken = d['broken']()
            results = {}
            for t in broken:
                try:
                    results[t] = str(h['fix']([t]))
                except Exception as e:
                    results[t] = f"fix_error: {e}"
            return _ok({"deep": True, "fixed": results, "broken_count": len(broken)})
        return _ok({"deep": False, "message": "Shallow heal: use deep=True for full remediation."})

    return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


def _ok(data):
    """Wrap result as MCP content."""
    text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    return {"content": [{"type": "text", "text": text}]}


# ============================================================================
# MCP JSONRPC PROTOCOL HANDLER
# ============================================================================
def handle_request(request_str):
    try:
        req = json.loads(request_str)
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "OS27 Hyper++ Universal MCP", "version": "3.0.0"}
            }
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        elif method == "notifications/initialized":
            return None  # no response needed

        elif method == "tools/list":
            result = {"tools": TOOLS}
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result = execute_tool(tool_name, tool_args)
            except Exception as e:
                result = {"isError": True, "content": [{"type": "text", "text": f"Execution error: {e}\n{traceback.format_exc()}"}]}
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    except Exception as e:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}


# ============================================================================
# MAIN LOOP (stdio transport)
# ============================================================================
if __name__ == "__main__":
    sys.stderr.write("[OS27 MCP v3] Server started. Waiting for JSONRPC requests on stdin...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_request(line)
        if response is not None:
            sys.stdout.write(json.dumps(response, default=str, ensure_ascii=False) + "\n")
            sys.stdout.flush()
