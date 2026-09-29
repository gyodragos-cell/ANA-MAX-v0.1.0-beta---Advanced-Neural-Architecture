"""
OS27 Hyper++ Tool Priority Map
Decide care tooluri sunt critice pentru orchestrator, UI, file analysis, system control.
"""

from typing import Dict, List

TOOL_PRIORITY = {
    "critical": [
        "LargeFileReaderHyperTool",
        "terminal_tool",
        "system_tool",
        "bash_exec_tool",
        "windows_uia_bridge",
        "desktop_capture",
        "ocr_tool",
        "clipboard_manager",
        "window_manager",
        "workspace_situational_awareness",
        "tool_healthcheck",
        "system_inspector_tool",
        "error_radar_tool",
        "project_navigator_tool",
        "file_patch_tool",
        "files",
        "unlimited_ocr_tool",
        "network_tool",
        "security_tool",
        "watchdog",
        "session_log_miner_tool",
        "agent_coach_tool",
    ],
    "secondary": [
        "frida_automation",
        "network_pentest_tool",
        "mitm_analyzer_tool",
        "vision_fallback_tool",
        "remote_control_tool",
        "browser_control",
    ],
    "optional": [
        "science_tool",
        "graph_context_pack_tool",
        "event_stream_tool",
        "todo_tool",
        "text_to_speech",
    ],
}


def get_priority(tool_name: str) -> str:
    """Get priority level for a tool name."""
    for level, tools in TOOL_PRIORITY.items():
        if tool_name in tools:
            return level
    return "optional"


def get_tools_by_priority(priority_level: str) -> List[str]:
    """Get all tools for a given priority level."""
    return TOOL_PRIORITY.get(priority_level, [])


def get_all_priorities() -> Dict[str, List[str]]:
    """Get the complete priority map."""
    return TOOL_PRIORITY.copy()


def is_critical(tool_name: str) -> bool:
    """Check if a tool is critical."""
    return tool_name in TOOL_PRIORITY.get("critical", [])


def is_secondary(tool_name: str) -> bool:
    """Check if a tool is secondary."""
    return tool_name in TOOL_PRIORITY.get("secondary", [])


def is_optional(tool_name: str) -> bool:
    """Check if a tool is optional."""
    return tool_name in TOOL_PRIORITY.get("optional", [])
