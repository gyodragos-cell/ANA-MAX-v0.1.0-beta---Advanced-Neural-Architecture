"""
ANA MAX - Clipboard Intelligence Tool (OS27 Hyper++)
=======================================================
tools/clipboard_manager.py

Clipboard: citire, scriere, istoric, monitorizare, transformari
Win32 nativ + threading stdlib, zero dependente noi

OS27 Hyper++ Features:
- Telemetry tracking for clipboard operations (get, set, history, transform, monitor)
- Health monitoring for clipboard operations
- MemoryCortex integration for clipboard errors and history learning
- ContextEngine integration for clipboard state awareness
- SelfEvolvingTool integration for anomaly detection on clipboard failures
- Structured logging with error detection
"""

import logging
import threading
import time
import win32clipboard
from typing import Dict, Any, Optional
from collections import deque

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_clipboard_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_clipboard_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for clipboard operations."""
    if operation not in _clipboard_telemetry:
        _clipboard_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _clipboard_telemetry[operation]["operation_count"] += 1
    _clipboard_telemetry[operation]["total_time"] += execution_time
    _clipboard_telemetry[operation]["last_execution_time"] = execution_time
    _clipboard_telemetry[operation]["last_success"] = success
    
    if success:
        _clipboard_telemetry[operation]["success_count"] += 1
    else:
        _clipboard_telemetry[operation]["failure_count"] += 1


def get_clipboard_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for clipboard operations."""
    if operation:
        return _clipboard_telemetry.get(operation, {})
    return _clipboard_telemetry.copy()


def get_clipboard_health() -> str:
    """Get health status for clipboard tool based on telemetry."""
    if not _clipboard_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _clipboard_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _clipboard_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

# State intern
_history = deque(maxlen=100)
_monitor_active = False
_monitor_thread: Optional[threading.Thread] = None
_last_clipboard = ""
_lock = threading.Lock()


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """Clipboard manager entry point with OS27 Hyper++ telemetry.

    Backwards-compat: accepta atat ``action`` (nume corect) cat si ``operation``
    (nume din tool_router / LLM vechi) si include aliasuri uzuale:
      ``read`` / ``get`` -> _get_clipboard
      ``write`` / ``set`` / ``put`` -> _set_clipboard
      ``clear`` -> _clear_history
    Daca ``operation`` e una din [upper, lower, title, strip, reverse] se considera
    sub-operatie de transform (echivalent cu action=transform).
    """
    start_time = time.time()
    action = args.get("action") or args.get("operation") or "get"
    action = str(action).strip().lower()
    
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

    # Aliasuri pentru actiuni de top-level (inclusiv apelul cu operation='read' din log)
    _ACTION_ALIASES: Dict[str, str] = {
        "read": "get",
        "fetch": "get",
        "get": "get",
        "paste": "get",
        "write": "set",
        "put": "set",
        "copy": "set",
        "set": "set",
        "history": "history",
        "hist": "history",
        "clear": "clear_history",
        "clear_history": "clear_history",
        "reset": "clear_history",
        "transform": "transform",
        "start_monitor": "start_monitor",
        "monitor": "start_monitor",
        "stop_monitor": "stop_monitor",
    }

    # Sub-operatii de transform: daca vin direct ca operation (nume vechi)
    _TRANSFORM_OPS = {"upper", "lower", "title", "strip", "reverse"}

    if action in _TRANSFORM_OPS:
        # Intrare legacy: operation="upper" / "strip" etc.
        args = dict(args)
        args["operation"] = action
        result = _transform_clipboard(args)
        execution_time = time.time() - start_time
        success = result.get("status") == "success"
        _record_clipboard_telemetry(action, success, execution_time)
        
        # MemoryCortex integration for transform errors
        if cortex and not success:
            try:
                cortex.remember(
                    "error",
                    f"clipboard.transform.{action}",
                    f"Clipboard transform failed: {result.get('error', 'Unknown error')}"
                )
            except Exception:
                pass
        
        return result

    mapped = _ACTION_ALIASES.get(action)
    result = None
    
    if mapped == "get":
        result = _get_clipboard()
    elif mapped == "set":
        result = _set_clipboard(args)
    elif mapped == "history":
        result = _get_history(args)
    elif mapped == "clear_history":
        result = _clear_history()
    elif mapped == "transform":
        result = _transform_clipboard(args)
    elif mapped == "start_monitor":
        result = _start_monitor()
    elif mapped == "stop_monitor":
        result = _stop_monitor()
    else:
        valid = sorted(set(_ACTION_ALIASES.values()) | _TRANSFORM_OPS)
        result = {
            "status": "error",
            "error": (
                f"Invalid value for action/operation: {action!r}. "
                f"Valid top-level actions: {sorted(set(_ACTION_ALIASES.values()))}. "
                f"Valid transform operations: {sorted(_TRANSFORM_OPS)}. "
                f"Supported aliases: {sorted(_ACTION_ALIASES)}."
            ),
        }
    
    execution_time = time.time() - start_time
    success = result.get("status") == "success"
    _record_clipboard_telemetry(mapped or action, success, execution_time)
    
    # MemoryCortex integration for clipboard errors
    if cortex and not success:
        try:
            cortex.remember(
                "error",
                f"clipboard.{mapped or action}",
                f"Clipboard operation failed: {result.get('error', 'Unknown error')}"
            )
        except Exception:
            pass
    
    # ContextEngine integration for clipboard state
    if context_engine and success and mapped == "get":
        try:
            context_engine.update_context(
                key="clipboard_state",
                value={
                    "content_length": result.get("length", 0),
                    "timestamp": time.time(),
                }
            )
        except Exception:
            pass
    
    return result


def _get_clipboard() -> Dict[str, Any]:
    """Get current clipboard content."""
    try:
        win32clipboard.OpenClipboard()
        content = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        
        return {
            "status": "success",
            "content": content,
            "length": len(content)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _set_clipboard(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set clipboard content."""
    try:
        text = args.get("text", "")
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        
        # Add to history
        with _lock:
            _history.append(text)
        
        return {
            "status": "success",
            "message": "Clipboard content set",
            "length": len(text)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_history(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get clipboard history."""
    try:
        limit = args.get("limit", 10)
        
        with _lock:
            history_list = list(_history)[-limit:]
        
        return {
            "status": "success",
            "history": history_list,
            "count": len(history_list)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _clear_history() -> Dict[str, Any]:
    """Clear clipboard history."""
    try:
        with _lock:
            _history.clear()
        
        return {
            "status": "success",
            "message": "Clipboard history cleared"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _transform_clipboard(args: Dict[str, Any]) -> Dict[str, Any]:
    """Transform clipboard content."""
    try:
        operation = args.get("operation", "upper")
        
        # Get current content
        win32clipboard.OpenClipboard()
        content = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        
        # Apply transformation
        if operation == "upper":
            transformed = content.upper()
        elif operation == "lower":
            transformed = content.lower()
        elif operation == "title":
            transformed = content.title()
        elif operation == "strip":
            transformed = content.strip()
        elif operation == "reverse":
            transformed = content[::-1]
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}
        
        # Set transformed content
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(transformed, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        
        # Add to history
        with _lock:
            _history.append(transformed)
        
        return {
            "status": "success",
            "operation": operation,
            "original_length": len(content),
            "transformed_length": len(transformed)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _start_monitor() -> Dict[str, Any]:
    """Start clipboard monitoring."""
    global _monitor_active, _monitor_thread, _last_clipboard
    
    try:
        if _monitor_active:
            return {"status": "success", "message": "Monitor already running"}
        
        _monitor_active = True
        
        # Get initial clipboard content
        try:
            win32clipboard.OpenClipboard()
            _last_clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except Exception as e:
            _last_clipboard = ""
        
        def monitor_loop():
            global _last_clipboard
            while _monitor_active:
                try:
                    win32clipboard.OpenClipboard()
                    current = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    
                    if current != _last_clipboard:
                        _last_clipboard = current
                        with _lock:
                            _history.append(current)
                        logger.info(f"Clipboard changed: {current[:50]}...")
                except Exception as e:
                    pass
                
                time.sleep(0.5)
        
        _monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        _monitor_thread.start()
        
        return {
            "status": "success",
            "message": "Clipboard monitoring started"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _stop_monitor() -> Dict[str, Any]:
    """Stop clipboard monitoring."""
    global _monitor_active
    
    try:
        _monitor_active = False
        
        if _monitor_thread:
            _monitor_thread.join(timeout=2)
        
        return {
            "status": "success",
            "message": "Clipboard monitoring stopped"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


class ClipboardManagerTool(Tool):
    """Standard Tool wrapper for clipboard operations."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="clipboard_manager",
            description="Clipboard intelligence: read, write, history, transform, monitor.",
            parameters=[
                ToolParameter("action", "get, set, history, clear_history, transform, start_monitor, stop_monitor", "string", False),
                ToolParameter("text", "Text to set in clipboard", "string", False),
                ToolParameter("operation", "Transform operation: upper, lower, title, strip, reverse", "string", False),
                ToolParameter("limit", "History limit", "integer", False),
            ],
            category="desktop",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        result = run(kwargs)
        if result.get("status") == "success":
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result.get("message", "Clipboard operation complete"))
        return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Clipboard operation failed"), data=result)
