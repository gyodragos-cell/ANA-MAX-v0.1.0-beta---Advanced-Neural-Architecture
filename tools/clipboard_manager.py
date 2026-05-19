"""
ANA MAX - Clipboard Manager

Release-safe clipboard operations used by the AI Core adapter.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any, Dict, List


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
_HISTORY: List[str] = []


def _open_clipboard() -> None:
    if not user32.OpenClipboard(None):
        raise RuntimeError("Could not open clipboard")


def _get_text() -> str:
    _open_clipboard()
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _set_text(text: str) -> None:
    data = text + "\0"
    size = len(data) * ctypes.sizeof(wintypes.WCHAR)
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
    if not handle:
        raise RuntimeError("Could not allocate clipboard memory")
    ptr = kernel32.GlobalLock(handle)
    ctypes.memmove(ptr, ctypes.create_unicode_buffer(data), size)
    kernel32.GlobalUnlock(handle)

    _open_clipboard()
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, handle)
    finally:
        user32.CloseClipboard()


def _transform(text: str, operation: str) -> str:
    if operation == "upper":
        return text.upper()
    if operation == "lower":
        return text.lower()
    if operation == "title":
        return text.title()
    if operation == "strip":
        return text.strip()
    if operation == "reverse":
        return text[::-1]
    raise ValueError(f"Unknown transform operation: {operation}")


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    action = args.get("action", "get")

    if action == "get":
        text = _get_text()
        if text and (not _HISTORY or _HISTORY[-1] != text):
            _HISTORY.append(text)
        return {"status": "success", "text": text}

    if action == "set":
        text = args.get("text", "")
        _set_text(text)
        _HISTORY.append(text)
        return {"status": "success", "text": text}

    if action == "history":
        limit = int(args.get("limit") or 10)
        return {"status": "success", "history": _HISTORY[-limit:]}

    if action == "clear_history":
        _HISTORY.clear()
        return {"status": "success", "history": []}

    if action == "transform":
        text = _get_text()
        transformed = _transform(text, args.get("operation", "strip"))
        _set_text(transformed)
        _HISTORY.append(transformed)
        return {"status": "success", "text": transformed}

    if action in {"start_monitor", "stop_monitor"}:
        return {"status": "success", "message": "Clipboard monitor is not persistent in the clean release"}

    return {"status": "error", "error": f"Unknown action: {action}"}
