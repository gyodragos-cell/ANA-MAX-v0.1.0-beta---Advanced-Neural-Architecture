"""
A.N.A. v16.0 - AdaL Integration Tool
====================================
Permite ANA să interacționeze cu CLI-ul AdaL (Sylph AI) pentru execuție tactică.
"""

import subprocess
import logging
from typing import Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class AdaLTool(Tool):
    """
    Tool pentru interfațarea cu AdaL CLI (Sylph AI).
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="adal_integration",
            description="Interfață cu AdaL CLI pentru execuție de cod, debug tactic și browser automation.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operațiunea: 'exec' (rulează o sarcină), 'web' (deschide interfața web), 'version' (verifică versiunea)",
                    type="string",
                    required=True,
                    choices=["exec", "web", "version"]
                ),
                ToolParameter(
                    name="task",
                    description="Sarcina pentru AdaL (doar pentru operațiunea 'exec')",
                    type="string",
                    required=False
                )
            ],
            category="tactic"
        )
    
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        task = kwargs.get("task")
        
        if operation == "version":
            return self._run_command(["adal", "--version"])
            
        elif operation == "web":
            # AdaL --web pornește un server, deci îl rulăm separat (recomandat să fie rulat manual de operator dacă e persistent)
            # Dar pentru integrare, putem încerca să-l pornim asincron sau doar să informăm.
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="Pentru a deschide interfața web AdaL, te rog să rulezi 'adal --web' în terminalul tău."
            )
            
        elif operation == "exec":
            if not task:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'task' este obligatoriu pentru 'exec'")
            
            # Rulăm adal cu task-ul specificat ca listă pentru siguranță
            cmd_list = ["adal", "-q", task, "--allowed-tools", "*"]
            return self._run_command(cmd_list)
            
        return ToolResult(status=ToolStatus.ERROR, error=f"Operațiune necunoscută: {operation}")

    def _run_command(self, cmd: Any) -> ToolResult:
        try:
            # Rulăm comanda și capturăm output-ul
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True, # Necesar pe Windows pentru CLI-uri instalate prin npm
                timeout=120
            )
            
            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result.stdout.strip(),
                    message=f"Comanda a fost executată cu succes."
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr.strip() or f"Cod ieșire: {result.returncode}",
                    message=f"Eroare la executarea comenzii AdaL."
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error="Timeout: Operațiunea AdaL a durat prea mult (> 120s)")
        except Exception as e:
            logger.error(f"Eroare execuție AdaL: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
