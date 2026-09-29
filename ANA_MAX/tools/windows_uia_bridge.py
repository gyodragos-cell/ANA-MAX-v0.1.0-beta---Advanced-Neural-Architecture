"""
ANA MAX - Windows UIA Bridge Tool (OS27 Hyper++)
==================================================
Eyes and hands of ANA MAX (via Microsoft UI Automation).

OS27 Hyper++ Features:
- Telemetry tracking for UI operations (list, inspect, click, type)
- Health monitoring for UI automation stability
- MemoryCortex integration for UI state and error learning
- ContextEngine integration for UI awareness
- SelfEvolvingTool integration for anomaly detection on UI failures
- Structured logging with error detection
"""

import logging
import json
import re
import time
import sys
from typing import Dict, Any, List

from tools.base import Tool, ToolResult, ToolStatus, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_uia_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_uia_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for UIA operations."""
    if operation not in _uia_telemetry:
        _uia_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _uia_telemetry[operation]["operation_count"] += 1
    _uia_telemetry[operation]["total_time"] += execution_time
    _uia_telemetry[operation]["last_execution_time"] = execution_time
    _uia_telemetry[operation]["last_success"] = success
    
    if success:
        _uia_telemetry[operation]["success_count"] += 1
    else:
        _uia_telemetry[operation]["failure_count"] += 1


def get_uia_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for UIA operations."""
    if operation:
        return _uia_telemetry.get(operation, {})
    return _uia_telemetry.copy()


def get_uia_health() -> str:
    """Get health status for UIA tool based on telemetry."""
    if not _uia_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _uia_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _uia_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

class WindowsUiaBridgeTool(Tool):
    """Eyes and hands of ANA MAX (via Microsoft UI Automation)."""

    def get_definition(self):
        return ToolDefinition(
            name="windows_uia_bridge",
            description=(
                "Eyes and hands of ANA MAX (via Microsoft UI Automation). "
                "Reads window structure tree, clicks elements, types text "
                "without using OCR or visual coordinates."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform: list_windows, inspect_window, click_element, type_text.",
                    type="string",
                    required=True,
                    choices=["list_windows", "inspect_window", "click_element", "type_text"]
                ),
                ToolParameter(
                    name="window_title",
                    description="Partial or complete window name (for inspect_window, click_element, type_text).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="element_title",
                    description="UI element name/text (for click or type).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="auto_id",
                    description="Element AutomationId (if known).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="control_type",
                    description="Element type (e.g., Button, Edit, MenuItem).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="text",
                    description="Text to type (for type_text action).",
                    type="string",
                    required=False
                )
            ],
            category="desktop",
            dangerous=True,
        )

    def __init__(self):
        self._uia_available = False
        self._import_error = None
        try:
            import pywinauto
            self._uia_available = True
            logger.info(f"pywinauto loaded successfully: {pywinauto.__version__}")
        except ImportError as e:
            self._import_error = str(e)
            logger.error(f"pywinauto import failed: {e}")
            logger.error(f"Python path: {sys.path[:3]}")

    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        if not self._uia_available:
            error_msg = f"pywinauto library missing. "
            if self._import_error:
                error_msg += f"Import error: {self._import_error}"
            else:
                error_msg += "Run 'pip install pywinauto' first."
            logger.error(error_msg)
            _record_uia_telemetry("execute", False, time.time() - start_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=error_msg
            )

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

        action = kwargs.get("action")
        if action == "list_windows":
            result = self._list_windows()
            execution_time = time.time() - start_time
            success = result.status == ToolStatus.SUCCESS
            _record_uia_telemetry(action, success, execution_time)
            
            # ContextEngine integration for window list
            if context_engine and success:
                try:
                    context_engine.update_context(
                        key="ui_windows",
                        value={
                            "window_count": result.data.get("count", 0),
                            "windows": result.data.get("windows", [])[:10],  # Limit to 10
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            return result
        elif action == "inspect_window":
            result = self._inspect_window(kwargs.get("window_title"))
            execution_time = time.time() - start_time
            success = result.status == ToolStatus.SUCCESS
            _record_uia_telemetry(action, success, execution_time)
            
            # MemoryCortex integration for window structure
            if cortex and success:
                try:
                    cortex.remember(
                        "episodic",
                        f"uia.inspect.{kwargs.get('window_title')}",
                        f"Inspected window: {result.data.get('window_title')} with {result.data.get('count')} elements"
                    )
                except Exception:
                    pass
            
            # ContextEngine integration for window structure
            if context_engine and success:
                try:
                    context_engine.update_context(
                        key="active_window_structure",
                        value={
                            "window_title": result.data.get("window_title"),
                            "element_count": result.data.get("count"),
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            return result
        elif action == "click_element":
            result = self._interact_element(
                kwargs.get("window_title"),
                kwargs.get("element_title"),
                kwargs.get("auto_id"),
                kwargs.get("control_type"),
                action="click"
            )
            execution_time = time.time() - start_time
            success = result.status == ToolStatus.SUCCESS
            _record_uia_telemetry(action, success, execution_time)
            
            # MemoryCortex integration for click errors
            if cortex and not success:
                try:
                    cortex.remember(
                        "error",
                        f"uia.click.{kwargs.get('window_title')}",
                        f"Click failed on element: {kwargs.get('element_title')} or {kwargs.get('auto_id')}"
                    )
                except Exception:
                    pass
            
            return result
        elif action == "type_text":
            result = self._interact_element(
                kwargs.get("window_title"),
                kwargs.get("element_title"),
                kwargs.get("auto_id"),
                kwargs.get("control_type"),
                action="type",
                text=kwargs.get("text")
            )
            execution_time = time.time() - start_time
            success = result.status == ToolStatus.SUCCESS
            _record_uia_telemetry(action, success, execution_time)
            
            # MemoryCortex integration for type errors
            if cortex and not success:
                try:
                    cortex.remember(
                        "error",
                        f"uia.type.{kwargs.get('window_title')}",
                        f"Type failed on element: {kwargs.get('element_title')} or {kwargs.get('auto_id')}"
                    )
                except Exception:
                    pass
            
            return result
        else:
            _record_uia_telemetry(action, False, time.time() - start_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")

    def _list_windows(self) -> ToolResult:
        try:
            win_list = []
            try:
                import win32gui

                def _collect(hwnd, _extra):
                    if not win32gui.IsWindowVisible(hwnd):
                        return
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return
                    win_list.append({
                        "title": title,
                        "class": win32gui.GetClassName(hwnd),
                        "handle": hwnd
                    })

                win32gui.EnumWindows(_collect, None)
            except Exception:
                import pywinauto

                windows = pywinauto.Desktop(backend="win32").windows(visible_only=True)
                for w in windows:
                    title = w.window_text()
                    if title:
                        win_list.append({
                            "title": title,
                            "class": w.class_name(),
                            "handle": w.handle
                        })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"windows": win_list, "count": len(win_list)},
                message=f"Am gasit {len(win_list)} ferestre vizibile."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la listarea ferestrelor: {e}")

    def _inspect_window(self, title: str) -> ToolResult:
        if not title:
            return ToolResult(status=ToolStatus.ERROR, error="window_title este obligatoriu pentru inspect_window.")

        import pywinauto
        try:
            app = pywinauto.Desktop(backend="uia")
            wins = app.windows(title_re=f".*{re.escape(title)}.*", visible_only=True)
            if not wins:
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{title}' nu a fost gasita.")
            win = wins[0]

            elements = []
            for ctrl in win.descendants():
                try:
                    elem_title = ctrl.window_text()
                    auto_id = ctrl.automation_id()
                    ctrl_type = ctrl.element_info.control_type
                    if elem_title or auto_id:
                        elements.append({
                            "title": elem_title,
                            "auto_id": auto_id,
                            "control_type": ctrl_type
                        })
                except Exception:
                    pass

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"window_title": win.window_text(), "elements": elements, "count": len(elements)},
                message=f"Am mapat fereastra '{win.window_text()}' ({len(elements)} elemente interactionabile)."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la inspectare fereastra: {e}")

    def _interact_element(self, win_title, elem_title, auto_id, ctrl_type, action="click", text="") -> ToolResult:
        if not win_title:
            return ToolResult(status=ToolStatus.ERROR, error="window_title este obligatoriu.")

        if not elem_title and not auto_id and not ctrl_type:
            return ToolResult(status=ToolStatus.ERROR, error="Specifica element_title, auto_id sau control_type.")

        import pywinauto
        try:
            desktop = pywinauto.Desktop(backend="uia")
            wins = desktop.windows(title_re=f".*{re.escape(win_title)}.*", visible_only=True)
            if not wins:
                logger.error(f"Fereastra '{win_title}' nu a fost gasita")
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{win_title}' nu a fost gasita.")
            win = wins[0]

            search_args = {
                "auto_id": auto_id,
                "title": elem_title,
                "control_type": ctrl_type,
            }

            ctrl = None
            for candidate in win.descendants():
                try:
                    candidate_title = candidate.window_text()
                    candidate_auto_id = candidate.automation_id()
                    candidate_type = candidate.element_info.control_type
                    title_ok = not elem_title or elem_title.lower() in (candidate_title or "").lower()
                    auto_id_ok = not auto_id or auto_id == candidate_auto_id
                    type_ok = not ctrl_type or ctrl_type == candidate_type or (
                        ctrl_type == "Edit" and candidate_type in {"Edit", "Document"}
                    )
                    if title_ok and auto_id_ok and type_ok:
                        ctrl = candidate
                        break
                except Exception:
                    continue

            if ctrl is None:
                return ToolResult(status=ToolStatus.ERROR, error=f"Element {search_args} nu a fost gasit in fereastra.")

            if action == "click":
                try:
                    # Try invoke() first (works better for UWP apps like Calculator)
                    ctrl.invoke()
                    logger.info(f"Invoke pe elementul '{elem_title or auto_id}'")
                except Exception:
                    # Fallback to click_input() for Win32 apps
                    try:
                        ctrl.click_input()
                        logger.info(f"Click vizual pe elementul '{elem_title or auto_id}'")
                    except Exception as e2:
                        return ToolResult(status=ToolStatus.ERROR, error=f"Nu am putut da click: {e2}")
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Am dat click pe elementul '{elem_title or auto_id}'."
                )
            elif action == "type":
                ctrl.set_focus()
                import pywinauto.keyboard
                pywinauto.keyboard.send_keys(text, with_spaces=True)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Am scris textul in elementul '{elem_title or auto_id}'."
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la actiunea {action}: {e}")
