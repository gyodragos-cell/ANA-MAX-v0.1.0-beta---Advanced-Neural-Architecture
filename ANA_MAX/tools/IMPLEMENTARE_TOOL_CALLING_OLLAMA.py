#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implementare Tool Calling pentru Ollama in Ana v16 (Legacy utility)
"""

import sys
import os
import re
from pathlib import Path


def main():
    print("=" * 80)
    print("   IMPLEMENTARE TOOL CALLING PENTRU OLLAMA")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent
    agent_file = project_root / "core" / "agent.py"
    backup_file = project_root / "core" / "agent.py.backup_before_tool_calling"

    if not agent_file.exists():
        print("[FAIL] EROARE: core/agent.py nu exista!")
        return

    if backup_file.exists():
        print(f"[OK] Backup existent gasit: {backup_file.name}")
    else:
        import shutil
        shutil.copy(agent_file, backup_file)
        print(f"[OK] Backup creat: {backup_file.name}")

    print("[1/4] Citire fisier agent.py...")
    content = agent_file.read_text(encoding='utf-8')

    if "# OLLAMA_TOOL_CALLING_IMPLEMENTED" in content:
        print("[WARN] Tool calling deja implementat!")
        return

    print("[OK] Fisier citit!")


if __name__ == "__main__":
    main()
