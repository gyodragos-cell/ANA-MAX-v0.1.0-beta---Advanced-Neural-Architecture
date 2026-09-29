"""
OS27 Hyper++ Tool Health Dashboard
Monitorizeaza telemetria tuturor toolurilor si calculeaza health scoring.
"""

from typing import Any, Dict
from tools.tool_priority_map import get_priority

# Health computation based on telemetry stats
def compute_health(stats: Dict[str, Any]) -> str:
    """Compute health status from telemetry statistics."""
    if not stats or stats.get("operation_count", 0) == 0:
        return "unknown"
    
    failure_count = stats.get("failure_count", 0)
    success_count = stats.get("success_count", 0)
    
    if failure_count == 0:
        return "healthy"
    if failure_count < success_count:
        return "degraded"
    return "broken"


def compute_health_score(stats: Dict[str, Any]) -> float:
    """Compute a numeric health score (0-100) from telemetry statistics."""
    if not stats or stats.get("operation_count", 0) == 0:
        return 50.0
    
    total_ops = stats.get("operation_count", 1)
    success_count = stats.get("success_count", 0)
    failure_count = stats.get("failure_count", 0)
    
    if total_ops == 0:
        return 50.0
    
    success_rate = success_count / total_ops
    return round(success_rate * 100, 2)


def get_tool_health_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive health dashboard for all tools.
    Aggregates telemetry from individual tool modules.
    """
    dashboard = {
        "schema": "ana.tool_health_dashboard.v1",
        "summary": {
            "total_tools": 0,
            "healthy": 0,
            "degraded": 0,
            "broken": 0,
            "unknown": 0,
        },
        "tools": {},
    }
    
    # Import telemetry functions from modernized tools
    # This is a registry of tools that have OS27 Hyper++ telemetry
    telemetry_functions = {
        "terminal_tool": ("tools.terminal_tool", "get_terminal_telemetry", "get_terminal_health"),
        "windows_uia_bridge": ("tools.windows_uia_bridge", "get_windows_uia_telemetry", "get_windows_uia_health"),
        "desktop_capture": ("tools.desktop_capture", "get_desktop_capture_telemetry", "get_desktop_capture_health"),
        "ocr_tool": ("tools.ocr_tool", "get_ocr_telemetry", "get_ocr_health"),
        "clipboard_manager": ("tools.clipboard_manager", "get_clipboard_telemetry", "get_clipboard_health"),
        "window_manager": ("tools.window_manager", "get_window_telemetry", "get_window_health"),
        "workspace_situational_awareness": ("tools.workspace_situational_awareness", "get_workspace_telemetry", "get_workspace_health"),
        "tool_healthcheck": ("tools.tool_healthcheck", "get_healthcheck_telemetry", "get_healthcheck_health"),
        "system_inspector_tool": ("tools.system_inspector_tool", "get_system_inspector_telemetry", "get_system_inspector_health"),
        "error_radar_tool": ("tools.error_radar_tool", "get_error_radar_telemetry", "get_error_radar_health"),
        "project_navigator_tool": ("tools.project_navigator_tool", "get_project_navigator_telemetry", "get_project_navigator_health"),
        "file_patch_tool": ("tools.file_patch_tool", "get_file_patch_telemetry", "get_file_patch_health"),
        "file_operations": ("tools.files", "get_file_operations_telemetry", "get_file_operations_health"),
        "unlimited_ocr_tool": ("tools.unlimited_ocr_tool", "get_unlimited_ocr_telemetry", "get_unlimited_ocr_health"),
        "network_tool": ("tools.network_tool", "get_network_telemetry", "get_network_health"),
        "security_tool": ("tools.security_tool", "get_security_telemetry", "get_security_health"),
        "system_tool": ("tools.system_tool", "get_system_telemetry", "get_system_health"),
        "watchdog": ("tools.watchdog", "get_watchdog_telemetry", "get_watchdog_health"),
        "frida_automation": ("tools.frida_automation", "get_frida_telemetry", "get_frida_health"),
        "network_pentest_tool": ("tools.network_pentest_tool", "get_network_pentest_telemetry", "get_network_pentest_health"),
        "mitm_analyzer_tool": ("tools.mitm_analyzer_tool", "get_mitm_analyzer_telemetry", "get_mitm_analyzer_health"),
        "session_log_miner_tool": ("tools.session_log_miner_tool", "get_session_log_miner_telemetry", "get_session_log_miner_health"),
        "agent_coach": ("tools.agent_coach_tool", "get_agent_coach_telemetry", "get_agent_coach_health"),
        "code_tool": ("tools.code", "get_code_telemetry", "get_code_health"),
        "browser_control": ("tools.browser_control", "get_browser_control_telemetry", "get_browser_control_health"),
        "git_tool": ("tools.git_tool", "get_git_telemetry", "get_git_health"),
        "web_tool": ("tools.web_tool", "get_web_telemetry", "get_web_health"),
        "memory_tool": ("tools.memory_tool", "get_memory_telemetry", "get_memory_health"),
        "skill_tool": ("tools.skill_tool", "get_skill_telemetry", "get_skill_health"),
        "tool_router_tool": ("tools.tool_router_tool", "get_router_telemetry", "get_router_health"),
        "conversation_learning_tool": ("tools.conversation_learning_tool", "get_conversation_learning_telemetry", "get_conversation_learning_health"),
        "session_checkpoint_tool": ("tools.session_checkpoint_tool", "get_session_checkpoint_telemetry", "get_session_checkpoint_health"),
        "session_audit_tool": ("tools.session_audit_tool", "get_session_audit_telemetry", "get_session_audit_health"),
        "session_rem_sleep_tool": ("tools.session_rem_sleep_tool", "get_rem_sleep_telemetry", "get_rem_sleep_health"),
        "ana_context_tool": ("tools.ana_context_tool", "get_ana_context_telemetry", "get_ana_context_health"),
    }
    
    for tool_name, (module_path, telemetry_func, health_func) in telemetry_functions.items():
        try:
            module = __import__(module_path, fromlist=[telemetry_func, health_func])
            get_telemetry = getattr(module, telemetry_func, None)
            get_health = getattr(module, health_func, None)
            
            stats = get_telemetry() if get_telemetry else {}
            health = get_health() if get_health else "unknown"
            priority = get_priority(tool_name)
            
            # Compute overall stats from per-operation telemetry
            total_ops = sum(s.get("operation_count", 0) for s in stats.values() if isinstance(s, dict))
            total_success = sum(s.get("success_count", 0) for s in stats.values() if isinstance(s, dict))
            total_failure = sum(s.get("failure_count", 0) for s in stats.values() if isinstance(s, dict))
            total_time = sum(s.get("total_time", 0) for s in stats.values() if isinstance(s, dict))
            
            overall_stats = {
                "operation_count": total_ops,
                "success_count": total_success,
                "failure_count": total_failure,
                "total_time": total_time,
                "avg_time": round(total_time / total_ops, 4) if total_ops > 0 else 0,
            }
            
            dashboard["tools"][tool_name] = {
                "priority": priority,
                "health": health,
                "health_score": compute_health_score(overall_stats),
                "stats": overall_stats,
                "operations": stats,
            }
            
            dashboard["summary"]["total_tools"] += 1
            if health == "healthy":
                dashboard["summary"]["healthy"] += 1
            elif health == "degraded":
                dashboard["summary"]["degraded"] += 1
            elif health == "broken":
                dashboard["summary"]["broken"] += 1
            else:
                dashboard["summary"]["unknown"] += 1
        except Exception:
            # Tool not modernized or import failed
            dashboard["tools"][tool_name] = {
                "priority": get_priority(tool_name),
                "health": "unknown",
                "health_score": 0.0,
                "stats": {},
                "operations": {},
                "error": "telemetry_not_available",
            }
            dashboard["summary"]["total_tools"] += 1
            dashboard["summary"]["unknown"] += 1
    
    return dashboard


def get_critical_tools_health() -> Dict[str, Any]:
    """Get health status for critical tools only."""
    dashboard = get_tool_health_dashboard()
    critical_tools = {k: v for k, v in dashboard["tools"].items() if v.get("priority") == "critical"}
    return {
        "schema": "ana.critical_tools_health.v1",
        "tools": critical_tools,
        "summary": {
            "total": len(critical_tools),
            "healthy": sum(1 for v in critical_tools.values() if v.get("health") == "healthy"),
            "degraded": sum(1 for v in critical_tools.values() if v.get("health") == "degraded"),
            "broken": sum(1 for v in critical_tools.values() if v.get("health") == "broken"),
        },
    }


def get_broken_tools() -> list[str]:
    """Get list of tools with broken health status."""
    dashboard = get_tool_health_dashboard()
    return [name for name, info in dashboard["tools"].items() if info.get("health") == "broken"]


def get_degraded_tools() -> list[str]:
    """Get list of tools with degraded health status."""
    dashboard = get_tool_health_dashboard()
    return [name for name, info in dashboard["tools"].items() if info.get("health") == "degraded"]
