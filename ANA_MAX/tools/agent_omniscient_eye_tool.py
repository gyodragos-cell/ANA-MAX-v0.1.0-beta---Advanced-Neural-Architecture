import ast
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class AgentOmniscientEyeTool(Tool):
    """
    Agent Omniscient Eye (God Mode HUD)
    Ofera agentului un context 360-grade instant: 
    1. Syntax Check (Prinde erorile de Python inainte de executie)
    2. File Skeleton (AST extras - clase/metode fara a citi tot fisierul)
    3. Git Diff (Ce a stricat/modificat agentul recent)
    4. Error Logs (Ultimele erori reale din sistem)
    """

    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.workspace = self.root.parent

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="agent_omniscient_eye",
            description="[GOD MODE HUD] Tool suprem pentru agenti ca sa nu lucreze 'orbeste'. Ofera: Syntax Check, AST Skeleton, Git Diff curent si Ultimele Erori din log, toate intr-un singur apel.",
            parameters=[
                ToolParameter(
                    name="target_file",
                    description="Calea fisierului la care lucrezi acum (optional)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="log_lines",
                    description="Cate linii de log sa citeasca (default 20)",
                    type="integer",
                    required=False,
                    default=20,
                ),
            ],
            category="ai_core",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        target_file = kwargs.get("target_file", "")
        log_lines = int(kwargs.get("log_lines", 20))
        
        result_data: Dict[str, Any] = {
            "hud_active": True,
            "timestamp": time.time(),
        }

        # 1. Target File Analysis (Syntax & Skeleton)
        if target_file:
            path = Path(target_file)
            if not path.is_absolute():
                path = self.root / path
                
            if path.exists() and path.suffix == ".py":
                result_data["file"] = str(path)
                
                # Syntax Check
                try:
                    import py_compile
                    py_compile.compile(str(path), doraise=True)
                    result_data["syntax_check"] = "PASSED (No Syntax Errors)"
                except py_compile.PyCompileError as e:
                    result_data["syntax_check"] = f"FAILED: {e}"
                except Exception as e:
                    result_data["syntax_check"] = f"ERROR checking syntax: {e}"

                # AST Skeleton (Functions & Classes)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        tree = ast.parse(f.read())
                    skeleton = []
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                            skeleton.append(f"Class: {node.name} -> Methods: {methods}")
                        elif isinstance(node, ast.FunctionDef):
                            skeleton.append(f"Function: {node.name}()")
                    result_data["file_skeleton"] = skeleton
                except Exception as e:
                    result_data["file_skeleton"] = f"AST parse failed: {e}"

                # Git diff
                try:
                    diff = subprocess.check_output(
                        ["git", "diff", "--", str(path)], 
                        cwd=str(self.workspace),
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    result_data["uncommitted_changes"] = diff if diff else "No uncommitted changes."
                except Exception:
                    result_data["uncommitted_changes"] = "Git diff failed or not a git repo."
            else:
                result_data["file_error"] = f"File not found or not .py: {target_file}"

        # 2. System Log Radar
        logs_dir = self.root / "logs"
        recent_errors = []
        if logs_dir.exists():
            for log_file in sorted(logs_dir.glob("*.log"), key=os.path.getmtime, reverse=True)[:2]:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        errs = [l.strip() for l in lines[-100:] if "ERROR" in l or "Exception" in l or "Traceback" in l]
                        if errs:
                            recent_errors.extend(errs[-log_lines:])
                except Exception:
                    pass
        
        result_data["recent_system_errors"] = recent_errors if recent_errors else "No recent errors found in logs."

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=result_data,
            message="Omniscient Eye HUD updated. Look at the data to understand the exact state of your code."
        )
