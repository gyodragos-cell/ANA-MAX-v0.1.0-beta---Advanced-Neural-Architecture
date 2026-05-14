"""
A.N.A. v17.0 PRO - Surgical Edit Engine (Inspirat de Aider)
============================================================
Editare chirurgicală de cod la nivel de bloc (Search & Replace).
În loc să rescrie fișiere întregi, ANA trimite doar diff-uri.
Optimizat pentru GPU-uri modeste (GTX 1650) - economisește tokens Ollama.
"""

import os
import re
import difflib
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SurgicalEdit:
    """Un singur edit chirurgical: înlocuiește un bloc de cod cu altul."""
    def __init__(self, file_path: str, old_block: str, new_block: str, description: str = ""):
        self.file_path = file_path
        self.old_block = old_block
        self.new_block = new_block
        self.description = description


class SurgicalEditEngine:
    """
    Motor de editare chirurgicală inspirat de Aider.
    
    În loc să ceară LLM-ului să regenereze un fișier întreg (lent pe 1650),
    cere doar blocuri SEARCH/REPLACE mici. Economisește 50-80% din tokeni.
    """
    
    # Formatul pe care ANA îl va folosi în prompturi
    EDIT_FORMAT = """<<<<<<< SEARCH
{old_code}
=======
{new_code}
>>>>>>> REPLACE"""

    EDIT_PROMPT_TEMPLATE = """Când trebuie să modifici cod, folosește ÎNTOTDEAUNA formatul SEARCH/REPLACE:

Fișier: {file_path}
<<<<<<< SEARCH
(codul exact care există acum - copie fidelă)
=======
(codul nou care îl înlocuiește)
>>>>>>> REPLACE

REGULI:
- Copiază EXACT blocul vechi (inclusiv spații, indentare)
- Poți da mai multe blocuri SEARCH/REPLACE pentru același fișier
- NU rescrie fișierul întreg, doar blocurile afectate
"""

    def __init__(self):
        self.history: List[Dict] = []  # Istoric de editări pentru undo
        self.stats = {"edits_applied": 0, "edits_failed": 0, "tokens_saved_estimate": 0}
    
    def parse_edit_response(self, response: str) -> List[SurgicalEdit]:
        """
        Parsează răspunsul LLM-ului și extrage blocurile SEARCH/REPLACE.
        Suportă mai multe editări în același răspuns.
        """
        edits = []
        
        # Extrage fișierul țintă (dacă e specificat)
        file_match = re.findall(r'(?:Fișier|File|fisier):\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        current_file = file_match[0].strip() if file_match else None
        
        # Pattern pentru blocuri SEARCH/REPLACE
        pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for old_block, new_block in matches:
            edits.append(SurgicalEdit(
                file_path=current_file or "",
                old_block=old_block,
                new_block=new_block
            ))
        
        return edits
    
    def apply_edit(self, edit: SurgicalEdit) -> Tuple[bool, str]:
        """
        Aplică o editare chirurgicală pe un fișier.
        
        Returns:
            (success, message)
        """
        file_path = Path(edit.file_path)
        
        if not file_path.exists():
            self.stats["edits_failed"] += 1
            return False, f"Fișierul nu există: {edit.file_path}"
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.stats["edits_failed"] += 1
            return False, f"Nu pot citi fișierul: {e}"
        
        # Caută blocul exact
        if edit.old_block in content:
            new_content = content.replace(edit.old_block, edit.new_block, 1)
            
            # Salvează backup în istorie (pentru undo)
            self.history.append({
                "file": str(file_path),
                "original": content,
                "modified": new_content,
                "edit": {"old": edit.old_block, "new": edit.new_block}
            })
            
            file_path.write_text(new_content, encoding='utf-8')
            self.stats["edits_applied"] += 1
            
            # Estimare tokeni economisiți (vs rescrierea întregului fișier)
            tokens_full = len(content.split()) 
            tokens_edit = len(edit.old_block.split()) + len(edit.new_block.split())
            self.stats["tokens_saved_estimate"] += max(0, tokens_full - tokens_edit)
            
            logger.info(f"✂️ Edit chirurgical aplicat: {file_path} (~{tokens_full - tokens_edit} tokeni economisiți)")
            return True, f"Edit aplicat cu succes în {file_path}"
        
        # Fallback: caută cu fuzzy matching (toleranță la whitespace)
        normalized_content = re.sub(r'\s+', ' ', content)
        normalized_old = re.sub(r'\s+', ' ', edit.old_block)
        
        if normalized_old in normalized_content:
            # Găsește blocul real cu whitespace original
            lines = content.split('\n')
            old_lines = edit.old_block.split('\n')
            
            for i in range(len(lines) - len(old_lines) + 1):
                chunk = '\n'.join(lines[i:i + len(old_lines)])
                if re.sub(r'\s+', ' ', chunk) == normalized_old:
                    new_content = content.replace(chunk, edit.new_block, 1)
                    self.history.append({
                        "file": str(file_path),
                        "original": content,
                        "modified": new_content
                    })
                    file_path.write_text(new_content, encoding='utf-8')
                    self.stats["edits_applied"] += 1
                    logger.info(f"✂️ Edit chirurgical (fuzzy) aplicat: {file_path}")
                    return True, f"Edit aplicat (fuzzy match) în {file_path}"
        
        self.stats["edits_failed"] += 1
        return False, f"Blocul SEARCH nu a fost găsit în {file_path}"
    
    def apply_edits(self, edits: List[SurgicalEdit]) -> List[Tuple[bool, str]]:
        """Aplică o listă de editări chirurgicale."""
        results = []
        for edit in edits:
            results.append(self.apply_edit(edit))
        return results
    
    def undo_last(self) -> Tuple[bool, str]:
        """Anulează ultima editare."""
        if not self.history:
            return False, "Nu există editări de anulat."
        
        last = self.history.pop()
        try:
            Path(last["file"]).write_text(last["original"], encoding='utf-8')
            return True, f"Undo reușit pentru {last['file']}"
        except Exception as e:
            return False, f"Eroare la undo: {e}"
    
    def generate_diff(self, edit: SurgicalEdit) -> str:
        """Generează un diff vizual pentru preview."""
        old_lines = edit.old_block.splitlines(keepends=True)
        new_lines = edit.new_block.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"{edit.file_path} (original)",
            tofile=f"{edit.file_path} (modificat)",
            lineterm=''
        )
        return ''.join(diff)
    
    def get_edit_instruction(self, file_path: str) -> str:
        """Returnează instrucțiunea de edit pentru un fișier specific (se adaugă în prompt)."""
        return self.EDIT_PROMPT_TEMPLATE.format(file_path=file_path)
    
    def get_stats(self) -> Dict:
        return self.stats.copy()
