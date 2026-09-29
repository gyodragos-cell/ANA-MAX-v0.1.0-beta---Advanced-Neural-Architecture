"""
A.N.A. - Autonomous Engine Tool
"""

import logging
from typing import Any, Dict

from core.engineer_platform import EngineerPlatform
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class AutonomousTool(Tool):
    """Expose the Engineer task loop as a tool."""

    def __init__(self, ana_agent=None):
        self.ana_agent = ana_agent
        self._platform = None

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="autonomous_engine",
            description="Activeaza modul de lucru autonom (Plan -> Execute -> Verify)",
            parameters=[
                ToolParameter(
                    name="task",
                    description="Descrierea completa a task-ului",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="max_steps",
                    description="Numarul maxim de iteratii",
                    type="integer",
                    required=False,
                ),
            ],
            category="autonomy",
        )

    def execute(self, **kwargs) -> ToolResult:
        task = kwargs.get("task")
        max_steps = kwargs.get("max_steps", 10)

        if not self.ana_agent:
            return ToolResult(status=ToolStatus.ERROR, error="Agentul ANA nu este legat la tool.")

        try:
            if not self._platform:
                workspace_root = getattr(getattr(self.ana_agent, "engineer_platform", None), "workspace_root", None)
                self._platform = EngineerPlatform(
                    self.ana_agent,
                    workspace_root=str(workspace_root) if workspace_root else ".",
                )

            logger.info("Mod AUTONOM activat pentru task: %s", task)
            result = self._platform.run_task(task, max_steps=max_steps)
            message = (
                f"Task finalizat cu succes in {result['iterations']} iteratii."
                if result["success"]
                else "Task-ul nu a fost completat integral. Vezi detaliile in rezultat."
            )
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=message)
        except Exception as exc:
            logger.error("Autonomous loop failed: %s", exc)
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
