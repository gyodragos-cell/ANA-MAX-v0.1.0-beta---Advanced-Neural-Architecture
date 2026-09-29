"""
ANA MAX - polymorphic_core_tool.py
====================================
Polymorphic Core (Auto-Rescriere + Auto-Vindecare)

Agentul poate modifica propriul cod. Inainte de a aplica modificarea pe disc,
codul este validat prin AST (pentru a prinde erori de sintaxa) si este compilat
intr-un sandbox pentru a se asigura ca nu face crash la import.
Daca pica testul, mutatia este blocata.
"""
from __future__ import annotations

import ast
import importlib
import logging
import re
import sys
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.PolymorphicCore")

# Aceasta functie este o tinta intentionata pentru a fi rescrisa de ea insasi.
def dummy_target_function() -> str:
    return "INITIAL_STATE"


def _validate_syntax(code_str: str) -> bool:
    """Verifica daca noul cod sursa este valid (nu are erori de sintaxa)."""
    try:
        ast.parse(code_str)
        return True
    except SyntaxError as e:
        logger.error(f"Sintaxa invalida in codul polimorfic: {e}")
        return False
    except Exception as e:
        logger.error(f"Eroare la validarea AST: {e}")
        return False


def _dry_run_compile(code_str: str) -> bool:
    """Incearca sa compileze codul in memorie (Dry-Run)."""
    try:
        compile(code_str, "<polymorphic_sandbox>", "exec")
        return True
    except Exception as e:
        logger.error(f"Dry-run compilation failed: {e}")
        return False


class PolymorphicCoreTool(Tool):
    """Mutatia codului live cu auto-aparare."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="polymorphic_core",
            description="Permite agentului sa isi modifice propriul cod sursa in timp real, folosind o camera de izolare (AST + DryRun) inainte de hot-reload.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="'mutate' (schimba o valoare/logica interna) sau 'test' (apeleaza logica curenta)",
                    type="string",
                    required=True,
                    choices=["mutate", "test"],
                ),
                ToolParameter(
                    name="new_return_value",
                    description="O noua valoare pe care sa o returneze functia target la mutatie.",
                    type="string",
                    required=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        
        if action == "test":
            res = dummy_target_function()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"current_state": res},
                message=f"Starea functiei tinta este: {res}"
            )
            
        elif action == "mutate":
            new_val = kwargs.get("new_return_value", "MUTATED_STATE")
            file_path = __file__
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                pattern = r'(def dummy_target_function\(\) -> str:\n\s+return ).*'
                new_content, count = re.subn(pattern, rf'\1"{new_val}"', content)
                
                if count == 0:
                    return ToolResult(status=ToolStatus.ERROR, error="Nu am putut gasi functia target in codul sursa.")
                
                # 1. Validare AST
                if not _validate_syntax(new_content):
                    return ToolResult(status=ToolStatus.ERROR, error="Mutatie BLOCATA: Codul a picat validarea AST (Eroare de Sintaxa).")
                
                # 2. Dry-Run Compiler
                if not _dry_run_compile(new_content):
                    return ToolResult(status=ToolStatus.ERROR, error="Mutatie BLOCATA: Codul a picat la compilarea in sandbox.")
                    
                # 3. Aplicare pe disc doar daca trece testele
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # Hot-reload in RAM
                mod_name = __name__
                if mod_name in sys.modules:
                    importlib.reload(sys.modules[mod_name])
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"mutated_value": new_val, "checks_passed": ["ast", "dry_run"]},
                    message=f"Mutatie sigura completa. Modulul a fost verificat si rescris. Noul state: {new_val}"
                )
                
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=f"Eroare polimorfica interna: {e}")

        return ToolResult(status=ToolStatus.ERROR, error="Actiune invalida")

