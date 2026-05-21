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
            include_text = kwargs.get("include_text", "true").lower() == "true"
            max_elements = int(kwargs.get("max_elements", "20"))
            
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
        try:
            from pywinauto import Desktop
            from pywinauto import application
            
            # Get foreground window
            desktop = Desktop(backend="uia")
            foreground = desktop.window(handle=self._get_foreground_window_handle())
            
            if not foreground.exists():
                return self._empty_snapshot("No foreground window found")
            
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
                "suggested_actions": self._suggest_actions(buttons, errors, inputs)
            }
            
            return snapshot
            
        except Exception as e:
            logger.error(f"UI capture error: {e}")
            return self._empty_snapshot(f"Error: {str(e)}")

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

    def _is_error_text(self, text: str) -> bool:
        """Detect if text is an error message."""
        error_keywords = [
            "error", "failed", "invalid", "cannot", "unable",
            "not found", "permission denied", "access denied",
            "exception", "crash", "warning"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in error_keywords)

    def _suggest_actions(self, buttons: List[str], errors: List[str], inputs: List[dict]) -> List[Dict[str, str]]:
        """Sugereaza actiuni bazate pe UI state."""
        actions = []
        
        # If errors detected, suggest dismissal
        if errors:
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
