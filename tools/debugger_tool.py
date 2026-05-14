"""
A.N.A. v15.0 - Debugger Tool
=============================
Instrument pentru diagnoză și reparare automată a erorilor.
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
    Tool care analizează erori și propune reparații.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="debugger",
            description="Analiză de traceback și propuneri de reparații automate.",
            parameters=[
                ToolParameter(
                    name="traceback_text",
                    description="Textul erorii / traceback-ului din consolă",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    description="Ațiunea: 'analyze' | 'fix_proposal'",
                    type="string",
                    required=False,
                    default="analyze",
                    choices=["analyze", "fix_proposal"]
                )
            ],
            category="code"
        )

    def execute(self, **kwargs) -> ToolResult:
        """Execută analiza de debugging."""
        traceback_text = kwargs.get('traceback_text', '')
        action = kwargs.get('action', 'analyze')
        
        if not traceback_text:
            return ToolResult(status=ToolStatus.ERROR, error="Traceback-ul lipsește.")
            
        try:
            # 1. Parsăm traceback-ul pentru a găsi fișierul și linia
            error_info = self._parse_traceback(traceback_text)
            
            if action == 'analyze':
                return self._analyze_error(error_info, traceback_text)
            elif action == 'fix_proposal':
                return self._propose_fix(error_info, traceback_text)
            
            return ToolResult(status=ToolStatus.ERROR, error=f"Acțiune necunoscută: {action}")
        except Exception as e:
            logger.error(f"Debugger failed: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _parse_traceback(self, text: str) -> Dict[str, Any]:
        """Extrage fișierul, linia și tipul erorii dintr-un traceback Python."""
        # Căutăm ultima linie "File ..., line ..., in ..."
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
        """Analizează eroarea folosind RAG."""
        from core.codebase_understanding import get_codebase_understanding
        rag = get_codebase_understanding()
        
        # Căutăm fragmente de cod relevante pentru tipul de eroare și fișier
        query = f"Error {info['type']} in {info['file']} at line {info['line']}: {info['message']}"
        search_results = rag.semantic_search(query, limit=3)
        
        analysis = [
            f"🔍 **DIAGNOZĂ EROARE**",
            f"• **Tip**: `{info['type']}`",
            f"• **Locație**: `{info['file']}` (Linia {info['line']})",
            f"• **Mesaj**: {info['message']}",
            "\n**Context din cod (via RAG):**"
        ]
        
        for res in search_results:
            analysis.append(f"- In `{res['file']}`: {res['content'][:150]}...")
            
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"analysis": analysis, "info": info},
            message="✓ Analiză eroare finalizată"
        )

    def _propose_fix(self, info: Dict, original_text: str) -> ToolResult:
        """Propune o reparație (concept)."""
        # Aici ideal am apela AI-ul pentru a genera fix-ul, dar tool-ul 
        # returnează datele necesare pentru ca ANA să decidă.
        
        fix_plan = f"""Plan de reparație:
1. Analizează fișierul `{info['file']}` în jurul liniei {info['line']}.
2. Verifică de ce apare `{info['type']}`.
3. Aplică un fix care să trateze: {info['message']}
"""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"fix_plan": fix_plan, "info": info},
            message="✓ Plan de reparație generat"
        )
