"""
ANA MAX - Foreground UI Snapshot Tool
======================================
"Ochii Structurali" - Fast, clean UI state for agents

Returns minimal JSON with:
- Active app name
- Window title
- Visible text elements
- Buttons (clickable)
- Input fields (editable)
- Detected errors
- Suggested actions

Designed for: Agent decision-making (not human reading)
"""

import logging
from typing import Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ForegroundUISnapshotTool(Tool):
    """
    Tool pentru capturarea starii UI a ferestrei active.
    Returneaza JSON mic, curat, optimizat pentru agenti AI.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="foreground_ui_snapshot",
            description="Captureaza starea UI a ferestrei active: titlu, controale vizibile, erori detectate, actiuni sugerate. Optimizat pentru agenti AI.",
            parameters=[
                ToolParameter(
                    name="include_text",
                    description="Include toate textele vizibile (default: True)",
                    type="boolean",
                    required=False,
                    default="true"
                ),
                ToolParameter(
                    name="max_elements",
                    description="Numar maxim de elemente per categorie (default: 20)",
                    type="string",
                    required=False,
                    default="20"
                )
            ],
            category="ui_automation"
        )

    def execute(self, **kwargs) -> ToolResult:
        """Executa snapshot UI foreground."""
        try:
            include_text = kwargs.get("include_text", True)
            if isinstance(include_text, str):
                include_text = include_text.lower() == "true"

            max_elements = int(kwargs.get("max_elements", 20))

            snapshot = self._capture_foreground_ui(
                include_text=include_text,
                max_elements=max_elements
            )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=snapshot,
                message=f"UI snapshot captured for: {snapshot.get('active_app', 'Unknown')}"
            )
        except Exception as e:
            logger.error(f"Foreground UI snapshot error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to capture UI snapshot: {str(e)}"
            )

    def _capture_foreground_ui(self, include_text: bool = True, max_elements: int = 20) -> Dict[str, Any]:
        """Captureaza UI state de la fereastra activa."""
        fallback = self._capture_foreground_win32()
        try:
            from pywinauto import Desktop
            from pywinauto import application

            # Get foreground window
            desktop = Desktop(backend="uia")
            foreground = desktop.window(handle=self._get_foreground_window_handle())

            if not foreground.exists():
                fallback["reason"] = "No foreground window found through UIA"
                return fallback

            # Extract app info
            app_name = self._get_app_name(foreground)
            window_title = foreground.window_text()

            # Get all visible controls
            controls = foreground.descendants()

            # Categorize elements
            buttons = []
            inputs = []
            texts = []
            errors = []
            clickable = []

            for ctrl in controls:
                try:
                    ctrl_type = ctrl.element_info.control_type
                    ctrl_text = ctrl.window_text()
                    is_visible = ctrl.is_visible()

                    if not is_visible or not ctrl_text:
                        continue

                    # Categorize by type
                    if ctrl_type == "Button":
                        buttons.append(ctrl_text)
                        clickable.append({"type": "button", "name": ctrl_text, "action": "click"})

                    elif ctrl_type in ["Edit", "Document"]:
                        inputs.append({
                            "name": ctrl_text,
                            "type": "input",
                            "action": "type"
                        })

                    elif ctrl_type == "Text" and include_text:
                        texts.append(ctrl_text)

                    # Detect errors
                    if self._is_error_text(ctrl_text):
                        errors.append(ctrl_text)

                except Exception:
                    continue

            # Build clean snapshot
            snapshot = {
                "active_app": app_name,
                "title": window_title,
                "buttons": buttons[:max_elements],
                "inputs": inputs[:max_elements],
                "visible_text": texts[:max_elements] if include_text else [],
                "detected_errors": errors,
                "suggested_actions": self._suggest_actions(app_name, window_title, buttons, errors, inputs)
            }

            return snapshot

        except Exception as e:
            error_text = str(e) or type(e).__name__
            logger.warning("UIA capture failed, using Win32 fallback: %s", error_text)
            fallback["reason"] = f"UIA error: {error_text}"
            fallback["fallback"] = "win32_foreground_window"
            return fallback

    def _get_foreground_window_handle(self) -> int:
        """Get handle of foreground window."""
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetForegroundWindow()

    def _get_app_name(self, window) -> str:
        """Extract application name from window."""
        try:
            # Try to get from process
            proc_id = window.process_id()
            import psutil
            process = psutil.Process(proc_id)
            return process.name().replace('.exe', '')
        except Exception:
            # Fallback to window title
            return "Unknown"

    def _capture_foreground_win32(self) -> Dict[str, Any]:
        """Cheap Win32 fallback when UIA COM is blocked or unstable."""
        snapshot = self._empty_snapshot("Win32 fallback did not find a foreground window")
        try:
            import ctypes
            import psutil

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return snapshot

            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            app_name = None
            try:
                app_name = psutil.Process(pid.value).name().replace(".exe", "")
            except Exception:
                app_name = None

            snapshot.update({
                "active_app": app_name,
                "title": buffer.value or None,
                "hwnd": int(hwnd),
                "pid": int(pid.value),
                "reason": "UIA not used; Win32 foreground fallback",
            })
            return snapshot
        except Exception as exc:
            snapshot["reason"] = f"Win32 fallback failed: {exc}"
            return snapshot

    def _is_error_text(self, text: str) -> bool:
        """Detect if text is an error message."""
        error_keywords = [
            "error", "failed", "invalid", "cannot", "unable",
            "not found", "permission denied", "access denied",
            "exception", "crash", "warning"
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in error_keywords)

    def _suggest_actions(
        self,
        app_name: str,
        window_title: str,
        buttons: List[str],
        errors: List[str],
        inputs: List[dict],
    ) -> List[Dict[str, str]]:
        """Sugereaza actiuni bazate pe UI state."""
        actions = []

        # If errors detected, suggest dismissal
        if errors:
            if self._looks_like_log_view(app_name, window_title, errors):
                return [{
                    "action": "inspect_log",
                    "target": "terminal_or_output",
                    "reason": f"Log text contains error signal: {errors[0][:50]}",
                }]
            # Look for OK/Close/Dismiss buttons
            for btn in buttons:
                if btn.lower() in ["ok", "close", "dismiss", "retry", "clear"]:
                    actions.append({
                        "action": "click",
                        "target": btn,
                        "reason": f"Error detected: {errors[0][:50]}"
                    })
                    break

        # If no errors, suggest common actions
        if not actions and buttons:
            # Suggest primary action buttons
            primary_buttons = ["OK", "Submit", "Next", "Continue", "Apply"]
            for btn in buttons:
                if btn in primary_buttons:
                    actions.append({
                        "action": "click",
                        "target": btn,
                        "reason": "Primary action button"
                    })
                    break

        return actions

    def _looks_like_log_view(self, app_name: str, window_title: str, errors: List[str]) -> bool:
        """Avoid destructive UI suggestions when errors are merely log text."""
        haystack = f"{app_name} {window_title} {' '.join(errors[:3])}".lower()
        log_markers = [
            "code ",
            "visual studio code",
            "terminal",
            "watchdog",
            "powershell",
            "error_radar",
            "tools.base",
            "tool start",
            "tool end",
            "errors=",
        ]
        return any(marker in haystack for marker in log_markers)

    def _empty_snapshot(self, reason: str = "") -> Dict[str, Any]:
        """Return empty snapshot with reason."""
        return {
            "active_app": None,
            "title": None,
            "buttons": [],
            "inputs": [],
            "visible_text": [],
            "detected_errors": [],
            "suggested_actions": [],
            "reason": reason
        }
