"""
ANA MAX - Task Tool
===================
Thin task orchestration wrapper for local models.
"""

from __future__ import annotations

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class TaskTool(Tool):
    """Expose simple planning/execution through AutonomousAgent."""

    def __init__(self, ana_agent=None):
        self.ana_agent = ana_agent

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="task",
            description=(
                "Planifica sau executa un task multi-pas folosind motorul autonom ANA. "
                "Bun pentru modele locale care au nevoie de orchestrare minima."
            ),
            parameters=[
                ToolParameter(
                    name="task",
                    description="Task-ul complet de planificat sau executat",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="plan_only",
                    description="Returneaza doar planul, fara executie",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="max_steps",
                    description="Numarul maxim de iteratii pentru executie",
                    type="integer",
                    required=False,
                    default=10,
                ),
            ],
            category="autonomy",
            requires_confirmation=False,
        )

    def execute(self, task: str, plan_only: bool = False, max_steps: int = 10, **kwargs) -> ToolResult:
        del kwargs
        if not self.ana_agent:
            return ToolResult(status=ToolStatus.ERROR, error="Agentul ANA nu este legat la tool.")

        try:
            from core.autonomous_agent import AutonomousAgent

            engine = AutonomousAgent(self.ana_agent)
            engine._project_root = getattr(getattr(self.ana_agent, "engineer_platform", None), "workspace_root", ".")

            if plan_only:
                plan = engine._create_plan(task)
                data = {
                    "task": plan.task_description,
                    "reasoning": plan.reasoning,
                    "total_steps": plan.total_steps,
                    "steps": [
                        {
                            "id": step.id,
                            "description": step.description,
                            "action": step.action,
                            "params": step.params,
                        }
                        for step in plan.steps
                    ],
                }
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Plan task generat")

            result = engine.execute_task(task, max_iterations=max_steps)
            return ToolResult(
                status=ToolStatus.SUCCESS if result.get("success", False) else ToolStatus.ERROR,
                data=result,
                message="Task executat" if result.get("success", False) else "Task executat partial sau esuat",
                error=None if result.get("success", False) else result.get("output", ""),
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
