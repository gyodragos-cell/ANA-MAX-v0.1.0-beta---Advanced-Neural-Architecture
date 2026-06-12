#!/usr/bin/env python3
"""
ANA MAX - MCP stdio wrapper.

Exposes a focused set of ANA tools over stdin/stdout for MCP clients.
Now integrated with OS v2 capabilities for unified system access.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
from pathlib import Path

os.environ["ANA_MCP_MODE"] = "1"

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

log_dir = BASE_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.ERROR, filename=str(log_dir / "mcp_stdio.log"))

from tools.base import registry  # noqa: E402

_tools_loaded = False


# Security: Input validation patterns
_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9_\-./\\]+$')
_COMMAND_PATTERN = re.compile(r'^[a-zA-Z0-9_\- ]+$')


def _validate_path(path: str) -> bool:
    """Validate path to prevent directory traversal attacks."""
    if not path:
        return False
    # Prevent path traversal
    if ".." in path or path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False
    return bool(_PATH_PATTERN.match(path))


def _validate_command(cmd: str) -> bool:
    """Validate command to prevent command injection."""
    if not cmd:
        return False
    # Prevent shell metacharacters
    dangerous_chars = ['|', '&', ';', '$', '`', '(', ')', '<', '>', '\n', '\r']
    if any(char in cmd for char in dangerous_chars):
        return False
    return bool(_COMMAND_PATTERN.match(cmd))


def _sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize string input to prevent injection attacks."""
    if not isinstance(value, str):
        return ""
    # Truncate to prevent DoS
    value = value[:max_length]
    # Remove null bytes
    value = value.replace("\x00", "")
    return value


def load_tools():
    """Load ALL available ANA MAX tools dynamically.

    Each tool is loaded inside its own try/except block so a single
    missing dependency never prevents the rest from loading.
    Returns the total number of successfully registered tools.
    """
    import logging as _log

    # --- Core tool catalogue -------------------------------------------
    _catalogue = [
        # (module_path, ClassName)
        ("tools.files",                     "FilesTool"),
        ("tools.system",                    "SystemTool"),
        ("tools.code",                      "CodeTool"),
        ("tools.web",                       "WebTool"),
        ("tools.memory_tool",               "MemoryTool"),
        ("tools.memory_cortex",             "MemoryCortexTool"),
        ("tools.smart_search_tool",         "SmartSearchTool"),
        ("tools.ana_context_tool",          "AnaContextTool"),
        ("tools.desktop_capture",           "DesktopCaptureTool"),
        ("tools.windows_uia_bridge",        "WindowsUiaBridgeTool"),
        ("tools.foreground_ui_snapshot",    "ForegroundUISnapshotTool"),
        ("tools.frida_automation",          "FridaTool"),
        ("tools.windows_deep_sight",        "WindowsDeepSightTool"),
        ("tools.windows_insight_tool",      "WindowsInsightTool"),
        ("tools.security_tool",             "SecurityTool"),
        ("tools.terminal_tool",             "TerminalTool"),
        ("tools.debugger_tool",             "DebuggerTool"),
        ("tools.edit_tool",                 "EditTool"),
        ("tools.task_tool",                 "TaskTool"),
        ("tools.code_search",               "CodeSearchTool"),
        ("tools.browser_control",           "BrowserControlTool"),
        ("tools.live_desktop_viewer",       "LiveDesktopViewerTool"),
        ("tools.desktop_control_tool",      "DesktopControlTool"),
        ("tools.edge_tts_voice",            "EdgeTTSVoice"),
        # Extended tool set
        ("tools.network_tool",              "NetworkTool"),
        ("tools.clipboard_manager",         "ClipboardManagerTool"),
        ("tools.ocr_tool",                  "OcrTool"),
        ("tools.qa_tool",                   "QATool"),
        ("tools.todo_tool",                 "TodoTool"),
        ("tools.session_log_miner_tool",    "SessionLogMinerTool"),
        ("tools.conversation_learning_tool","ConversationLearningTool"),
        ("tools.project_navigator_tool",    "ProjectNavigatorTool"),
        ("tools.codebase_understanding_tool","CodebaseUnderstandingTool"),
        ("tools.workspace_situational_awareness", "WorkspaceSituationalAwarenessTool"),
        ("tools.file_patch_tool",           "FilePatchTool"),
        ("tools.error_radar_tool",          "ErrorRadarTool"),
        ("tools.tool_router_tool",          "ToolRouterTool"),
        ("tools.window_manager",            "WindowManagerTool"),
        ("tools.web_scraper",               "WebScraperTool"),
        ("tools.hardware_scanner_tool",     "HardwareScannerTool"),
        ("tools.system_optimization_tool",  "SystemOptimizationTool"),
        ("tools.agent_coach_tool",          "AgentCoachTool"),
        ("tools.science_tool",              "ScienceTool"),
        ("tools.autonomous_tool",           "AutonomousTool"),
        ("tools.ana_orchestrator",          "AnaOrchestratorTool"),
        ("tools.adb_tool",                  "AdbTool"),
        ("tools.uia_click_tool",            "UiaClickTool"),
        ("tools.uia_type_tool",             "UiaTypeTool"),
        ("tools.vision_fallback_tool",      "VisionFallbackTool"),
        ("tools.vision_find_element_tool",  "VisionFindElementTool"),
        ("tools.vision_region_capture_tool","VisionRegionCaptureTool"),
        ("tools.session_checkpoint_tool",   "SessionCheckpointTool"),
        ("tools.session_rem_sleep_tool",    "SessionRemSleepTool"),
        ("tools.session_lifecycle_tool",    "SessionLifecycleTool"),
        ("tools.smoke_test_runner",         "SmokeTestRunnerTool"),
        ("tools.tool_healthcheck",          "ToolHealthcheckTool"),
        ("tools.live_debug_console",        "LiveDebugConsoleTool"),
        ("tools.voice_commentary",          "VoiceCommentaryTool"),
        ("tools.text_to_speech",            "TextToSpeechTool"),
        ("tools.web_ai_bridge",             "WebAiBridgeTool"),
        ("tools.swarm_tool",                "SwarmTool"),
        ("tools.advanced_scanner",          "AdvancedScannerTool"),
        ("tools.live_tool_healer",          "LiveToolHealerTool"),
        ("tools.context_engine",            "ContextEngineTool"),
        ("tools.ana_runtime_inspector",     "AnaRuntimeInspectorTool"),
        ("tools.event_stream_tool",         "EventStreamTool"),
        ("tools.vector_memory_tool",        "VectorMemoryTool"),
        ("tools.apk_analyzer",              "ApkAnalyzerTool"),
        ("tools.mitm_analyzer_tool",        "MitmAnalyzerTool"),
        ("tools.network_pentest_tool",      "NetworkPentestTool"),
    ]

    loaded = 0
    skipped = []
    for module_path, class_name in _catalogue:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance = cls()
            registry.register(instance)
            loaded += 1
        except Exception as exc:
            skipped.append(f"{module_path}.{class_name}: {exc}")

    if skipped:
        _log.getLogger(__name__).warning(
            "mcp_stdio: %d tools skipped:\n  %s", len(skipped), "\n  ".join(skipped)
        )

    return loaded


def _ensure_tools_loaded():
    global _tools_loaded
    if not _tools_loaded:
        load_tools()
        _tools_loaded = True


def _tool_schema(tool):
    definition = tool.get_definition()
    properties = {}
    required = []

    for param in definition.parameters:
        prop_schema = {"type": param.type, "description": param.description}
        if getattr(param, "choices", None):
            prop_schema["enum"] = param.choices
        if getattr(param, "default", None) is not None:
            prop_schema["default"] = param.default
        properties[param.name] = prop_schema
        if param.required:
            required.append(param.name)

    return {
        "name": definition.name,
        "description": definition.description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def handle_request(request):
    """Handle one MCP JSON-RPC request."""
    _ensure_tools_loaded()

    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id", 1)

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "ANA MAX", "version": "1.0"},
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"listChanged": True},
                    },
                },
            }

        if method == "tools/list":
            tools = []
            for name in registry.list_tools():
                tool = registry.get(name)
                if tool:
                    tools.append(_tool_schema(tool))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

        if method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            # Security: Validate and sanitize inputs
            if not isinstance(tool_name, str) or not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Invalid tool name"},
                }

            # Sanitize string arguments
            sanitized_args = {}
            for key, value in args.items():
                if isinstance(value, str):
                    sanitized_args[key] = _sanitize_string(value)
                elif isinstance(value, (int, float, bool, list, dict)):
                    sanitized_args[key] = value
                else:
                    sanitized_args[key] = str(value) if value is not None else None

            try:
                result = registry.execute(tool_name, **sanitized_args)
                payload = {
                    "success": result.is_success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                }
                if isinstance(result.data, dict) and isinstance(result.data.get("guidance_summary"), dict):
                    payload["guidance_summary"] = result.data["guidance_summary"]
            except Exception as exc:
                payload = {
                    "success": False,
                    "data": None,
                    "message": f"Tool execution error: {exc}",
                    "error": str(exc),
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, default=str),
                        }
                    ]
                },
            }

        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}

        if method == "resources/templates/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resourceTemplates": []}}

        if method == "prompts/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": str(exc)},
        }


def main():
    """Run the stdio JSON-RPC loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as exc:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            print(json.dumps(error_response), flush=True)
        except Exception as exc:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(exc)},
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
