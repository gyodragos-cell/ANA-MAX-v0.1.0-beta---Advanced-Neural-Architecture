#!/usr/bin/env python3
"""
Universal Task Orchestrator - Platform-Agnostic Task Planning
==============================================================
Coordinates tools across any platform (Devin, Windsurf, Cursor, Antigravity).
Not tied to ANA-specific ecosystem - works with any MCP tool registry.

Unlike ana_orchestrator.py which is ANA-specific, this orchestrator:
- Accepts any tool registry (MCP, local, remote)
- No dependency on ANA-specific tools
- Generic task planning and execution
- Can be used by any coding agent platform
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """A single step in a task execution plan."""
    id: int
    description: str
    tool_name: str
    operation: str
    parameters: Dict = field(default_factory=dict)
    depends_on: List[int] = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed | skipped
    result: Any = None
    error: str = ""
    duration_sec: float = 0.0


@dataclass
class TaskPlan:
    """A complete task execution plan."""
    task: str
    steps: List[TaskStep] = field(default_factory=list)
    estimated_duration_sec: float = 0.0
    complexity: str = "medium"  # low | medium | high


@dataclass
class TaskExecutionResult:
    """Result of task execution."""
    task: str
    success: bool
    steps_total: int
    steps_done: int
    steps_failed: int
    duration_sec: float
    summary: str
    learned: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class UniversalTaskOrchestratorTool(Tool):
    """
    Platform-agnostic task orchestrator.

    Unlike AnaOrchestrator (ANA-specific), this works with any tool registry
    and can be used by Devin, Windsurf, Cursor, Antigravity, etc.
    """

    def __init__(self):
        super().__init__()
        self.tool_registry: Dict[str, Tool] = {}
        self.execution_history: List[TaskExecutionResult] = []

    def get_definition(self) -> ToolDefinition:
        """Return tool definition."""
        return ToolDefinition(
            name="universal_task_orchestrator",
            description="Platform-agnostic task planning and execution for any tool registry",
            category="AI CORE",
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation: plan, execute, list_tools, register_tool",
                    required=True,
                    choices=["plan", "execute", "list_tools", "register_tool"]
                ),
                ToolParameter(
                    name="task",
                    type="string",
                    description="Task description in natural language (for plan/execute)",
                    required=False
                ),
                ToolParameter(
                    name="tools",
                    type="array",
                    description="List of available tools (for register_tool)",
                    required=False
                ),
                ToolParameter(
                    name="plan",
                    type="object",
                    description="Execution plan (for execute)",
                    required=False
                ),
                ToolParameter(
                    name="dry_run",
                    type="boolean",
                    description="Simulate without execution",
                    required=False
                ),
            ],
            requires_confirmation=False
        )

    def execute(self, **kwargs) -> ToolResult:
        """Execute orchestrator operations."""
        try:
            operation = kwargs.get('operation')

            if operation == 'plan':
                return self._plan_task(**kwargs)
            elif operation == 'execute':
                return self._execute_plan(**kwargs)
            elif operation == 'list_tools':
                return self._list_tools(**kwargs)
            elif operation == 'register_tool':
                return self._register_tool(**kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown operation: {operation}"
                )
        except Exception as e:
            logger.error(f"Error in universal_task_orchestrator: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error executing operation: {str(e)}"
            )

    def _plan_task(self, task: str, **kwargs) -> ToolResult:
        """
        Plan a task based on natural language description.

        This is a simplified planner. In production, this would use
        an LLM to generate the plan based on available tools.
        """
        try:
            # Simple heuristic-based planning (production would use LLM)
            steps = self._generate_heuristic_plan(task)

            plan = TaskPlan(
                task=task,
                steps=steps,
                estimated_duration_sec=sum(s.duration_sec for s in steps),
                complexity=self._assess_complexity(steps)
            )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'task': task,
                    'plan': self._plan_to_dict(plan),
                    'estimated_duration_sec': plan.estimated_duration_sec,
                    'complexity': plan.complexity,
                    'steps_count': len(steps)
                }
            )
        except Exception as e:
            logger.error(f"Error planning task: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error planning task: {str(e)}"
            )

    def _execute_plan(self, plan: Dict, dry_run: bool = False, **kwargs) -> ToolResult:
        """Execute a task plan."""
        try:
            task = plan.get('task', 'Unknown task')
            steps_data = plan.get('steps', [])

            steps = [self._dict_to_step(step_data) for step_data in steps_data]

            result = TaskExecutionResult(
                task=task,
                success=False,
                steps_total=len(steps),
                steps_done=0,
                steps_failed=0,
                duration_sec=0.0,
                summary=""
            )

            start_time = time.time()

            for step in steps:
                step.status = "running"
                step_start = time.time()

                try:
                    if dry_run:
                        step.result = {"dry_run": True, "simulated": True}
                        step.status = "done"
                    else:
                        # Execute the step using the registered tool
                        if step.tool_name in self.tool_registry:
                            tool = self.tool_registry[step.tool_name]
                            step.result = tool.execute(**step.parameters)
                            step.status = "done" if step.result.is_success else "failed"
                        else:
                            step.status = "failed"
                            step.error = f"Tool not found: {step.tool_name}"

                    step.duration_sec = time.time() - step_start

                    if step.status == "done":
                        result.steps_done += 1
                    elif step.status == "failed":
                        result.steps_failed += 1
                        result.errors.append(f"Step {step.id} failed: {step.error}")

                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    step.duration_sec = time.time() - step_start
                    result.steps_failed += 1
                    result.errors.append(f"Step {step.id} exception: {str(e)}")

            result.duration_sec = time.time() - start_time
            result.success = result.steps_failed == 0
            result.summary = f"Completed {result.steps_done}/{result.steps_total} steps"

            self.execution_history.append(result)

            return ToolResult(
                status=ToolStatus.SUCCESS if result.success else ToolStatus.ERROR,
                data={
                    'task': result.task,
                    'success': result.success,
                    'steps_total': result.steps_total,
                    'steps_done': result.steps_done,
                    'steps_failed': result.steps_failed,
                    'duration_sec': result.duration_sec,
                    'summary': result.summary,
                    'errors': result.errors
                }
            )
        except Exception as e:
            logger.error(f"Error executing plan: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error executing plan: {str(e)}"
            )

    def _list_tools(self, **kwargs) -> ToolResult:
        """List registered tools."""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                'total_tools': len(self.tool_registry),
                'tools': list(self.tool_registry.keys())
            }
        )

    def _register_tool(self, tool_name: str, tool: Tool, **kwargs) -> ToolResult:
        """Register a tool with the orchestrator."""
        try:
            self.tool_registry[tool_name] = tool
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'tool_name': tool_name,
                    'registered': True
                }
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error registering tool: {str(e)}"
            )

    def _generate_heuristic_plan(self, task: str) -> List[TaskStep]:
        """Generate a simple heuristic-based plan (production would use LLM)."""
        task_lower = task.lower()
        steps = []

        # Heuristic planning rules
        if 'capture' in task_lower or 'screenshot' in task_lower:
            steps.append(TaskStep(
                id=1,
                description="Capture desktop screenshot",
                tool_name="desktop_capture",
                operation="capture",
                parameters={},
                duration_sec=2.0
            ))

        if 'error' in task_lower or 'debug' in task_lower:
            steps.append(TaskStep(
                id=2,
                description="Detect errors in recent output",
                tool_name="error_radar",
                operation="scan",
                parameters={},
                duration_sec=3.0
            ))

        if 'terminal' in task_lower or 'command' in task_lower:
            steps.append(TaskStep(
                id=3,
                description="Capture terminal state",
                tool_name="terminal_monitor",
                operation="capture",
                parameters={},
                duration_sec=2.0
            ))

        if 'context' in task_lower or 'state' in task_lower:
            steps.append(TaskStep(
                id=4,
                description="Get workspace context",
                tool_name="workspace_situational_awareness",
                operation="get_state",
                parameters={},
                duration_sec=1.0
            ))

        # If no steps matched, add a generic step
        if not steps:
            steps.append(TaskStep(
                id=1,
                description="Generic task execution",
                tool_name="unknown",
                operation="execute",
                parameters={},
                duration_sec=5.0
            ))

        return steps

    def _assess_complexity(self, steps: List[TaskStep]) -> str:
        """Assess task complexity based on steps."""
        if len(steps) <= 2:
            return "low"
        elif len(steps) <= 5:
            return "medium"
        else:
            return "high"

    def _plan_to_dict(self, plan: TaskPlan) -> Dict:
        """Convert plan to dictionary for serialization."""
        return {
            'task': plan.task,
            'steps': [self._step_to_dict(step) for step in plan.steps],
            'estimated_duration_sec': plan.estimated_duration_sec,
            'complexity': plan.complexity
        }

    def _step_to_dict(self, step: TaskStep) -> Dict:
        """Convert step to dictionary."""
        return {
            'id': step.id,
            'description': step.description,
            'tool_name': step.tool_name,
            'operation': step.operation,
            'parameters': step.parameters,
            'depends_on': step.depends_on,
            'status': step.status,
            'duration_sec': step.duration_sec
        }

    def _dict_to_step(self, data: Dict) -> TaskStep:
        """Convert dictionary to step."""
        return TaskStep(
            id=data['id'],
            description=data['description'],
            tool_name=data['tool_name'],
            operation=data['operation'],
            parameters=data.get('parameters', {}),
            depends_on=data.get('depends_on', []),
            status=data.get('status', 'pending'),
            duration_sec=data.get('duration_sec', 0.0)
        )


# Standalone usage for testing
if __name__ == "__main__":
    orchestrator = UniversalTaskOrchestratorTool()

    # Test 1: Plan a task
    print("Test 1: Plan task")
    result = orchestrator.execute(operation='plan', task='Capture desktop and detect errors')
    print(json.dumps(result.data, indent=2))

    # Test 2: List tools
    print("\nTest 2: List tools")
    result = orchestrator.execute(operation='list_tools')
    print(json.dumps(result.data, indent=2))

    # Test 3: Execute plan (dry run)
    print("\nTest 3: Execute plan (dry run)")
    plan = {
        'task': 'Test task',
        'steps': [
            {
                'id': 1,
                'description': 'Test step',
                'tool_name': 'test_tool',
                'operation': 'test',
                'parameters': {},
                'depends_on': [],
                'status': 'pending',
                'duration_sec': 1.0
            }
        ]
    }
    result = orchestrator.execute(operation='execute', plan=plan, dry_run=True)
    print(json.dumps(result.data, indent=2))
