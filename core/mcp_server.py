"""
ANA MAX - MCP Server
=========================
Model Context Protocol server pentru integrare cu AdaL si alti agenti.
"""

import json
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from core.config import config

logger = logging.getLogger(__name__)


def _schema_from_tool_definition(definition) -> Dict[str, Any]:
    """Build MCP JSON schema from the public ToolDefinition."""
    input_schema = {"type": "object", "properties": {}, "required": []}
    for param in definition.parameters:
        prop = {"type": param.type if param.type != "any" else "string"}
        if param.description:
            prop["description"] = param.description
        if param.choices:
            prop["enum"] = param.choices
        if param.default is not None:
            prop["default"] = param.default
        input_schema["properties"][param.name] = prop
        if param.required:
            input_schema["required"].append(param.name)
    return input_schema


def _tool_result_payload(result) -> Dict[str, Any]:
    """Convert a ToolResult into a stable MCP-safe payload."""
    status = getattr(result, "status", None)
    return {
        "success": bool(getattr(result, "is_success", False)),
        "status": getattr(status, "value", str(status or "")),
        "data": getattr(result, "data", None),
        "message": getattr(result, "message", ""),
        "error": getattr(result, "error", None),
    }


def _make_registry_handler(tool_name: str) -> Callable:
    """Route MCP tool calls through ToolRegistry for validation and licensing."""
    def handler(**kwargs):
        from tools.base import registry

        result = registry.execute(tool_name, **kwargs)
        return _tool_result_payload(result)
    return handler


class MCPServer:
    """MCP Server pentru ANA MAX."""
    
    VERSION = "1.0.0"
    PROTOCOL_VERSION = "2024-11-05"
    
    def __init__(self, agent_name: str = "ANA MAX", agent_version: str = "18.0"):
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.tools: Dict[str, Any] = {}
        self.resources: Dict[str, Any] = {}
        self.prompts: Dict[str, Any] = {}
        self.connections: List[Dict] = []
        logger.info(f"MCP Server initialized: {agent_name} v{agent_version}")
    
    def register_tool(self, name: str, description: str, 
                     function: Callable, schema: Optional[Dict] = None) -> None:
        self.tools[name] = {
            "name": name,
            "description": description,
            "function": function,
            "inputSchema": schema or {"type": "object", "properties": {}, "required": []}
        }
        logger.info(f"Registered MCP tool: {name}")
    
    def register_resource(self, uri: str, name: str, 
                         description: str, mime_type: str = "text/plain") -> None:
        self.resources[uri] = {"uri": uri, "name": name, "description": description, "mimeType": mime_type}
        logger.info(f"Registered MCP resource: {uri}")
    
    def register_prompt(self, name: str, template: str, description: str = "") -> None:
        self.prompts[name] = {"name": name, "description": description, "template": template}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize": result = self._handle_initialize(params)
            elif method == "tools/list": result = self._handle_tools_list()
            elif method == "tools/call": result = await self._handle_tool_call(params)
            elif method == "resources/list": result = self._handle_resources_list()
            elif method == "prompts/list": result = self._handle_prompts_list()
            else: raise ValueError(f"Unknown method: {method}")
            
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(e)}}
    
    def _handle_initialize(self, params: Dict) -> Dict:
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {"name": self.agent_name, "version": self.agent_version},
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}}
        }
    
    def _handle_tools_list(self) -> Dict:
        return {"tools": [{"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]} for t in self.tools.values()]}
    
    async def _handle_tool_call(self, params: Dict) -> Dict:
        name = params.get("name")
        args = params.get("arguments", {})
        if name not in self.tools: raise ValueError(f"Tool not found: {name}")
        func = self.tools[name]["function"]
        try:
            if asyncio.iscoroutinefunction(func): res = await func(**args)
            else: res = func(**args)
            return {"content": [{"type": "text", "text": json.dumps(res, indent=2, default=str)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}

    def _handle_resources_list(self) -> Dict:
        return {"resources": list(self.resources.values())}

    def _handle_prompts_list(self) -> Dict:
        return {"prompts": list(self.prompts.values())}


class AdalBridge:
    """Bridge intre A.N.A. si AdaL."""
    
    def __init__(self, mcp_server: MCPServer):
        self.mcp_server = mcp_server
        self._register_ana_capabilities()
    
    def _register_ana_capabilities(self) -> None:
        # Tool: Smart Search
        self.mcp_server.register_tool(
            name="ana_smart_search",
            description="Cautare rapida FTS5 in codebase",
            function=self._smart_search_handler,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project_path": {"type": "string"}
                },
                "required": ["query"]
            }
        )
        
        # Tool: Auto-Evolution
        self.mcp_server.register_tool(
            name="ana_evolve",
            description="Evolutie A.N.A.",
            function=self._evolution_handler,
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["learn_pattern", "propose_tool"]},
                    "data": {"type": "object"}
                },
                "required": ["action", "data"]
            }
        )
        
        # Tool: Memory Search
        self.mcp_server.register_tool(
            name="ana_memory_search",
            description="Cauta in memoria locala A.N.A.",
            function=self._memory_search_handler,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string", "default": "all"}
                },
                "required": ["query"]
            }
        )

        # Sync all tools from ToolRegistry into MCP (no-op if already synced)
        try:
            from tools.base import registry
            # Ensure ToolRegistry is populated
            try:
                from tools.tool_healthcheck import ToolHealthcheckTool
                ToolHealthcheckTool()._ensure_registry()
            except Exception:
                pass

            # Register each tool from ToolRegistry to MCP
            for tool_name, tool_instance in list(registry._tools.items()):
                try:
                    definition = tool_instance.get_definition()
                    self.mcp_server.register_tool(
                        name=definition.name,
                        description=definition.description,
                        schema=_schema_from_tool_definition(definition),
                        function=_make_registry_handler(definition.name)
                    )
                except Exception as e:
                    logger.warning(f"Failed to register tool {tool_name}: {e}")
        except Exception as e:
            logger.warning(f"Error syncing ToolRegistry to MCP: {e}")
    
    def _smart_search_handler(self, query: str, project_path: Optional[str] = None) -> Dict:
        from core.smart_search import get_search_engine
        try:
            engine = get_search_engine(project_path)
            results = engine.search(query)
            return {"success": True, "count": len(results), "results": results[:20]}
        except Exception as e: return {"success": False, "error": str(e)}
    
    def _evolution_handler(self, action: str, data: Dict) -> Dict:
        from core.evolution import get_evolution_engine
        try:
            engine = get_evolution_engine()
            if action == "learn_pattern":
                engine.memory.save_knowledge(data.get("topic", "pattern"), data.get("content", ""))
                return {"success": True, "message": "Pattern learned"}
            elif action == "propose_tool":
                proposer = getattr(engine, "propose_new_capability", None) or getattr(engine, "propose_capability")
                proposal = proposer(
                    data.get("name", "new_tool"),
                    data.get("code_template", "def plugin_function(*args, **kwargs):\n    return 'ok'\n"),
                )
                return {"success": True, "message": "Tool proposed", "proposal": proposal}
            return {"success": False, "error": "Unknown action"}
        except Exception as e: return {"success": False, "error": str(e)}
    
    def _memory_search_handler(self, query: str, category: str = "all") -> Dict:
        from core.memory import get_memory
        try:
            memory = get_memory()
            rows = memory.search_knowledge(query, limit=15)
            if category != "all":
                rows = [row for row in rows if row.get("category", "") == category]
            return {
                "success": True,
                "count": len(rows),
                "results": [
                    {
                        "topic": str(row.get("topic", "")),
                        "content": str(row.get("content", ""))[:200],
                        "category": str(row.get("category", "")),
                    }
                    for row in rows[:15]
                ]
            }
        except Exception as e: return {"success": False, "error": str(e)}


# Global instance
_mcp_server: Optional[MCPServer] = None

def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer(agent_name="A.N.A. MAX", agent_version="18.0")
        AdalBridge(_mcp_server)
        # Load ALL tools from ToolRegistry into MCP server
        try:
            from tools.base import registry
            from tools.tool_healthcheck import ToolHealthcheckTool
            # Ensure ToolRegistry is populated
            health_tool = ToolHealthcheckTool()
            health_tool._ensure_registry()
            # Register all tools with MCP server
            for tool_name, tool_instance in registry._tools.items():
                try:
                    definition = tool_instance.get_definition()
                    _mcp_server.register_tool(
                        name=definition.name,
                        description=definition.description,
                        schema=_schema_from_tool_definition(definition),
                        function=_make_registry_handler(definition.name)
                    )
                except Exception as e:
                    logger.warning("Failed to register tool %s: %s", str(tool_name), str(e))
        except Exception as e:
            logger.warning("Failed to load tools from ToolRegistry: %s", str(e))
    return _mcp_server

# --- WEB BRIDGE INTEGRATION (Flask) ---
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    srv = get_mcp_server()
    return jsonify({
        "status": "online",
        "agent": f"ANA MAX MCP v{srv.agent_version}",
        "ready": True,
        "port": 8765
    })


@app.route('/status', methods=['GET'])
def status():
    """Health check extins: backend, memorie, MCP. Pentru /status in consola si monitorizare."""
    out = {"status": "online", "agent": "A.N.A. MCP", "ready": True}
    try:
        from core.config import config
        out["backend"] = config.get("ai.primary_backend", "gemini")
        out["evolution_enabled"] = config.get("evolution.enabled", False)
        out["evolution_mode"] = config.get("evolution.mode", "observe")
    except Exception as e:
        out["config_error"] = str(e)
    try:
        from core.memory import get_memory
        m = get_memory()
        out["memory"] = m.get_stats() if hasattr(m, "get_stats") else "ok"
    except Exception as e:
        out["memory_error"] = str(e)
    return jsonify(out)

@app.route('/tools', methods=['GET'])
def http_tools_list():
    """HTTP helper for clients that expect /tools."""
    srv = get_mcp_server()
    return jsonify({"tools": [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in srv.tools.values()
    ]})

@app.route('/execute', methods=['POST'])
def tool_endpoint():
    api_key = os.environ.get("ANA_MCP_KEY") or config.get("mcp.api_key")
    if api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {api_key}":
            logger.warning(f"MCP /execute Auth failed from {request.remote_addr}")
            return jsonify({"error": "Unauthorized", "success": False}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided", "success": False}), 400
    name = data.get("name")
    args = data.get("args", {})
    srv = get_mcp_server()
    if name not in srv.tools:
        return jsonify({"error": f"Tool not found: {name}", "success": False}), 404
    func = srv.tools[name]["function"]
    try:
        res = func(**args) if not asyncio.iscoroutinefunction(func) else asyncio.run(func(**args))
        return jsonify({"result": res, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/dashboard')
def dashboard():
    dashboard_path = Path(__file__).resolve().parent / 'dashboard.html'
    if not dashboard_path.exists():
        return "<h1>ANA MAX Dashboard</h1><p>dashboard.html not found.</p>", 404
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        return f.read()

def _get_ana_agent_fallback():
    """Creeaza un agent ANA; respecta tools-only mode cand backend-ul este none."""
    from core.config import config
    from core.agent import ANAAgent
    backend = config.get("ai.primary_backend", "gemini")
    if backend in (None, "", "none"):
        return None
    for candidate in (backend, "ollama", "gemini"):
        try:
            return ANAAgent(backend=candidate)
        except Exception as e:
            logger.warning(f"MCP: backend {candidate} nu este disponibil: {e}")
            continue
    raise RuntimeError("Niciun backend ANA disponibil (configura Gemini/Ollama/Grok).")


_web_bridge_agent = None

@app.route('/mcp', methods=['POST'])
def mcp_handler():
    """
    Endpoint pentru extensia de browser (Chrome/Grok/Gemini)
    Permite controlul A.N.A. direct din interfata web a AI-urilor.
    """
    import traceback
    
    api_key = os.environ.get("ANA_MCP_KEY") or config.get("mcp.api_key")
    if api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {api_key}":
            logger.warning(f"MCP /mcp Auth failed from {request.remote_addr}")
            return jsonify({"error": "Unauthorized", "jsonrpc": "2.0", "id": request.json.get('id') if request.is_json else None}), 401

    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    method_raw = data.get('method')
    method = str(method_raw).lower() if method_raw is not None else ""
    params = data.get('params', {})
    request_id = data.get('id', 1)

    print(f"[MCP Web] Request: {method}")

    try:
        # Standard MCP / JSON-RPC helpers
        srv = get_mcp_server()

        if method == "initialize":
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": srv.PROTOCOL_VERSION,
                    "serverInfo": {"name": srv.agent_name, "version": srv.agent_version},
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}}
                }
            })

        if method in ("tools/list", "tools.list"):
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": [
                    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
                    for t in srv.tools.values()
                ]}
            })

        if method in ("tools/call", "tools.call"):
            name = params.get("name")
            args = params.get("arguments", {})
            if name not in srv.tools:
                return jsonify({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Tool not found: {name}"}}), 404
            func = srv.tools[name]["function"]
            logger.info(f"TOOL CALL: {name} with args: {args}")
            try:
                res = func(**args) if not asyncio.iscoroutinefunction(func) else asyncio.run(func(**args))
                return jsonify({"jsonrpc": "2.0", "id": request_id, "result": res})
            except Exception as e:
                return jsonify({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(e)}}), 500

        if method == "ana.ping":
            return jsonify({"jsonrpc": "2.0", "id": request_id, "result": "pong"})

        if method == "ana.execute_task":
            task_desc = params.get('task') or params.get('query') or ""
            if not task_desc:
                return jsonify({"error": "No task provided", "jsonrpc": "2.0", "id": request_id}), 400

            global _web_bridge_agent
            if _web_bridge_agent is None:
                try:
                    from core.agent import ANAAgent
                    from core.config import config
                    backend = config.get("ai.primary_backend", "gemini")
                    if backend not in (None, "", "none"):
                        _web_bridge_agent = ANAAgent(backend=backend)
                except Exception as e:
                    logger.warning(f"MCP: agent init failed ({e}), trying fallback backends...")
                    _web_bridge_agent = _get_ana_agent_fallback()
            main_agent = _web_bridge_agent

            if main_agent is None:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "output": "ANA ruleaza in tools-only mode. ana.execute_task necesita un backend intern activ (gemini/ollama/grok).",
                        "success": False,
                        "full_report": "Activeaza un backend intern daca vrei reasoning intern; pentru tool-uri externe foloseste MCP tools direct."
                    }
                })

            # Incearca multi-agent cu audit; la eroare fallback la raspuns simplu
            try:
                from core.multi_agent_system import get_multi_agent_system
                mas = get_multi_agent_system(main_agent)
                result = mas.execute_with_audit(task_desc)
                elapsed = result.get("elapsed_time", 0)
                output_summary = {
                    "success": result.get("success", False),
                    "steps_completed": result.get("completed_steps", 0),
                    "total_steps": result.get("total_steps", 0),
                    "time": f"{elapsed:.2f}s",
                    "mode": "MULTI-AGENT (Audit Active)"
                }
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "output": str(output_summary),
                        "success": result.get("success", False),
                        "full_report": "Task executat. Verifica fisierele create."
                    }
                })
            except Exception as mas_err:
                logger.warning(f"MCP: multi-agent failed ({mas_err}), using simple send_message.")
                response_text = main_agent.send_message(task_desc)
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "output": response_text[:2000] if response_text else "(fara raspuns)",
                        "success": True,
                        "full_report": "Raspuns direct ANA (mod simplu)."
                    }
                })

        return jsonify({"error": "Method not found", "jsonrpc": "2.0", "id": request_id}), 404

    except Exception as e:
        logger.exception("MCP handler error")
        return jsonify({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

def run_flask():
    from werkzeug.serving import make_server
    
    # Configurare stealth
    stealth = config.get("mcp.stealth_mode", True)
    fake_banner = config.get("mcp.fake_banner", "")
    
    if stealth:
        # Ascunde banner-ul Flask
        import werkzeug.serving
        werkzeug.serving.run_with_reloader = lambda f: f
    
    server = make_server('127.0.0.1', 8765, app, threaded=True)
    
    if fake_banner and not getattr(app, '_banner_patched', False):
        # Seteaza banner fals
        original_wsgi = app.wsgi_app
        app.wsgi_app = lambda environ, start_response: environ.update({'SERVER_SOFTWARE': fake_banner}) or original_wsgi(environ, start_response)
        app._banner_patched = True
    
    print(f"ANA MAX MCP running on http://127.0.0.1:8765")
    server.serve_forever()

def start_mcp_with_bridge():
    port = config.get("mcp.port", 8765)
    host = config.get("mcp.host", "127.0.0.1")
    stealth = config.get("mcp.stealth_mode", True)
    fake_banner = config.get("mcp.fake_banner", "")
    
    if stealth:
        print(f"ANA MAX running on http://{host}:{port}")
    else:
        print(f"🚀 [A.N.A. MCP] Starting Server + Web Bridge on port {port}...")
    
    run_flask()

if __name__ == "__main__":
    start_mcp_with_bridge()
