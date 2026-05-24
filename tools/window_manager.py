"""
ANA MAX - Window Manager

Release-safe Windows window operations used by the AI Core adapter.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any, Dict, List, Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


user32 = ctypes.windll.user32

SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _visible_windows() -> List[Dict[str, Any]]:
    windows: List[Dict[str, Any]] = []

    def enum_proc(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            title = _window_title(hwnd)
            if title:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                windows.append({
                    "handle": int(hwnd),
                    "title": title,
                    "x": rect.left,
                    "y": rect.top,
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top,
                })
        return True

    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_proc)
    user32.EnumWindows(callback, 0)
    return windows


def _find_window(title: Optional[str]) -> Optional[int]:
    if not title:
        return user32.GetForegroundWindow()
    needle = title.lower()
    for item in _visible_windows():
        if needle in item["title"].lower():
            return item["handle"]
    return None


def _work_area() -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    action = args.get("action", "list")
    title = args.get("title")

    if action == "list":
        return {"status": "success", "windows": _visible_windows()}

    hwnd = _find_window(title)
    if not hwnd:
        return {"status": "error", "error": f"Window not found: {title or '<active>'}"}

    if action == "focus":
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return {"status": "success", "handle": int(hwnd)}

    if action == "minimize":
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        return {"status": "success", "handle": int(hwnd)}

    if action == "maximize":
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        return {"status": "success", "handle": int(hwnd)}

    if action == "close":
        user32.PostMessageW(hwnd, 0x0010, 0, 0)
        return {"status": "success", "handle": int(hwnd)}

    if action in {"move", "snap"}:
        left, top, width, height = _work_area()
        position = args.get("position", "left")
        if position == "left":
            target = (left, top, width // 2, height)
        elif position == "right":
            target = (left + width // 2, top, width // 2, height)
        elif position == "top":
            target = (left, top, width, height // 2)
        elif position == "bottom":
            target = (left, top + height // 2, width, height // 2)
        else:
            target = (left, top, width, height)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.MoveWindow(hwnd, *target, True)
        return {"status": "success", "handle": int(hwnd), "rect": target}

    if action == "tile":
        return {"status": "error", "error": "Tile is not implemented in the clean release"}

    return {"status": "error", "error": f"Unknown action: {action}"}


class WindowManagerTool(Tool):
    """Standard Tool wrapper for native Win32 window management."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="window_manager",
            description="Window management: list, snap, move, focus, minimize, maximize, close windows.",
            parameters=[
                ToolParameter("action", "Action to perform", "string", True, choices=["list", "snap", "move", "focus", "minimize", "maximize", "close", "tile"]),
                ToolParameter("title", "Partial window title; defaults to active window for window actions", "string", False),
                ToolParameter("position", "Snap position", "string", False, choices=["left", "right", "top", "bottom"]),
            ],
            category="desktop",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        result = run(kwargs)
        if result.get("status") == "success":
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result.get("message", "Window action complete"))
        return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Window action failed"), data=result)
