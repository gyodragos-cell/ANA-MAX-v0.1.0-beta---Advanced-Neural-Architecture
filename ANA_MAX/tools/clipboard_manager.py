"""
ANA MAX - Clipboard Intelligence Tool
tools/clipboard_manager.py

Clipboard: citire, scriere, istoric, monitorizare, transformari
Win32 nativ + threading stdlib, zero dependente noi
"""

import logging
import threading
import time
import win32clipboard
from typing import Dict, Any, Optional, List
from collections import deque

logger = logging.getLogger(__name__)

# State intern
_history = deque(maxlen=100)
_monitor_active = False
_monitor_thread: Optional[threading.Thread] = None
_last_clipboard = ""
_lock = threading.Lock()


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """Clipboard manager entry point."""
    action = args.get("action")
    
    if action == "get":
        return _get_clipboard()
    elif action == "set":
        return _set_clipboard(args)
    elif action == "history":
        return _get_history(args)
    elif action == "clear_history":
        return _clear_history()
    elif action == "transform":
        return _transform_clipboard(args)
    elif action == "start_monitor":
        return _start_monitor()
    elif action == "stop_monitor":
        return _stop_monitor()
    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


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
