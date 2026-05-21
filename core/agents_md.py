"""
A.N.A. v17.0 PRO - AGENTS.md Reader (Standard GitHub)
======================================================
Citeste si respecta fisierele AGENTS.md din proiectele utilizatorului.
La fel cum README.md e pentru oameni, AGENTS.md e pentru AI.
ANA nu va face niciodata greseli de stil daca proiectul are AGENTS.md.
"""

import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentsMDReader:
    """
    Citeste regulile din AGENTS.md (sau .cursorrules) si le aplica
    in system prompt-ul ANA pentru proiectul curent.
    
    Fisiere suportate (in ordine de prioritate):
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
        Cauta un fisier de tip AGENTS.md in proiectul dat.
        
        Returns:
            Calea catre fisierul gasit, sau None
        """
        project = Path(project_path).resolve()
        
        for filename in self.SUPPORTED_FILES:
            filepath = project / filename
            if filepath.exists() and filepath.is_file():
                logger.info(f"📋 AGENTS.md gasit: {filepath}")
                return str(filepath)
        
        # Cauta si in subdirectoare de nivel 1 (monorepo support)
        for subdir in project.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                for filename in self.SUPPORTED_FILES[:2]:  # Doar AGENTS.md
                    filepath = subdir / filename
                    if filepath.exists():
                        logger.info(f"📋 AGENTS.md gasit in subdir: {filepath}")
                        return str(filepath)
        
        return None
    
    def read_rules(self, project_path: str = ".") -> Optional[str]:
        """
        Citeste regulile din AGENTS.md pentru un proiect.
        Returneaza continutul sau None daca nu exista.
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
            logger.info(f"📋 Reguli AGENTS.md incarcate ({len(content)} caractere)")
            return content
        except Exception as e:
            logger.error(f"Eroare la citirea {filepath}: {e}")
            return None
    
    def get_prompt_injection(self, project_path: str = ".") -> str:
        """
        Returneaza textul care se adauga la system prompt-ul ANA
        cand lucreaza pe un proiect care are AGENTS.md.
        """
        rules = self.read_rules(project_path)
        if not rules:
            return ""
        
        return f"""
REGULI PROIECT (din AGENTS.md - RESPECTA-LE OBLIGATORIU):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rules}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: Aceste reguli au prioritate maxima. Nu le incalca niciodata.
"""
    
    def parse_structured_rules(self, content: str) -> Dict[str, List[str]]:
        """
        Parseaza regulile structurate din AGENTS.md.
        Returneaza sectiunile principale ca dict.
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
        """Goleste cache-ul."""
        self._cache.clear()
    
    @staticmethod
    def generate_template(project_path: str = ".") -> str:
        """
        Genereaza un template AGENTS.md pentru un proiect nou.
        ANA poate crea automat acest fisier cand analizeaza un proiect.
        """
        project_name = Path(project_path).resolve().name
        
        return f"""# AGENTS.md - Reguli pentru AI ({project_name})

## Structura Proiect
- Descrie aici structura de foldere si conventiile de denumire

## Tehnologii
- Limbaj: Python 3.10+
- Framework: (specifica aici)
- Package Manager: pip / uv

## Reguli de Stil
- Foloseste docstrings pentru functii publice
- Denumiri de variabile in snake_case
- Comentarii in limba romana (sau engleza - specifica)

## Fisiere Protejate (NU MODIFICA)
- config/settings.yaml (fara aprobare explicita)
- .env (contine secrete)

## Conventii Commit
- Format: type(scope): message
- Types: feat, fix, refactor, docs, test

## Reguli Speciale
- (adauga reguli specifice proiectului tau aici)
"""
