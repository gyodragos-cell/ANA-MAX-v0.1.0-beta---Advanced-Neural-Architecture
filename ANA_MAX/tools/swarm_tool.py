#!/usr/bin/env python3
"""
ANA MAX - Advanced Swarm Tool
===============================
Tool pentru orchestrare multi-agent swarm.

Features:
- Execute complex tasks with swarm
- Dynamic agent spawning
- Task decomposition
- Consensus-based decisions
- Performance tracking

Author: ANA MAX Team (2026-05-19)
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.advanced_swarm import get_swarm_orchestrator, Topology


class SwarmTool(Tool):
    """Advanced Swarm Tool pentru ANA MAX."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="swarm_orchestrator",
            description=(
                "Orchestrare multi-agent swarm cu topologii adaptive. "
                "Descompune task-uri complexe in subtask-uri si le executa paralel. "
                "Actions: execute, status, add_agent, optimize, spawn"
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Actiunea: execute, status, add_agent, optimize, spawn",
                    type="string",
                    required=True,
                    choices=["execute", "status", "add_agent", "optimize", "spawn"]
                ),
                ToolParameter(
                    name="task",
                    description="Task de executat (pentru execute)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="agent_name",
                    description="Nume agent (pentru add_agent)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="agent_role",
                    description="Rol agent: coordinator, architect, developer, tester, security, researcher",
                    type="string",
                    required=False,
                    choices=["coordinator", "architect", "developer", "tester", "security", "researcher"]
                ),
                ToolParameter(
                    name="topology",
                    description="Topologie swarm: hierarchical, mesh, adaptive",
                    type="string",
                    required=False,
                    choices=["hierarchical", "mesh", "adaptive"]
                ),
                ToolParameter(
                    name="specializations",
                    description="Specializari agent (JSON array)",
                    type="string",
                    required=False
                )
            ],
            category="swarm"
        )
    
    def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            # Get topology
            topology_str = kwargs.get("topology", "adaptive")
            topology = Topology(topology_str)
            
            swarm = get_swarm_orchestrator(topology=topology)
            
            if action == "execute":
                return self._execute(swarm, **kwargs)
            elif action == "status":
                return self._status(swarm)
            elif action == "add_agent":
                return self._add_agent(swarm, **kwargs)
            elif action == "optimize":
                return self._optimize(swarm)
            elif action == "spawn":
                return self._spawn(swarm, **kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Swarm error: {e}"
            )
    
    def _execute(self, swarm, task: str = None, **kwargs) -> ToolResult:
        """Execute task with swarm."""
        if not task:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Task is required for execute action"
            )
        
        # Mock executor (in real use, this would call ANA's LLM)
        def mock_executor(task_desc):
            return f"Completed by swarm: {task_desc}"
        
        result = swarm.execute_swarm_task(task, mock_executor)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=result,
            message=f"Task executed: {result['successful']}/{result['subtasks']} subtasks completed"
        )
    
    def _status(self, swarm) -> ToolResult:
        """Get swarm status."""
        status = swarm.get_swarm_status()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=status,
            message=f"Swarm: {status['total_agents']} agents, {status['total_completed']} tasks completed"
        )
    
    def _add_agent(self, swarm, agent_name: str = None, agent_role: str = None,
                   specializations: str = None, **kwargs) -> ToolResult:
        """Add agent to swarm."""
        if not agent_name or not agent_role:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="agent_name and agent_role are required"
            )
        
        import json
        from core.advanced_swarm import AgentRole
        
        role = AgentRole(agent_role)
        specs = json.loads(specializations) if specializations else []
        
        agent_id = swarm.add_agent(agent_name, role, specs)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_role": agent_role,
                "specializations": specs
            },
            message=f"Agent added: {agent_name}"
        )
    
    def _optimize(self, swarm) -> ToolResult:
        """Optimize swarm."""
        swarm.optimize_swarm()
        status = swarm.get_swarm_status()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=status,
            message="Swarm optimized"
        )
    
    def _spawn(self, swarm, task: str = None, **kwargs) -> ToolResult:
        """Spawn agent based on task."""
        if not task:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Task description is required for spawn action"
            )
        
        agent_id = swarm.spawn_agent(task)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "agent_id": agent_id,
                "task_description": task
            },
            message=f"Agent spawned for task"
        )


if __name__ == "__main__":
    # Test tool
    tool = SwarmTool()
    
    # Status
    result = tool.execute("status")
    print(f"Status: {result.message}")
    
    # Execute task
    result = tool.execute("execute", task="Build a REST API")
    print(f"Execute: {result.message}")
    print(result.data)
