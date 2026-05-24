"""
A.N.A. v16.0 - AdaL Integration Tool
====================================
Permite ANA sa interactioneze cu CLI-ul AdaL (Sylph AI) pentru executie tactica.
"""

import subprocess
import logging
import shutil
from typing import Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class AdaLTool(Tool):
    """
    Tool pentru interfatarea cu AdaL CLI (Sylph AI).
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="adal_integration",
            description="Interfata cu AdaL CLI pentru executie de cod, debug tactic si browser automation.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: 'exec' (ruleaza o sarcina), 'web' (deschide interfata web), 'version' (verifica versiunea)",
                    type="string",
                    required=True,
                    choices=["exec", "web", "version"]
                ),
                ToolParameter(
                    name="task",
                    description="Sarcina pentru AdaL (doar pentru operatiunea 'exec')",
                    type="string",
                    required=False
                )
            ],
            category="tactic",
            dangerous=True,
        )
    
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        task = kwargs.get("task")
        
        if operation == "version":
            return self._run_command(["adal", "--version"])
            
        elif operation == "web":
            # AdaL --web porneste un server, deci il rulam separat (recomandat sa fie rulat manual de operator daca e persistent)
            # Dar pentru integrare, putem incerca sa-l pornim asincron sau doar sa informam.
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="Pentru a deschide interfata web AdaL, te rog sa rulezi 'adal --web' in terminalul tau."
            )
            
        elif operation == "exec":
            if not task:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'task' este obligatoriu pentru 'exec'")
            
            # Rulam adal cu task-ul specificat ca lista pentru siguranta
            cmd_list = ["adal", "-q", task, "--allowed-tools", "*"]
            return self._run_command(cmd_list)
            
        return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")

    def _run_command(self, cmd: Any) -> ToolResult:
        try:
            if isinstance(cmd, list) and cmd:
                cmd = [shutil.which(cmd[0]) or cmd[0], *cmd[1:]]
            # Rulam comanda si capturam output-ul
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,
                timeout=120
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result.stdout.strip(),
                    message=f"Comanda a fost executata cu succes."
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or f"Cod iesire: {result.returncode}",
                    message=f"Eroare la executarea comenzii AdaL."
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error="Timeout: Operatiunea AdaL a durat prea mult (> 120s)")
        except Exception as e:
            logger.error(f"Eroare executie AdaL: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
