import logging
import json
import re
import time
import sys
from typing import Dict, Any, List

from tools.base import Tool, ToolResult, ToolStatus, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

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
        if not self._uia_available:
            error_msg = f"pywinauto library missing. "
            if self._import_error:
                error_msg += f"Import error: {self._import_error}"
            else:
                error_msg += "Run 'pip install pywinauto' first."
            logger.error(error_msg)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=error_msg
            )

        action = kwargs.get("action")
        if action == "list_windows":
            return self._list_windows()
        elif action == "inspect_window":
            return self._inspect_window(kwargs.get("window_title"))
        elif action == "click_element":
            return self._interact_element(
                kwargs.get("window_title"),
                kwargs.get("element_title"),
                kwargs.get("auto_id"),
                kwargs.get("control_type"),
                action="click"
            )
        elif action == "type_text":
            return self._interact_element(
                kwargs.get("window_title"),
                kwargs.get("element_title"),
                kwargs.get("auto_id"),
                kwargs.get("control_type"),
                action="type",
                text=kwargs.get("text")
            )
        else:
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
