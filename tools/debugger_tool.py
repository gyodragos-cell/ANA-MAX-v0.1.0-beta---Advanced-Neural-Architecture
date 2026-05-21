"""
A.N.A. v15.0 - Debugger Tool
=============================
Instrument pentru diagnoza si reparare automata a erorilor.
"""

import re
import logging
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class DebuggerTool(Tool):
    """
    Tool care analizeaza erori si propune reparatii.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="debugger",
            description="Analiza de traceback si propuneri de reparatii automate.",
            parameters=[
                ToolParameter(
                    name="traceback_text",
                    description="Textul erorii / traceback-ului din consola",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    description="Atiunea: 'analyze' | 'fix_proposal'",
                    type="string",
                    required=False,
                    default="analyze",
                    choices=["analyze", "fix_proposal"]
                )
            ],
            category="code"
        )

    def execute(self, **kwargs) -> ToolResult:
        """Executa analiza de debugging."""
        traceback_text = kwargs.get('traceback_text', '')
        action = kwargs.get('action', 'analyze')
        
        if not traceback_text:
            return ToolResult(status=ToolStatus.ERROR, error="Traceback-ul lipseste.")
            
        try:
            # 1. Parsam traceback-ul pentru a gasi fisierul si linia
            error_info = self._parse_traceback(traceback_text)
            
            if action == 'analyze':
                return self._analyze_error(error_info, traceback_text)
            elif action == 'fix_proposal':
                return self._propose_fix(error_info, traceback_text)
            
            return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
        except Exception as e:
            logger.error(f"Debugger failed: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _parse_traceback(self, text: str) -> Dict[str, Any]:
        """Extrage fisierul, linia si tipul erorii dintr-un traceback Python."""
        # Cautam ultima linie "File ..., line ..., in ..."
        file_matches = re.findall(r'File "([^"]+)", line (\d+)', text)
        error_match = re.search(r'^(\w+): (.*)$', text.splitlines()[-1])
        
        last_file = file_matches[-1][0] if file_matches else "unknown"
        last_line = int(file_matches[-1][1]) if file_matches else 0
        error_type = error_match.group(1) if error_match else "UnknownError"
        error_msg = error_match.group(2) if error_match else text.splitlines()[-1]
        
        return {
            "file": last_file,
            "line": last_line,
            "type": error_type,
            "message": error_msg,
            "all_files": list(set([m[0] for m in file_matches]))
        }

    def _analyze_error(self, info: Dict, original_text: str) -> ToolResult:
        """Analizeaza eroarea folosind RAG."""
        from core.codebase_understanding import get_codebase_understanding
        rag = get_codebase_understanding()
        
        # Cautam fragmente de cod relevante pentru tipul de eroare si fisier
        query = f"Error {info['type']} in {info['file']} at line {info['line']}: {info['message']}"
        search_results = rag.semantic_search(query, limit=3)
        
        analysis = [
            f"🔍 **DIAGNOZA EROARE**",
            f"• **Tip**: `{info['type']}`",
            f"• **Locatie**: `{info['file']}` (Linia {info['line']})",
            f"• **Mesaj**: {info['message']}",
            "\n**Context din cod (via RAG):**"
        ]
        
        for res in search_results:
            analysis.append(f"- In `{res['file']}`: {res['content'][:150]}...")
            
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"analysis": analysis, "info": info},
            message="✓ Analiza eroare finalizata"
        )

    def _propose_fix(self, info: Dict, original_text: str) -> ToolResult:
        """Propune o reparatie (concept)."""
        # Aici ideal am apela AI-ul pentru a genera fix-ul, dar tool-ul 
        # returneaza datele necesare pentru ca ANA sa decida.
        
        fix_plan = f"""Plan de reparatie:
1. Analizeaza fisierul `{info['file']}` in jurul liniei {info['line']}.
2. Verifica de ce apare `{info['type']}`.
3. Aplica un fix care sa trateze: {info['message']}
"""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"fix_plan": fix_plan, "info": info},
            message="✓ Plan de reparatie generat"
        )
