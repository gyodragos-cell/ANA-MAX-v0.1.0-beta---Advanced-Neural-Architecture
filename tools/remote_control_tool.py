#!/usr/bin/env python3
"""
ANA MAX - Remote Control Tool
===============================
Tool wrapper for Remote Control Module.

Author: ANA MAX Team (2026-05-19)
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.remote_control import get_remote_manager


class RemoteControlTool(Tool):
    """Remote Control Tool for ANA MAX."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="remote_control",
            description=(
                "Control remote computers via MCP. Register machines, take screenshots, "
                "execute actions remotely. Actions: register, list, screenshot, action, session"
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform",
                    type="string",
                    required=True,
                    choices=["register", "list", "remove", "screenshot", "execute", "session_list", "session_create", "session_close"]
                ),
                ToolParameter(
                    name="machine_name",
                    description="Machine name (for register)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="machine_address",
                    description="Machine address/IP (for register)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="machine_id",
                    description="Machine ID (for screenshot/execute)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="api_key",
                    description="MCP API key (for register)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="remote_action",
                    description="Remote action: click, type, key_press, move_mouse, scroll, run_command",
                    type="string",
                    required=False,
                    choices=["click", "type", "key_press", "move_mouse", "scroll", "run_command"]
                ),
                ToolParameter(
                    name="action_params",
                    description="Action parameters as JSON string",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="session_id",
                    description="Session ID (for session operations)",
                    type="string",
                    required=False
                )
            ],
            category="remote"
        )
    
    def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            manager = get_remote_manager()
            
            if action == "register":
                return self._register(manager, **kwargs)
            elif action == "list":
                return self._list(manager)
            elif action == "remove":
                return self._remove(manager, **kwargs)
            elif action == "screenshot":
                return self._screenshot(manager, **kwargs)
            elif action == "execute":
                return self._execute(manager, **kwargs)
            elif action == "session_list":
                return self._session_list(manager)
            elif action == "session_create":
                return self._session_create(manager, **kwargs)
            elif action == "session_close":
                return self._session_close(manager, **kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Remote control error: {e}"
            )
    
    def _register(self, manager, machine_name: str = None, 
                  machine_address: str = None, api_key: str = None, **kwargs) -> ToolResult:
        """Register a remote machine."""
        if not machine_name or not machine_address or not api_key:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="machine_name, machine_address, and api_key are required"
            )
        
        machine_id = manager.register_machine(
            name=machine_name,
            address=machine_address,
            api_key=api_key
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"machine_id": machine_id, "name": machine_name},
            message=f"Registered machine: {machine_name}"
        )
    
    def _list(self, manager) -> ToolResult:
        """List all remote machines."""
        machines = manager.list_machines()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"machines": machines, "count": len(machines)},
            message=f"Found {len(machines)} machines"
        )
    
    def _remove(self, manager, machine_id: str = None, **kwargs) -> ToolResult:
        """Remove a remote machine."""
        if not machine_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="machine_id is required"
            )
        
        success = manager.remove_machine(machine_id)
        
        if success:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"machine_id": machine_id},
                message=f"Removed machine: {machine_id}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Machine not found: {machine_id}"
            )
    
    def _screenshot(self, manager, machine_id: str = None, **kwargs) -> ToolResult:
        """Take screenshot on remote machine."""
        if not machine_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="machine_id is required"
            )
        
        screenshot = manager.take_remote_screenshot(machine_id)
        
        if screenshot:
            # Save screenshot
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/remote_{machine_id}_{timestamp}.png"
            
            Path("screenshots").mkdir(exist_ok=True)
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"screenshot_path": screenshot_path, "size": len(screenshot)},
                message=f"Screenshot saved: {screenshot_path}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Failed to take remote screenshot"
            )
    
    def _execute(self, manager, machine_id: str = None,
                 remote_action: str = None, action_params: str = None, **kwargs) -> ToolResult:
        """Execute action on remote machine."""
        if not machine_id or not remote_action:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="machine_id and remote_action are required"
            )
        
        import json
        params = json.loads(action_params) if action_params else {}
        
        result = manager.execute_remote_action(machine_id, remote_action, params)
        
        if result:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                message=f"Executed {remote_action} on {machine_id}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Failed to execute remote action"
            )
    
    def _session_list(self, manager) -> ToolResult:
        """List active sessions."""
        sessions = manager.list_sessions()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"sessions": sessions, "count": len(sessions)},
            message=f"{len(sessions)} active sessions"
        )
    
    def _session_create(self, manager, machine_id: str = None, **kwargs) -> ToolResult:
        """Create a remote session."""
        if not machine_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="machine_id is required"
            )
        
        session_id = manager.create_session(machine_id)
        
        if session_id:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"session_id": session_id, "machine_id": machine_id},
                message=f"Created session: {session_id}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to create session for machine: {machine_id}"
            )
    
    def _session_close(self, manager, session_id: str = None, **kwargs) -> ToolResult:
        """Close a remote session."""
        if not session_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="session_id is required"
            )
        
        success = manager.close_session(session_id)
        
        if success:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"session_id": session_id},
                message=f"Closed session: {session_id}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Session not found: {session_id}"
            )


if __name__ == "__main__":
    tool = RemoteControlTool()
    
    # List machines
    result = tool.execute("list")
    print(f"Machines: {result.message}")
    if result.data:
        print(f"Count: {result.data.get('count', 0)}")
