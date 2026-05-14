import logging
import json
import time
import sys
from typing import Dict, Any, List

from tools.base import Tool, ToolResult, ToolStatus, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

class WindowsUiaBridgeTool(Tool):
    """Ochii și mâinile ANA MAX (via Microsoft UI Automation)."""

    def get_definition(self):
        return ToolDefinition(
            name="windows_uia_bridge",
            description=(
                "Ochii și mâinile ANA MAX (via Microsoft UI Automation). "
                "Citește arborele structural al ferestrelor, dă click pe elemente și scrie text "
                "fără să folosească OCR sau coordonate vizuale."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Acțiunea pe care dorești să o faci: list_windows, inspect_window, click_element, type_text.",
                    type="string",
                    required=True,
                    choices=["list_windows", "inspect_window", "click_element", "type_text"]
                ),
                ToolParameter(
                    name="window_title",
                    description="Numele parțial sau complet al ferestrei (pentru inspect_window, click_element, type_text).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="element_title",
                    description="Numele/Textul elementului UI (pentru click sau type).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="auto_id",
                    description="AutomationId-ul elementului (dacă e cunoscut).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="control_type",
                    description="Tipul elementului (ex: Button, Edit, MenuItem).",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="text",
                    description="Textul de tastat (pentru acțiunea type_text).",
                    type="string",
                    required=False
                )
            ],
            category="desktop"
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
            error_msg = f"Librăria pywinauto lipsește. "
            if self._import_error:
                error_msg += f"Eroare la import: {self._import_error}"
            else:
                error_msg += "Rulează 'pip install pywinauto' mai întâi."
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
            return ToolResult(status=ToolStatus.ERROR, error=f"Acțiune necunoscută: {action}")

    def _list_windows(self) -> ToolResult:
        import pywinauto
        try:
            windows = pywinauto.Desktop(backend="uia").windows(visible_only=True)
            win_list = []
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
                message=f"Am găsit {len(win_list)} ferestre vizibile."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la listarea ferestrelor: {e}")

    def _inspect_window(self, title: str) -> ToolResult:
        if not title:
            return ToolResult(status=ToolStatus.ERROR, error="window_title este obligatoriu pentru inspect_window.")
        
        import pywinauto
        try:
            app = pywinauto.Desktop(backend="uia")
            wins = app.windows(title_re=f".*{title}.*", visible_only=True)
            if not wins:
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{title}' nu a fost găsită.")
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
                message=f"Am mapat fereastra '{win.window_text()}' ({len(elements)} elemente interacționabile)."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la inspectare fereastră: {e}")

    def _interact_element(self, win_title, elem_title, auto_id, ctrl_type, action="click", text="") -> ToolResult:
        if not win_title:
            return ToolResult(status=ToolStatus.ERROR, error="window_title este obligatoriu.")
            
        if not elem_title and not auto_id:
            return ToolResult(status=ToolStatus.ERROR, error="Specifică element_title sau auto_id.")

        import pywinauto
        try:
            app = pywinauto.Desktop(backend="uia")
            wins = app.windows(title_re=f".*{win_title}.*", visible_only=True)
            if not wins:
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{win_title}' nu a fost găsită.")
            win = wins[0]
            
            search_args = {}
            if auto_id:
                search_args["auto_id"] = auto_id
            if elem_title:
                search_args["title"] = elem_title
            if ctrl_type:
                search_args["control_type"] = ctrl_type

            ctrl = win.child_window(**search_args)
            if not ctrl.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Elementul {search_args} nu a fost găsit în fereastră.")
                
            if action == "click":
                try:
                    ctrl.invoke()
                except AttributeError:
                    ctrl.click_input()
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
                    message=f"Am scris textul în elementul '{elem_title or auto_id}'."
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la acțiunea {action}: {e}")
