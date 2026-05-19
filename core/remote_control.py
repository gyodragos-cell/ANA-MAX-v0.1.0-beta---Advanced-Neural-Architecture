#!/usr/bin/env python3
"""
ANA MAX - Remote Control Module (Inspirat din UI-TARS Remote Operator)
========================================================================
Control remote computers and browsers securizat prin MCP.

Features:
- Remote computer control (screen, mouse, keyboard)
- Remote browser automation
- Secure MCP endpoints with authentication
- Tailscale/Cloudflare Tunnel support
- Session management
- Multi-machine orchestration

Author: ANA MAX Team (2026-05-19)
Inspired by: UI-TARS Desktop Remote Operator
"""

import os
import json
import time
import logging
import threading
import socket
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RemoteMachine:
    """Represents a remote machine."""
    id: str
    name: str
    address: str  # IP or Tailscale address
    port: int = 8765
    api_key: str = ""
    status: str = "offline"  # online, offline, busy
    last_seen: float = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class RemoteSession:
    """Represents a remote control session."""
    id: str
    machine_id: str
    created_at: float = field(default_factory=time.time)
    active: bool = True
    screenshot_count: int = 0
    action_count: int = 0


class RemoteControlManager:
    """
    Remote control manager for ANA MAX.
    
    Features:
    - Register remote machines
    - Execute actions on remote machines
    - Screenshot streaming
    - Browser control
    - Session management
    - Security via MCP Bearer tokens
    """
    
    def __init__(self, config_path: str = "config/remote_machines.json"):
        self.config_path = Path(config_path)
        self.machines: Dict[str, RemoteMachine] = {}
        self.sessions: Dict[str, RemoteSession] = {}
        self._lock = threading.Lock()
        
        # Load saved machines
        self._load_machines()
        
        logger.info(f"Remote Control Manager initialized ({len(self.machines)} machines)")
    
    def _load_machines(self):
        """Load remote machines from config."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for machine_data in data.get("machines", []):
                    machine = RemoteMachine(**machine_data)
                    self.machines[machine.id] = machine
                
                logger.info(f"Loaded {len(self.machines)} remote machines")
            except Exception as e:
                logger.error(f"Failed to load remote machines config: {e}")
    
    def _save_machines(self):
        """Save remote machines to config."""
        try:
            data = {
                "machines": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "address": m.address,
                        "port": m.port,
                        "api_key": m.api_key,
                        "metadata": m.metadata
                    }
                    for m in self.machines.values()
                ]
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save remote machines config: {e}")
    
    def register_machine(self, name: str, address: str, api_key: str, 
                        port: int = 8765, metadata: Dict = None) -> str:
        """
        Register a new remote machine.
        
        Args:
            name: Friendly name
            address: IP address or Tailscale address
            api_key: MCP Bearer token for authentication
            port: MCP server port
            metadata: Optional metadata (os, location, etc.)
        
        Returns:
            Machine ID
        """
        import uuid
        machine_id = str(uuid.uuid4())[:8]
        
        machine = RemoteMachine(
            id=machine_id,
            name=name,
            address=address,
            port=port,
            api_key=api_key,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.machines[machine_id] = machine
            self._save_machines()
        
        logger.info(f"Registered remote machine: {name} ({address})")
        return machine_id
    
    def remove_machine(self, machine_id: str) -> bool:
        """Remove a remote machine."""
        with self._lock:
            if machine_id in self.machines:
                del self.machines[machine_id]
                self._save_machines()
                return True
        return False
    
    def check_machine_status(self, machine_id: str) -> str:
        """Check if remote machine is online."""
        machine = self.machines.get(machine_id)
        if not machine:
            return "not_found"
        
        try:
            # Try to connect to MCP server
            url = f"http://{machine.address}:{machine.port}/health"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                machine.status = "online"
                machine.last_seen = time.time()
                return "online"
            else:
                machine.status = "offline"
                return "offline"
                
        except:
            machine.status = "offline"
            return "offline"
    
    def list_machines(self) -> List[Dict]:
        """List all registered machines with status."""
        result = []
        for machine in self.machines.values():
            self.check_machine_status(machine.id)
            result.append({
                "id": machine.id,
                "name": machine.name,
                "address": machine.address,
                "port": machine.port,
                "status": machine.status,
                "last_seen": machine.last_seen,
                "metadata": machine.metadata
            })
        return result
    
    def take_remote_screenshot(self, machine_id: str) -> Optional[bytes]:
        """Take screenshot on remote machine."""
        machine = self.machines.get(machine_id)
        if not machine:
            return None
        
        try:
            url = f"http://{machine.address}:{machine.port}/api/desktop_capture"
            headers = {"Authorization": f"Bearer {machine.api_key}"}
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Update session stats
                for session in self.sessions.values():
                    if session.machine_id == machine_id and session.active:
                        session.screenshot_count += 1
                
                return response.content
            else:
                logger.error(f"Remote screenshot failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Remote screenshot error: {e}")
            return None
    
    def execute_remote_action(self, machine_id: str, action: str, 
                             params: Dict = None) -> Optional[Dict]:
        """
        Execute action on remote machine.
        
        Actions:
        - click: {x, y}
        - type: {text}
        - key_press: {key}
        - move_mouse: {x, y}
        - scroll: {direction, amount}
        - run_command: {command}
        """
        machine = self.machines.get(machine_id)
        if not machine:
            return None
        
        try:
            url = f"http://{machine.address}:{machine.port}/api/desktop_control"
            headers = {
                "Authorization": f"Bearer {machine.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "action": action,
                "params": params or {}
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Update session stats
                for session in self.sessions.values():
                    if session.machine_id == machine_id and session.active:
                        session.action_count += 1
                
                return response.json()
            else:
                logger.error(f"Remote action failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Remote action error: {e}")
            return None
    
    def create_session(self, machine_id: str) -> Optional[str]:
        """Create a remote control session."""
        if machine_id not in self.machines:
            return None
        
        import uuid
        session_id = str(uuid.uuid4())[:8]
        
        session = RemoteSession(
            id=session_id,
            machine_id=machine_id
        )
        
        with self._lock:
            self.sessions[session_id] = session
        
        logger.info(f"Created remote session: {session_id} -> {machine_id}")
        return session_id
    
    def close_session(self, session_id: str) -> bool:
        """Close a remote control session."""
        session = self.sessions.get(session_id)
        if session:
            session.active = False
            logger.info(f"Closed remote session: {session_id}")
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "id": session.id,
            "machine_id": session.machine_id,
            "created_at": session.created_at,
            "active": session.active,
            "screenshot_count": session.screenshot_count,
            "action_count": session.action_count,
            "duration": time.time() - session.created_at
        }
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions."""
        return [
            self.get_session_info(sid)
            for sid, session in self.sessions.items()
            if session.active
        ]


# Singleton instance
_remote_manager_instance = None
_remote_manager_lock = threading.Lock()


def get_remote_manager() -> RemoteControlManager:
    """Get or create RemoteControlManager singleton."""
    global _remote_manager_instance
    
    if _remote_manager_instance is None:
        with _remote_manager_lock:
            if _remote_manager_instance is None:
                _remote_manager_instance = RemoteControlManager()
    
    return _remote_manager_instance


if __name__ == "__main__":
    # Test remote control
    manager = get_remote_manager()
    
    # List machines
    machines = manager.list_machines()
    print(f"Registered machines: {len(machines)}")
    
    for machine in machines:
        print(f"  - {machine['name']} ({machine['address']}): {machine['status']}")
