#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemple de cod pentru extindere tool calling
Adauga aceste pattern-uri in core/agent.py -> _send_ollama()
"""

import re
import shutil
from pathlib import Path

# ========================================
# EXEMPLU 1: Stergere folder
# ========================================
r"""
Adauga in _send_ollama() dupa pattern-ul de creare fisier:

        # Detectare comanda stergere folder
        if re.search(r'(sterge|delete|remove).*?(folder|director)', message, re.I):
            try:
                desktop = Path.home() / "Desktop"
                
                # Extrage nume folder
                name_match = re.search(r'folder\s+["\']?(\w+)["\']?', message, re.I)
                
                if name_match:
                    folder_name = name_match.group(1)
                    folder_path = desktop / folder_name
                    
                    if folder_path.exists() and folder_path.is_dir():
                        shutil.rmtree(folder_path)
                        return f" Folder '{folder_name}' sters cu succes!"
                    else:
                        return f"[FAIL] Folder-ul '{folder_name}' nu exista pe Desktop."
                else:
                    return "[FAIL] Nu am putut detecta numele folder-ului de sters."
                    
            except Exception as e:
                return f"[FAIL] Eroare la stergere folder: {e}"
"""

# ========================================
# EXEMPLU 2: Listare fisiere din folder
# ========================================
r"""
Adauga in _send_ollama():

        # Detectare comanda listare fisiere
        if re.search(r'(listeaza|list|afiseaza|arata).*?(fi[ss]ier|foldere|continut)', message, re.I):
            try:
                desktop = Path.home() / "Desktop"
                
                # Extrage folder tinta (optional)
                folder_match = re.search(r'din\s+folder\s+["\']?(\w+)["\']?', message, re.I)
                
                if folder_match:
                    target = desktop / folder_match.group(1)
                else:
                    target = desktop
                
                if not target.exists():
                    return f"[FAIL] Folder-ul nu exista: {target}"
                
                # Listeaza continut
                items = list(target.iterdir())
                
                if not items:
                    return f" Folder-ul '{target.name}' este gol."
                
                # Formatare rezultat
                folders = [f" {item.name}" for item in items if item.is_dir()]
                files = [f" {item.name}" for item in items if item.is_file()]
                
                result = f" Continut {target.name}:\\n\\n"
                if folders:
                    result += "Foldere:\\n" + "\\n".join(folders) + "\\n\\n"
                if files:
                    result += "Fisiere:\\n" + "\\n".join(files)
                
                return result
                
            except Exception as e:
                return f"[FAIL] Eroare la listare: {e}"
"""

# ========================================
# EXEMPLU 3: Citire continut fisier
# ========================================
r"""
Adauga in _send_ollama():

        # Detectare comanda citire fisier
        if re.search(r'(citeste|read|deschide|arata).*?fi[ss]ier', message, re.I):
            try:
                desktop = Path.home() / "Desktop"
                
                # Extrage nume fisier
                name_match = re.search(r'fi[ss]ier\s+([\w\.]+)', message, re.I)
                
                if name_match:
                    file_name = name_match.group(1)
                    file_path = desktop / file_name
                    
                    if file_path.exists() and file_path.is_file():
                        content = file_path.read_text(encoding='utf-8')
                        return f" Continut {file_name}:\\n\\n{content}"
                    else:
                        return f"[FAIL] Fisierul '{file_name}' nu exista pe Desktop."
                else:
                    return "[FAIL] Nu am putut detecta numele fisierului."
                    
            except Exception as e:
                return f"[FAIL] Eroare la citire fisier: {e}"
"""

# ========================================
# EXEMPLU 4: Redenumire folder/fisier
# ========================================
r"""
Adauga in _send_ollama():

        # Detectare comanda redenumire
        if re.search(r'(redenumeste|rename|schimba\\s+nume)', message, re.I):
            try:
                desktop = Path.home() / "Desktop"
                
                # Extrage nume vechi si nou
                rename_match = re.search(r'(folder|fi[ss]ier)\s+(\w+)\s+(?:in|to|ca)\s+(\w+)', message, re.I)
                
                if rename_match:
                    item_type = rename_match.group(1)
                    old_name = rename_match.group(2)
                    new_name = rename_match.group(3)
                    
                    old_path = desktop / old_name
                    new_path = desktop / new_name
                    
                    if old_path.exists():
                        old_path.rename(new_path)
                        return f" {item_type.capitalize()} redenumit: '{old_name}'  '{new_name}'"
                    else:
                        return f"[FAIL] {item_type.capitalize()} '{old_name}' nu exista."
                else:
                    return "[FAIL] Format invalid. Foloseste: 'redenumeste folder X in Y'"
                    
            except Exception as e:
                return f"[FAIL] Eroare la redenumire: {e}"
"""

# ========================================
# EXEMPLU 5: Rulare comanda sistem
# ========================================
r"""
[WARN] ATENTIE: Aceasta e mai periculoasa - permite executie comenzi sistem!

Adauga in _send_ollama():

        # Detectare comanda rulare
        if re.search(r'(ruleaza|run|execute).*?comand[aa]', message, re.I):
            try:
                import subprocess
                
                # Extrage comanda
                cmd_match = re.search(r'comand[aa]\s+["\'](.+?)["\']', message, re.I)
                
                if cmd_match:
                    command = cmd_match.group(1)
                    
                    # SIGURANTA: Blocheaza comenzi periculoase
                    dangerous = ['rm -rf', 'del /f', 'format', 'rmdir /s']
                    if any(d in command.lower() for d in dangerous):
                        return "[FAIL] Comanda periculoasa blocata din motive de siguranta!"
                    
                    # Executa
                    result = subprocess.run(
                        command, 
                        shell=True, 
                        capture_output=True, 
                        text=True,
                        timeout=10
                    )
                    
                    output = result.stdout if result.stdout else result.stderr
                    return f" Comanda executata:\\n\\n{output}"
                else:
                    return "[FAIL] Nu am putut detecta comanda de executat."
                    
            except subprocess.TimeoutExpired:
                return "[FAIL] Comanda timeout (>10 secunde)"
            except Exception as e:
                return f"[FAIL] Eroare la executie: {e}"
"""

print("""

   EXEMPLE DE EXTINDERE TOOL CALLING


Acest fisier contine exemple de cod pentru extindere tool calling in Ana.

 CUM SA LE FOLOSESTI:

1. Deschide: core/agent.py
2. Gaseste functia _send_ollama() (linia ~857)
3. Copiaza exemplele de mai sus DUPA pattern-urile existente
4. Salveaza si testeaza!

 EXEMPLE DISPONIBILE:

  1. [FAIL] Stergere folder
     Comanda: "sterge folder TestAna"

  2.  Listare fisiere
     Comanda: "listeaza fisierele din Desktop"

  3.  Citire fisier
     Comanda: "citeste fisier test.txt"

  4.   Redenumire
     Comanda: "redenumeste folder Vechi in Nou"

  5.  Rulare comenzi ([WARN] ATENTIE - periculos!)
     Comanda: "ruleaza comanda 'dir'"

[WARN]  IMPORTANT:

- Testeaza fiecare comanda separat!
- Adauga comenzi periculoase cu verificari de siguranta
- Foloseste try/except pentru toate pattern-urile


""")
