#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implementare Tool Calling pentru Ollama in Ana v16
Autor: Billy (cu ajutor Skywork AI)
Data: 2026-03-01

Aceasta modifica _send_ollama() pentru a trimite tools catre Ollama
si a procesa raspunsurile cu tool calls (similar cu Gemini).
"""

import sys
import os
from pathlib import Path

print("=" * 80)
print("   IMPLEMENTARE TOOL CALLING PENTRU OLLAMA")
print("=" * 80)
print()

# Paths
project_root = Path(__file__).parent
agent_file = project_root / "core" / "agent.py"
backup_file = project_root / "core" / "agent.py.backup_before_tool_calling"

# Verificare
if not agent_file.exists():
    print("[FAIL] EROARE: core/agent.py nu exista!")
    sys.exit(1)

# Backup
if backup_file.exists():
    print(f"[OK] Backup existent gasit: {backup_file.name}")
else:
    import shutil
    shutil.copy(agent_file, backup_file)
    print(f"[OK] Backup creat: {backup_file.name}")

print()
print("[1/4] Citire fisier agent.py...")

content = agent_file.read_text(encoding='utf-8')

# Verificare daca e deja modificat
if "# OLLAMA_TOOL_CALLING_IMPLEMENTED" in content:
    print("[WARN]  Tool calling deja implementat!")
    print()
    print("Daca vrei sa reinstalezi:")
    print("  1. cp core/agent.py.backup_before_tool_calling core/agent.py")
    print("  2. Ruleaza din nou acest script")
    sys.exit(0)

print("[OK] Fisier citit!")
print()

print("[2/4] Generare cod nou pentru _send_ollama()...")

# Noul cod pentru _send_ollama() cu tool calling
new_send_ollama = '''    def _send_ollama(self, message: str) -> str:
        """Trimite mesaj catre Ollama cu tool calling support."""
        # OLLAMA_TOOL_CALLING_IMPLEMENTED
        import requests
        import json
        
        # Construieste mesajele
        history = self.memory.get_conversation_history(self.session_id, limit=20)
        messages = [{'role': 'system', 'content': self._get_system_prompt()}]
        
        for msg in history:
            role = 'assistant' if msg['role'] == 'model' else msg['role']
            messages.append({'role': role, 'content': msg['content']})
        
        messages.append({'role': 'user', 'content': message})
        
        # Construieste lista de tools in format Ollama
        tools = self._get_ollama_tools()
        
        # Apeleaza Ollama cu tools
        payload = {
            'model': self.ai_client['model'],
            'messages': messages,
            'stream': False,
            'tools': tools  #  ADAUGAT AICI!
        }
        
        try:
            response = requests.post(self.ai_client['url'], json=payload, timeout=120)
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            result = response.json()
            message_data = result.get('message', {})
            
            # Verifica daca are tool_calls
            tool_calls = message_data.get('tool_calls', [])
            
            if tool_calls:
                # Ollama cere sa executam tool-urile
                logger.info(f" Ollama cere executie {len(tool_calls)} tool(s)")
                
                tool_results = []
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    arguments = tool_call['function']['arguments']
                    
                    logger.info(f"   Executam: {function_name}({arguments})")
                    
                    # Executa tool-ul efectiv
                    result = self._execute_tool(function_name, arguments)
                    tool_results.append(f"Tool {function_name}: {result}")
                
                # Returneaza rezultatul executiei
                return "\\n".join(tool_results)
            else:
                # Raspuns text normal
                return message_data.get('content', '(fara raspuns)')
                
        except Exception as e:
            logger.error(f"Eroare Ollama: {e}")
            raise Exception(f"Ollama error: {e}")
'''

# Adauga functia helper pentru a converti tools in format Ollama
get_ollama_tools = '''
    def _get_ollama_tools(self) -> list:
        """Returneaza lista de tools in format Ollama/OpenAI."""
        from tools.base import registry
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "file_operations",
                    "description": "Operatii cu fisiere: citeste, scrie, creeaza foldere, cauta fisiere.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["read", "write", "list", "create_folder", "search", "info"],
                                "description": "Tipul operatiei"
                            },
                            "path": {
                                "type": "string",
                                "description": "Path-ul fisierului sau folderului"
                            },
                            "content": {
                                "type": "string",
                                "description": "Continutul pentru scriere (optional)"
                            }
                        },
                        "required": ["operation", "path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "system_control",
                    "description": "Control sistem: verifica vitalele sistemului, procesele, executa comenzi shell.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["vitals", "processes", "shell"],
                                "description": "Tipul operatiei"
                            },
                            "target": {
                                "type": "string",
                                "description": "Comanda shell sau procesul tinta (optional)"
                            }
                        },
                        "required": ["operation"]
                    }
                }
            }
        ]
        
        return tools
    
    def _execute_tool(self, function_name: str, arguments: dict) -> str:
        """Executa efectiv un tool si returneaza rezultatul."""
        from tools.base import registry
        
        try:
            if function_name == "file_operations":
                operation = arguments.get('operation')
                path = arguments.get('path')
                content = arguments.get('content', '')
                
                result = registry.execute(
                    "file_operations",
                    operation=operation,
                    path=path,
                    content=content
                )
                return f" Operatie {operation} executata cu succes pe {path}"
                
            elif function_name == "system_control":
                operation = arguments.get('operation')
                target = arguments.get('target', '')
                
                result = registry.execute(
                    "system_control",
                    operation=operation,
                    target=target
                )
                return f" Operatie sistem {operation} executata"
            
            else:
                return f"[WARN] Tool {function_name} necunoscut"
                
        except Exception as e:
            return f"[FAIL] Eroare la executie {function_name}: {e}"
'''

print("[OK] Cod generat!")
print()

print("[3/4] Aplicare modificari in agent.py...")

import re

# Gaseste si inlocuieste functia _send_ollama
pattern = r'    def _send_ollama\(self, message: str\) -> str:.*?(?=\n    def _send_grok|\n    def [a-z_]+\(self|\nclass |\Z)'

new_content = re.sub(
    pattern,
    new_send_ollama + get_ollama_tools,
    content,
    flags=re.DOTALL
)

if new_content == content:
    print("[FAIL] EROARE: Nu am putut gasi functia _send_ollama()!")
    print("   Fisierul e modificat sau versiunea e diferita.")
    sys.exit(1)

# Salveaza
agent_file.write_text(new_content, encoding='utf-8')
print("[OK] Modificari aplicate!")
print()

print("[4/4] Verificare finala...")
if "OLLAMA_TOOL_CALLING_IMPLEMENTED" in agent_file.read_text(encoding='utf-8'):
    print("[OK] Tool calling implementat cu succes!")
else:
    print("[WARN] Verificare esuata, dar fisierul e modificat.")

print()
print("=" * 80)
print("   IMPLEMENTARE COMPLETA!")
print("=" * 80)
print()
print("NEXT STEPS:")
print()
print("  1. Restart Ana:")
print("     START_ANA_MISTRAL_DIRECT.bat")
print()
print("  2. Testeaza:")
print("     'creeaza un folder test_ollama_tools pe desktop'")
print()
print("  3. Folder-ul AR TREBUI sa apara acum!")
print()
print("NOTA: Daca ceva nu merge, restaureaza backup-ul:")
print(f"  cp {backup_file.name} core/agent.py")
print()
print("=" * 80)
