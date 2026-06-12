"""
ANA MAX - Window Management Tool
tools/window_manager.py

Gestionare ferestre: listare, snap, move, tile, focus
Win32 nativ, zero dependente noi
"""

import logging
import win32gui
import win32con
import win32api
from typing import Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """Window manager entry point."""
    action = args.get("action")
    
    if action == "list":
        return _list_windows(args)
    elif action == "focus":
        return _focus_window(args)
    elif action == "snap":
        return _snap_window(args)
    elif action == "tile":
        return _tile_windows(args)
    elif action == "minimize":
        return _minimize_window(args)
    elif action == "maximize":
        return _maximize_window(args)
    elif action == "close":
        return _close_window(args)
    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


def _list_windows(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all visible windows."""
    try:
        windows = []
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append({
                        "hwnd": hwnd,
                        "title": title
                    })
            return True
        
        win32gui.EnumWindows(callback, None)
        
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
        
        win32gui.EnumWindows(callback, None)
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
        
        win32gui.EnumWindows(callback, None)
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
        win32gui.EnumWindows(callback, None)
        
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
        
        win32gui.EnumWindows(callback, None)
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
        
        win32gui.EnumWindows(callback, None)
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
        
        win32gui.EnumWindows(callback, None)
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
