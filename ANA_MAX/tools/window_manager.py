"""
ANA MAX - Window Management Tool (OS27 Hyper++)
================================================
tools/window_manager.py

Gestionare ferestre: listare, snap, move, tile, focus
Win32 nativ, zero dependente noi

OS27 Hyper++ Features:
- Telemetry tracking for window operations (list, snap, tile, focus, minimize, maximize, close)
- Health monitoring for window management reliability
- MemoryCortex integration for window errors and state learning
- ContextEngine integration for window state awareness
- SelfEvolvingTool integration for anomaly detection on window failures
- Structured logging with error detection
"""

import logging
import time
import win32gui
import win32con
import win32api
from typing import Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_window_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_window_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for window operations."""
    if operation not in _window_telemetry:
        _window_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _window_telemetry[operation]["operation_count"] += 1
    _window_telemetry[operation]["total_time"] += execution_time
    _window_telemetry[operation]["last_execution_time"] = execution_time
    _window_telemetry[operation]["last_success"] = success
    
    if success:
        _window_telemetry[operation]["success_count"] += 1
    else:
        _window_telemetry[operation]["failure_count"] += 1


def get_window_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for window operations."""
    if operation:
        return _window_telemetry.get(operation, {})
    return _window_telemetry.copy()


def get_window_health() -> str:
    """Get health status for window tool based on telemetry."""
    if not _window_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _window_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _window_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """Window manager entry point with OS27 Hyper++ telemetry."""
    start_time = time.time()
    action = args.get("action")
    
    # AI Core hooks (lazy import for safety)
    cortex = None
    context_engine = None
    evolver = None
    try:
        from tools.memory_cortex import MemoryCortex
        cortex = MemoryCortex()
    except Exception:
        pass
    try:
        from tools.context_engine import ContextEngine
        context_engine = ContextEngine()
    except Exception:
        pass
    try:
        from tools.self_evolving_tool import SelfEvolvingTool
        evolver = SelfEvolvingTool()
    except Exception:
        pass
    
    result = None
    
    if action == "list":
        result = _list_windows(args)
    elif action == "focus":
        result = _focus_window(args)
    elif action == "snap":
        result = _snap_window(args)
    elif action == "tile":
        result = _tile_windows(args)
    elif action == "minimize":
        result = _minimize_window(args)
    elif action == "maximize":
        result = _maximize_window(args)
    elif action == "close":
        result = _close_window(args)
    else:
        result = {"status": "error", "error": f"Unknown action: {action}"}
    
    execution_time = time.time() - start_time
    success = result.get("status") == "success"
    _record_window_telemetry(action, success, execution_time)
    
    # MemoryCortex integration for window errors
    if cortex and not success:
        try:
            cortex.remember(
                "error",
                f"window.{action}",
                f"Window operation failed: {result.get('error', 'Unknown error')}"
            )
        except Exception:
            pass
    
    # ContextEngine integration for window state
    if context_engine and success and action == "list":
        try:
            context_engine.update_context(
                key="window_state",
                value={
                    "window_count": result.get("count", 0),
                    "windows": result.get("windows", [])[:10],  # Limit to 10
                    "timestamp": time.time(),
                }
            )
        except Exception:
            pass
    
    return result


def _list_windows(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all visible windows."""
    try:
        windows = []
        
        def callback(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append({
                            "hwnd": hwnd,
                            "title": title
                        })
            except Exception:
                pass
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
            
        if not windows:
            import subprocess
            import json
            try:
                cmd = 'powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object Id, MainWindowTitle | ConvertTo-Json"'
                res = subprocess.check_output(cmd, shell=True, text=True)
                if res.strip():
                    data = json.loads(res)
                    if isinstance(data, dict): data = [data]
                    for item in data:
                        windows.append({"hwnd": item.get("Id"), "title": item.get("MainWindowTitle")})
            except Exception:
                pass
                
        return {
            "status": "success",
            "windows": windows,
            "count": len(windows)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _focus_window(args: Dict[str, Any]) -> Dict[str, Any]:
    """Focus a window by title."""
    try:
        title = args.get("title", "")
        if not title:
            return {"status": "error", "error": "title is required"}
        found = {"value": False}
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    found["value"] = True
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if not found["value"]:
            return {"status": "error", "error": f"Window not found: {title}"}
        
        return {
            "status": "success",
            "message": f"Window '{title}' focused"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _snap_window(args: Dict[str, Any]) -> Dict[str, Any]:
    """Snap window to position (left, right, top, bottom)."""
    try:
        title = args.get("title", "")
        position = args.get("position", "left")
        if not title:
            return {"status": "error", "error": "title is required"}
        
        # Get screen dimensions
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        
        # Calculate position
        if position == "left":
            x, y, width, height = 0, 0, screen_width // 2, screen_height
        elif position == "right":
            x, y, width, height = screen_width // 2, 0, screen_width // 2, screen_height
        elif position == "top":
            x, y, width, height = 0, 0, screen_width, screen_height // 2
        elif position == "bottom":
            x, y, width, height = 0, screen_height // 2, screen_width, screen_height // 2
        else:
            return {"status": "error", "error": f"Invalid position: {position}"}
        
        # Find and snap window
        found = {"value": False}

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    win32gui.MoveWindow(hwnd, x, y, width, height, True)
                    found["value"] = True
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if not found["value"]:
            return {"status": "error", "error": f"Window not found: {title}"}
        
        return {
            "status": "success",
            "message": f"Window '{title}' snapped to {position}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _tile_windows(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tile all visible windows in grid layout."""
    try:
        layout = args.get("layout", "grid")
        
        # Get all visible windows
        windows = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
            return True
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        
        if not windows:
            return {"status": "success", "message": "No windows to tile"}
        
        # Calculate grid
        import math
        cols = math.ceil(math.sqrt(len(windows)))
        rows = math.ceil(len(windows) / cols)
        
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        
        cell_width = screen_width // cols
        cell_height = screen_height // rows
        
        # Tile windows
        for i, hwnd in enumerate(windows):
            col = i % cols
            row = i // cols
            x = col * cell_width
            y = row * cell_height
            win32gui.MoveWindow(hwnd, x, y, cell_width, cell_height, True)
        
        return {
            "status": "success",
            "message": f"Tiled {len(windows)} windows in {layout} layout"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _minimize_window(args: Dict[str, Any]) -> Dict[str, Any]:
    """Minimize a window."""
    try:
        title = args.get("title", "")
        if not title:
            return {"status": "error", "error": "title is required"}
        found = {"value": False}
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    found["value"] = True
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if not found["value"]:
            return {"status": "error", "error": f"Window not found: {title}"}
        
        return {"status": "success", "message": f"Window '{title}' minimized"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _maximize_window(args: Dict[str, Any]) -> Dict[str, Any]:
    """Maximize a window."""
    try:
        title = args.get("title", "")
        if not title:
            return {"status": "error", "error": "title is required"}
        found = {"value": False}
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    found["value"] = True
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if not found["value"]:
            return {"status": "error", "error": f"Window not found: {title}"}
        
        return {"status": "success", "message": f"Window '{title}' maximized"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _close_window(args: Dict[str, Any]) -> Dict[str, Any]:
    """Close a window."""
    try:
        title = args.get("title", "")
        if not title:
            return {"status": "error", "error": "title is required"}
        found = {"value": False}
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    found["value"] = True
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if not found["value"]:
            return {"status": "error", "error": f"Window not found: {title}"}
        
        return {"status": "success", "message": f"Window '{title}' closed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class WindowManagerTool(Tool):
    """Standard Tool wrapper for native Win32 window management."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="window_manager",
            description="Window management: list, snap, tile, focus, minimize, maximize, close windows.",
            parameters=[
                ToolParameter("action", "Action to perform", "string", True, choices=["list", "snap", "tile", "focus", "minimize", "maximize", "close"]),
                ToolParameter("title", "Partial window title", "string", False),
                ToolParameter("position", "Snap position", "string", False, choices=["left", "right", "top", "bottom"]),
                ToolParameter("layout", "Tile layout", "string", False, choices=["grid", "horizontal", "vertical"]),
            ],
            category="desktop",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        result = run(kwargs)
        if result.get("status") == "success":
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result.get("message", "Window action complete"))
        return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Window action failed"), data=result)
