import os
import time
from typing import Any, Dict
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.watchdog_bus import EventBus

class ArtifactTool(Tool):
    """
    Tool for creating and updating artifacts to present structured plans to the user.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="artifact_tool",
            description="Creeaza sau actualizeaza un artefact (ex: plan de implementare, diagrama, tabel). Foloseste acest tool in loc sa generezi raspunsuri masive de text/cod in fereastra de chat.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="Actiunea de efectuat ('create', 'update', 'request_approval')",
                    type="string",
                    required=True,
                    choices=["create", "update", "request_approval"]
                ),
                ToolParameter(
                    name="filename",
                    description="Numele fisierului (ex: implementation_plan.md). Salvat automat in folderul de artifacts.",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    description="Continutul markdown (folosit pentru 'create' si 'update'). Nu este necesar pentru 'request_approval'.",
                    type="string",
                    required=False
                )
            ],
            category="artifacts"
        )
        
    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        filename = kwargs.get("filename")
        content = kwargs.get("content", "")
        
        # Salvam artefactele in ANA_MAX/artifacts/
        artifacts_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        file_path = os.path.join(artifacts_dir, os.path.basename(filename))
        
        if action == "create" or action == "update":
            if not content:
                return ToolResult(status=ToolStatus.ERROR, error="Continutul (content) este obligatoriu pentru create/update.")
            
            mode = "w" if action == "create" else "a"
            try:
                with open(file_path, mode, encoding="utf-8") as f:
                    if action == "update":
                        f.write("\n" + content)
                    else:
                        f.write(content)
                        
                return ToolResult(
                    status=ToolStatus.SUCCESS, 
                    data={"file_path": file_path, "action": action},
                    message=f"Artifact {action}d successfully at {file_path}"
                )
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la scrierea artefactului: {e}")
                
        elif action == "request_approval":
            if not os.path.exists(file_path):
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul {file_path} nu exista. Creati artefactul inainte de a cere aprobare.")
            
            try:
                # Folosim watchdog bus pentru a trimite cererea catre dashboard
                bus = EventBus()
                bus.publish("artifact_tool", "artifact_approval_requested", {
                    "file_path": file_path,
                    "filename": filename,
                    "timestamp": time.time()
                })
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"file_path": file_path, "status": "waiting_for_user"},
                    message=f"Approval requested via EventBus for {filename}. Wait for user input."
                )
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la trimiterea request-ului: {e}")
                
        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune invalida: {action}")
