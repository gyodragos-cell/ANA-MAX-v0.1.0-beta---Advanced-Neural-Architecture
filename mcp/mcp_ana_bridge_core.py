#!/usr/bin/env python3
"""ANA MAX MCP Bridge - Core Tools with Lazy Loading."""

import asyncio
import os
import sys
import subprocess
import time
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

ANA_MANUS_ROOT = os.path.dirname(os.path.abspath(__file__))
ANA_MAX_ROOT = os.path.join(ANA_MANUS_ROOT, "ANA_MAX")

# Add paths
for p in (ANA_MAX_ROOT, ANA_MANUS_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# Lazy loading: delay startup if MCP_LAZY_LOAD is set
if os.environ.get("MCP_LAZY_LOAD", "0") == "1":
    lazy_delay = int(os.environ.get("MCP_LAZY_DELAY", "5"))
    print(f"[MCP LAZY LOAD] Delaying startup by {lazy_delay}s...")
    time.sleep(lazy_delay)
    print("[MCP LAZY LOAD] Startup resumed")

server = Server("ana-max-core")

server = Server("ana-max-core")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List tools with optional category filtering based on MCP_CATEGORY environment variable."""
    all_tools = [
        Tool(name="terminal", description="Execute terminal commands", inputSchema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}),
        Tool(name="file_operations", description="File operations: read, write, delete, list", inputSchema={"type": "object", "properties": {"operation": {"type": "string"}, "path": {"type": "string"}}, "required": ["operation", "path"]}),
        Tool(name="large_file_reader", description="Read large text/code files (10k+ lines) by splitting into chunks", inputSchema={"type": "object", "properties": {"file_path": {"type": "string"}, "chunk_size": {"type": "integer"}, "max_chunks": {"type": "integer"}}, "required": ["file_path"]}),
        Tool(name="code_search", description="Search code in project", inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        Tool(name="git_operations", description="Git operations: commit, push, pull", inputSchema={"type": "object", "properties": {"operation": {"type": "string"}}, "required": ["operation"]}),
        Tool(name="system_control", description="System control operations", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="system_inspector", description="Inspect system state", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="project_navigator", description="Navigate project structure", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="agent_coach", description="AI agent coaching and recommendations", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="tool_router", description="Route to appropriate tool", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="error_radar", description="Detect and analyze errors", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="security_audit", description="Security audit tools", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="network_diag", description="Network diagnostics", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="file_patch", description="Patch files with diffs", inputSchema={"type": "object", "properties": {}, "required": []}),
        # NEW TOOLS - 12 critical additions from ANA local tools (NO VOICE, NO OCR)
        Tool(name="smart_search", description="Smart search across project", inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": []}),
        Tool(name="code_context_pack", description="Code context pack for project understanding", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="tool_healthcheck", description="Tool health check and status", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="live_debug_console", description="Live debug console", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="procmon_monitor", description="Process monitoring", inputSchema={"type": "object", "properties": {"pid": {"type": "integer"}}, "required": []}),
        Tool(name="memory_cortex", description="Memory cortex operations", inputSchema={"type": "object", "properties": {"action": {"type": "string"}}, "required": []}),
        Tool(name="context_engine", description="Context engine for AI operations", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="privacy_shield", description="Privacy protection shield", inputSchema={"type": "object", "properties": {"action": {"type": "string"}}, "required": []}),
        Tool(name="session_checkpoint", description="Session checkpoint management", inputSchema={"type": "object", "properties": {"action": {"type": "string"}}, "required": []}),
        Tool(name="qa_tool", description="Quality assurance tool", inputSchema={"type": "object", "properties": {"test_type": {"type": "string"}}, "required": []}),
        Tool(name="conversation_audit", description="Conversation audit and analysis", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="graph_context_pack", description="Graph context pack for understanding", inputSchema={"type": "object", "properties": {}, "required": []})
    ]
    
    # Filter by category if MCP_CATEGORY environment variable is set
    category = os.environ.get("MCP_CATEGORY", "").lower()
    if category == "coding":
        return [tool for tool in all_tools if tool.name in ["terminal", "file_operations", "code_search", "git_operations", "smart_search", "code_context_pack"]]
    elif category == "system":
        return [tool for tool in all_tools if tool.name in ["system_control", "system_inspector", "project_navigator", "tool_healthcheck"]]
    elif category == "intelligence":
        return [tool for tool in all_tools if tool.name in ["agent_coach", "tool_router", "error_radar", "memory_cortex"]]
    
    return all_tools

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "terminal":
            command = arguments.get("command", "")
            if command:
                result = await asyncio.to_thread(subprocess.run, command, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout + result.stderr
                return [TextContent(type="text", text=output)]
            return [TextContent(type="text", text="Error: No command provided")]
        
        elif name == "file_operations":
            operation = arguments.get("operation", "")
            path = arguments.get("path", "")
            if operation == "list":
                if os.path.isdir(path):
                    files = os.listdir(path)
                    return [TextContent(type="text", text=f"Files in {path}:\n" + "\n".join(files))]
                return [TextContent(type="text", text=f"Error: {path} is not a directory")]
            elif operation == "read":
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    return [TextContent(type="text", text=content)]
                return [TextContent(type="text", text=f"Error: {path} is not a file")]
            return [TextContent(type="text", text=f"Error: Unknown operation {operation}")]
        
        elif name == "large_file_reader":
            file_path = arguments.get("file_path", "")
            chunk_size = arguments.get("chunk_size", 1000)
            max_chunks = arguments.get("max_chunks", 10)
            
            if not file_path:
                return [TextContent(type="text", text="Error: file_path is required")]
            
            if not os.path.exists(file_path):
                return [TextContent(type="text", text=f"Error: File not found: {file_path}")]
            
            try:
                # Read file with simple approach - no complex imports
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                
                total_lines = len(lines)
                lines_to_read = min(total_lines, chunk_size * max_chunks)
                
                # Limit response size to prevent blocking
                max_response_size = 50000  # 50KB max response
                chunks = []
                current_size = 0
                
                for i in range(0, lines_to_read, chunk_size):
                    if current_size >= max_response_size:
                        break
                        
                    chunk_lines = lines[i:min(i + chunk_size, lines_to_read)]
                    chunk_text = "".join(chunk_lines)
                    chunk_size_chars = len(chunk_text)
                    
                    if current_size + chunk_size_chars > max_response_size:
                        # Truncate last chunk if too big
                        remaining = max_response_size - current_size
                        chunk_text = chunk_text[:remaining]
                        chunks.append(f"Chunk {len(chunks) + 1} (lines {i+1}-{min(i+len(chunk_lines), total_lines)}, truncated):\n{chunk_text}")
                        current_size += remaining
                        break
                    
                    chunks.append(f"Chunk {len(chunks) + 1} (lines {i+1}-{min(i+chunk_size, total_lines)}):\n{chunk_text}")
                    current_size += chunk_size_chars
                
                header = (
                    f"File: {file_path}\n"
                    f"Total lines: {total_lines}\n"
                    f"Reading: {min(lines_to_read, current_size//100)} lines\n"
                    f"Chunks: {len(chunks)}\n"
                    f"Response size: {current_size} chars\n\n"
                )
                
                return [TextContent(type="text", text=header + "\n\n".join(chunks))]
                
            except Exception as e:
                return [TextContent(type="text", text=f"Error reading file: {str(e)}")]
        
        elif name == "code_search":
            query = arguments.get("query", "")
            result = await asyncio.to_thread(subprocess.run, f"grep -r \"{query}\" {ANA_MANUS_ROOT}", shell=True, capture_output=True, text=True, timeout=30)
            return [TextContent(type="text", text=result.stdout or "No results")]
        
        elif name == "git_operations":
            operation = arguments.get("operation", "")
            result = await asyncio.to_thread(subprocess.run, f"git {operation}", shell=True, capture_output=True, text=True, timeout=30, cwd=ANA_MANUS_ROOT)
            return [TextContent(type="text", text=result.stdout + result.stderr)]
        
        elif name == "system_inspector":
            cpu_info = await asyncio.to_thread(subprocess.run, "wmic cpu get name", shell=True, capture_output=True, text=True, timeout=10)
            ram_info = await asyncio.to_thread(subprocess.run, "wmic memorychip get capacity", shell=True, capture_output=True, text=True, timeout=10)
            info = f"CPU:\n{cpu_info.stdout}\n\nRAM:\n{ram_info.stdout}"
            return [TextContent(type="text", text=info)]
        
        elif name == "system_control":
            action = arguments.get("action", "")
            if action == "shutdown":
                return [TextContent(type="text", text="Shutdown not implemented (safety)")]
            elif action == "reboot":
                return [TextContent(type="text", text="Reboot not implemented (safety)")]
            elif action == "sleep":
                await asyncio.to_thread(subprocess.run, "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True, capture_output=True, timeout=10)
                return [TextContent(type="text", text="System going to sleep")]
            return [TextContent(type="text", text=f"Unknown action: {action}")]
        
        elif name == "project_navigator":
            path = arguments.get("path", ANA_MANUS_ROOT)
            if os.path.isdir(path):
                result = await asyncio.to_thread(subprocess.run, f"dir /s /b {path}", shell=True, capture_output=True, text=True, timeout=30)
                files = result.stdout.split("\n")[:50]
                return [TextContent(type="text", text=f"Project structure (first 50 files):\n" + "\n".join(files))]
            return [TextContent(type="text", text=f"Error: {path} not found")]
        
        elif name == "network_diag":
            ping_result = await asyncio.to_thread(subprocess.run, "ping -n 4 8.8.8.8", shell=True, capture_output=True, text=True, timeout=30)
            ip_result = await asyncio.to_thread(subprocess.run, "ipconfig", shell=True, capture_output=True, text=True, timeout=10)
            info = f"Ping test:\n{ping_result.stdout}\n\nIP Config:\n{ip_result.stdout}"
            return [TextContent(type="text", text=info)]
        
        elif name == "error_radar":
            return [TextContent(type="text", text="Error radar not implemented (requires log analysis)")]
        
        elif name == "security_audit":
            return [TextContent(type="text", text="Security audit not implemented (requires security scanner)")]
        
        elif name == "ocr_tool":
            return [TextContent(type="text", text="OCR tool not implemented (requires Tesseract or similar)")]
        
        elif name == "file_patch":
            return [TextContent(type="text", text="File patch not implemented (requires diff library)")]
        
        elif name == "agent_coach":
            return [TextContent(type="text", text="Agent coach not implemented (requires ANA telemetry)")]
        
        elif name == "tool_router":
            return [TextContent(type="text", text="Tool router not implemented")]
        
        elif name == "project_analyzer":
            return [TextContent(type="text", text="Project analyzer not implemented")]
        
        # NEW TOOLS IMPLEMENTATIONS - Connected to ANA local tools
        elif name == "smart_search":
            query = arguments.get("query", "")
            try:
                from tools.smart_search_tool import SmartSearchTool
                tool = SmartSearchTool()
                result = tool.execute(query=query)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Smart search error: {str(e)}")]

        elif name == "code_context_pack":
            try:
                from tools.code_context_pack_tool import CodeContextPackTool
                tool = CodeContextPackTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Code context pack error: {str(e)}")]

        elif name == "tool_healthcheck":
            try:
                from tools.tool_healthcheck import ToolHealthcheckTool
                tool = ToolHealthcheckTool()
                result = tool.execute()
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Tool healthcheck error: {str(e)}")]
        
        elif name == "live_debug_console":
            try:
                from tools.debugger_tool import DebuggerTool
                tool = DebuggerTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Live debug console error: {str(e)}")]

        elif name == "procmon_monitor":
            try:
                from tools.session_audit_tool import SessionAuditTool
                tool = SessionAuditTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Process monitor error: {str(e)}")]

        elif name == "memory_cortex":
            action = arguments.get("action", "query")
            try:
                from tools.memory_tool import MemoryTool
                tool = MemoryTool()
                # Convert MCP 'action' to MemoryTool API
                if action == "query":
                    result = tool.execute(action="search_knowledge", query=arguments.get("query", ""))
                elif action == "stats":
                    result = tool.execute(action="stats")
                elif action == "list":
                    result = tool.execute(action="list_topics")
                else:
                    result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Memory cortex error: {str(e)}")]

        elif name == "context_engine":
            try:
                from tools.tool_adapters import ContextEngineAdapter
                tool = ContextEngineAdapter()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Context engine error: {str(e)}")]

        elif name == "privacy_shield":
            try:
                from tools.privacy import PrivacyTool
                tool = PrivacyTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Privacy shield error: {str(e)}")]

        elif name == "session_checkpoint":
            try:
                from tools.session_checkpoint_tool import SessionCheckpointTool
                tool = SessionCheckpointTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Session checkpoint error: {str(e)}")]

        elif name == "qa_tool":
            try:
                from tools.qa_tool import QATool
                tool = QATool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"QA tool error: {str(e)}")]

        elif name == "conversation_audit":
            try:
                from tools.conversation_learning_tool import ConversationLearningTool
                tool = ConversationLearningTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Conversation audit error: {str(e)}")]

        elif name == "graph_context_pack":
            try:
                from tools.graph_context_pack_tool import GraphContextPackTool
                tool = GraphContextPackTool()
                result = tool.execute(**arguments)
                return [TextContent(type="text", text=str(result.data or result.message))]
            except Exception as e:
                return [TextContent(type="text", text=f"Graph context pack error: {str(e)}")]
        
        return [TextContent(type="text", text=f"Tool {name} not implemented yet")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
