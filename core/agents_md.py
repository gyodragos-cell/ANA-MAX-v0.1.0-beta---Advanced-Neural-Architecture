"""
A.N.A. v17.0 PRO - AGENTS.md Reader (Standard GitHub)
======================================================
Citește și respectă fișierele AGENTS.md din proiectele utilizatorului.
La fel cum README.md e pentru oameni, AGENTS.md e pentru AI.
ANA nu va face niciodată greșeli de stil dacă proiectul are AGENTS.md.
"""

import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentsMDReader:
    """
    Citește regulile din AGENTS.md (sau .cursorrules) și le aplică
    în system prompt-ul ANA pentru proiectul curent.
    
    Fișiere suportate (în ordine de prioritate):
    1. AGENTS.md
    2. .agents.md  
    3. .cursorrules
    4. .github/copilot-instructions.md
    """
    
    SUPPORTED_FILES = [
        "AGENTS.md",
        ".agents.md",
        ".cursorrules",
        ".github/copilot-instructions.md",
        "CLAUDE.md",
    ]
    
    def __init__(self):
        self._cache: Dict[str, str] = {}  # path -> content cache
    
    def find_agents_file(self, project_path: str = ".") -> Optional[str]:
        """
        Caută un fișier de tip AGENTS.md în proiectul dat.
        
        Returns:
            Calea către fișierul găsit, sau None
        """
        project = Path(project_path).resolve()
        
        for filename in self.SUPPORTED_FILES:
            filepath = project / filename
            if filepath.exists() and filepath.is_file():
                logger.info(f"📋 AGENTS.md găsit: {filepath}")
                return str(filepath)
        
        # Caută și în subdirectoare de nivel 1 (monorepo support)
        for subdir in project.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                for filename in self.SUPPORTED_FILES[:2]:  # Doar AGENTS.md
                    filepath = subdir / filename
                    if filepath.exists():
                        logger.info(f"📋 AGENTS.md găsit în subdir: {filepath}")
                        return str(filepath)
        
        return None
    
    def read_rules(self, project_path: str = ".") -> Optional[str]:
        """
        Citește regulile din AGENTS.md pentru un proiect.
        Returnează conținutul sau None dacă nu există.
        """
        # Check cache
        cache_key = str(Path(project_path).resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        filepath = self.find_agents_file(project_path)
        if not filepath:
            return None
        
        try:
            content = Path(filepath).read_text(encoding='utf-8')
            self._cache[cache_key] = content
            logger.info(f"📋 Reguli AGENTS.md încărcate ({len(content)} caractere)")
            return content
        except Exception as e:
            logger.error(f"Eroare la citirea {filepath}: {e}")
            return None
    
    def get_prompt_injection(self, project_path: str = ".") -> str:
        """
        Returnează textul care se adaugă la system prompt-ul ANA
        când lucrează pe un proiect care are AGENTS.md.
        """
        rules = self.read_rules(project_path)
        if not rules:
            return ""
        
        return f"""
REGULI PROIECT (din AGENTS.md - RESPECTĂ-LE OBLIGATORIU):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rules}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: Aceste reguli au prioritate maximă. Nu le încălca niciodată.
"""
    
    def parse_structured_rules(self, content: str) -> Dict[str, List[str]]:
        """
        Parsează regulile structurate din AGENTS.md.
        Returnează secțiunile principale ca dict.
        """
        sections: Dict[str, List[str]] = {}
        current_section = "general"
        sections[current_section] = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                current_section = line[2:].strip().lower()
                sections[current_section] = []
            elif line.startswith('## '):
                current_section = line[3:].strip().lower()
                sections[current_section] = []
            elif line and not line.startswith('---'):
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)
        
        return sections
    
    def clear_cache(self):
        """Golește cache-ul."""
        self._cache.clear()
    
    @staticmethod
    def generate_template(project_path: str = ".") -> str:
        """
        Generează un template AGENTS.md pentru un proiect nou.
        ANA poate crea automat acest fișier când analizează un proiect.
        """
        project_name = Path(project_path).resolve().name
        
        return f"""# AGENTS.md - Reguli pentru AI ({project_name})

## Structură Proiect
- Descrie aici structura de foldere și convențiile de denumire

## Tehnologii
- Limbaj: Python 3.10+
- Framework: (specifică aici)
- Package Manager: pip / uv

## Reguli de Stil
- Folosește docstrings pentru funcții publice
- Denumiri de variabile în snake_case
- Comentarii în limba română (sau engleză - specifică)

## Fișiere Protejate (NU MODIFICA)
- config/settings.yaml (fără aprobare explicită)
- .env (conține secrete)

## Convenții Commit
- Format: type(scope): message
- Types: feat, fix, refactor, docs, test

## Reguli Speciale
- (adaugă reguli specifice proiectului tău aici)
"""
