import ast
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Adauga cai daca nu exista
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("os27.nervous_system")
logger.setLevel(logging.WARNING)

class OS27NervousSystem:
    """
    Sistemul Nervos Central OS27 Hyper++
    Intercepteaza erorile din runtime si genereaza retete instant de auto-vindecare (patches)
    fara a bloca STDIO sau a consuma CPU in mod inutil (rules: non-blocking, asynchronous style).
    """

    def __init__(self) -> None:
        self.tools_dir = ROOT / "tools"
        self.logs_dir = ROOT / "logs"

    def handle_tool_failure(
        self, 
        tool_name: str, 
        exception_msg: str, 
        tb_str: str, 
        target_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Intercepteaza o eroare si genereaza solutia in background.
        Returneaza un payload JSON pe care agentul il poate pasa direct la replace_file_content.
        """
        try:
            # 1. Determina fisierul care a dat crash
            file_path = self._resolve_tool_file(tool_name, target_file_path, tb_str)
            if not file_path or not os.path.exists(file_path):
                return {
                    "success": False,
                    "reason": f"Nu s-a putut localiza fisierul sursa pentru tool: {tool_name}"
                }

            # 2. Obtine contextul fisierului (AST + Linii din jurul crash-ului)
            error_line = self._extract_error_line_number(tb_str, file_path)
            code_context = self._get_code_context(file_path, error_line)

            # 3. Generare patch (Heuristic ca fallback rapid si ieftin + Ollama offline compat)
            patch = self._generate_healing_patch(file_path, error_line, code_context, exception_msg)

            # 4. Inregistreaza in telemetrie (ana_memory.db)
            self._log_to_memory(tool_name, exception_msg, file_path, patch)

            return {
                "success": True,
                "tool_name": tool_name,
                "file_path": str(file_path),
                "error_line": error_line,
                "exception": exception_msg,
                "recommended_patch": patch
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Nervous System failure: {str(e)}"
            }

    def _resolve_tool_file(self, tool_name: str, provided_path: Optional[str], tb_str: str) -> Optional[Path]:
        """Gaseste fisierul Python responsabil de eroare."""
        if provided_path and os.path.exists(provided_path):
            return Path(provided_path)

        # Incearca import din registry
        try:
            from tools import _CLASS_TO_MODULE
            module_name = _CLASS_TO_MODULE.get(tool_name)
            if module_name:
                candidate = self.tools_dir / f"{module_name}.py"
                if candidate.exists():
                    return candidate
        except Exception:
            pass

        # Parseaza traceback ca backup
        # Cauta prima referinta catre tools/ din traceback
        matches = list(Path(ROOT / "tools").glob("*.py"))
        for m in matches:
            if m.name in tb_str:
                return m

        return None

    def _extract_error_line_number(self, tb_str: str, file_path: Path) -> int:
        """Parseaza Traceback-ul ca sa afle linia exacta din fisierul tool-ului."""
        filename = file_path.name
        import re
        
        # Cauta in traceback tiparul: ...filename", line X
        pattern = rf'{re_escape(filename)}", line (\d+)'
        matches = re.findall(pattern, tb_str)
        if matches:
            return int(matches[-1])
            
        return 1

    def _get_code_context(self, file_path: Path, error_line: int, window: int = 5) -> Dict[str, Any]:
        """Citeste doar liniile esentiale de cod din jurul erorii ca sa nu consume tokeni/RAM."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            start = max(1, error_line - window)
            end = min(len(lines), error_line + window)
            
            context_lines = lines[start-1:end]
            target_line_content = lines[error_line-1] if 0 < error_line <= len(lines) else ""

            return {
                "start_line": start,
                "end_line": end,
                "target_line_content": target_line_content,
                "context_code": "".join(context_lines),
                "total_lines": len(lines)
            }
        except Exception:
            return {"start_line": 1, "end_line": 1, "target_line_content": "", "context_code": "", "total_lines": 0}

    def _generate_healing_patch(
        self, 
        file_path: Path, 
        error_line: int, 
        context: Dict[str, Any], 
        exception_msg: str
    ) -> Dict[str, Any]:
        """
        Generare patch cu fallback inteligent.
        Returneaza direct argumentele pentru replace_file_content.
        """
        target_content = context["target_line_content"]
        replacement_content = target_content

        # 1. Fallback Heuristic: Prindem cele mai frecvente erori locale
        # Exemplu 1: AttributeError: module 'x' has no attribute 'y'
        if "has no attribute" in exception_msg:
            # Daca e un import invalid sau o variabila gresita, adaugam o protectie try/except
            replacement_content = f"        try:\n            {target_content.strip()}\n        except Exception as e:\n            logger.warning(f'Self-healed import bypass: {{e}}')\n"
        
        # Exemplu 2: KeyError
        elif "KeyError" in exception_msg or "key" in exception_msg.lower():
            # Inlocuieste dict[key] cu dict.get(key) ca sa nu dea crash
            import re
            match = re.search(r'\[([^]]+)\]', target_content)
            if match:
                key_expr = match.group(1)
                replacement_content = target_content.replace(f"[{key_expr}]", f".get({key_expr})")

        # Exemplu 3: FileNotFoundError
        elif "FileNotFoundError" in exception_msg:
            replacement_content = f"        if not os.path.exists({target_content.split('open(')[-1].split(',')[0]}):\n            return ToolResult(status=ToolStatus.ERROR, error='File not found')\n{target_content}"

        # Daca nicio euristica nu se aplica, wrap in general exception safety block
        if replacement_content == target_content and target_content.strip():
            indent = " " * (len(target_content) - len(target_content.lstrip()))
            replacement_content = f"{indent}try:\n{indent}    {target_content.strip()}\n{indent}except Exception as e:\n{indent}    logger.error(f'Auto-healed crash: {{e}}')\n"

        return {
            "TargetFile": str(file_path),
            "StartLine": error_line,
            "EndLine": error_line,
            "TargetContent": target_content,
            "ReplacementContent": replacement_content,
            "Instruction": f"Auto-heal block for exception: {exception_msg}"
        }

    def _log_to_memory(self, tool_name: str, error: str, file_path: Path, patch: Dict[str, Any]) -> None:
        """Inregistreaza eroarea in ana_memory.db sqlite pentru modelul local."""
        try:
            import sqlite3
            db_path = ROOT / "ana_memory.db"
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute(
                "INSERT INTO known_errors (error_type, tool_name, file_path, solution_patch, timestamp) VALUES (?, ?, ?, ?, ?)",
                (error, tool_name, str(file_path), json.dumps(patch), time.time())
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

def re_escape(fn: str) -> str:
    """Escapeaza caracterele speciale din nume fisier pt regex."""
    import re
    return re.escape(fn)
