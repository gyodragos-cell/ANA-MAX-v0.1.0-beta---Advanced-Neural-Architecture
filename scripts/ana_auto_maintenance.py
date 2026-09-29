"""
ANA OS-27 Auto-Maintenance Daemon
==================================
Ruleaza automat la startup sau periodic:
  1. Curata diacritice din toate fisierele .py/.md/.json
  2. Muta scripturi ratacite (test_*.py, analyze_*.py) din root in sandbox
  3. Curata fisiere .bak/.old/.tmp
  4. Verifica integritatea structurii enterprise
  5. Raporteaza ACTION -> RESULT -> NEXT STEP
"""

import os
import sys
import shutil
import time
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # ana-manus/
ANA_MAX = PROJECT_ROOT / "ANA_MAX"
SANDBOX_SCRIPTS = ANA_MAX / "sandbox" / "scripts"
SANDBOX_TESTS = ANA_MAX / "sandbox" / "tests"
SANDBOX_MCP = ANA_MAX / "sandbox" / "mcp_backup_devin"

# Folders to never touch
SKIP_DIRS = {"venv", ".git", "__pycache__", "node_modules", ".ana_backups", "archives"}

DIACRITICS_MAP = {
    '\u0103': 'a', '\u00e2': 'a', '\u00ee': 'i', '\u0219': 's', '\u021b': 't',
    '\u0102': 'A', '\u00c2': 'A', '\u00ce': 'I', '\u0218': 'S', '\u021a': 'T',
    # cedilla variants
    '\u015f': 's', '\u0163': 't', '\u015e': 'S', '\u0162': 'T',
}

LOG_FILE = ANA_MAX / "logs" / "auto_maintenance.log"


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def clean_diacritics() -> int:
    """Replace Romanian diacritics in .py, .md, .json files. Returns count of files changed."""
    count = 0
    for root, dirs, files in os.walk(str(PROJECT_ROOT)):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if not fname.endswith(('.py', '.md', '.json')):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = content
                for old, new in DIACRITICS_MAP.items():
                    new_content = new_content.replace(old, new)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count += 1
            except Exception:
                pass
    return count


def organize_root_scripts() -> int:
    """Move stray test/analyze/check scripts from root to sandbox."""
    SANDBOX_SCRIPTS.mkdir(parents=True, exist_ok=True)
    SANDBOX_TESTS.mkdir(parents=True, exist_ok=True)
    count = 0
    for fpath in PROJECT_ROOT.glob("*.py"):
        fname = fpath.name
        # Keep essential root files
        if fname in ("large_file_reader.py", "conftest.py", "requirements.txt"):
            continue
        dest = None
        if fname.startswith("test_"):
            dest = SANDBOX_TESTS / fname
        elif fname.startswith(("analyze_", "check_", "smoke_test_", "create_", "run_", "generate_")):
            dest = SANDBOX_SCRIPTS / fname
        if dest and not dest.exists():
            try:
                shutil.move(str(fpath), str(dest))
                count += 1
            except Exception:
                pass
    return count


def organize_root_mcp() -> int:
    """Move stray mcp_* files from root to sandbox backup."""
    SANDBOX_MCP.mkdir(parents=True, exist_ok=True)
    count = 0
    for pattern in ("mcp_*.py", "mcp_*.json"):
        for fpath in PROJECT_ROOT.glob(pattern):
            dest = SANDBOX_MCP / fpath.name
            if not dest.exists():
                try:
                    shutil.move(str(fpath), str(dest))
                    count += 1
                except Exception:
                    pass
    return count


def clean_junk_files() -> int:
    """Remove .bak, .old, .tmp files (except in venv/archives)."""
    count = 0
    for root, dirs, files in os.walk(str(PROJECT_ROOT)):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(('.bak', '.old', '.tmp')):
                fpath = os.path.join(root, fname)
                try:
                    os.remove(fpath)
                    count += 1
                except Exception:
                    pass
    return count


def verify_structure() -> dict:
    """Quick enterprise structure integrity check."""
    checks = {}
    checks["AGENTS.md"] = (PROJECT_ROOT / "AGENTS.md").exists()
    checks["docs/ROADMAP.md"] = (PROJECT_ROOT / "docs" / "ROADMAP.md").exists()
    checks["docs/ANA_MEMORY.md"] = (PROJECT_ROOT / "docs" / "ANA_MEMORY.md").exists()
    checks["ANA_MAX/tools/__init__.py"] = (ANA_MAX / "tools" / "__init__.py").exists()
    checks["ANA_MAX/core/agent.py"] = (ANA_MAX / "core" / "agent.py").exists()
    checks["ANA_MAX/sandbox/"] = (ANA_MAX / "sandbox").is_dir()
    return checks


def run_all(dry_run=False):
    _log("=== ANA OS-27 Auto-Maintenance START ===")
    start = time.time()

    # 1. Diacritics
    if dry_run:
        _log("[DRY-RUN] Would clean diacritics")
        diac_count = 0
    else:
        diac_count = clean_diacritics()
    _log(f"ACTION: clean_diacritics -> RESULT: {diac_count} files cleaned")

    # 2. Organize root
    if dry_run:
        _log("[DRY-RUN] Would organize root scripts")
        scripts_moved = 0
    else:
        scripts_moved = organize_root_scripts()
    _log(f"ACTION: organize_root_scripts -> RESULT: {scripts_moved} scripts moved to sandbox")

    # 3. MCP isolation
    if dry_run:
        _log("[DRY-RUN] Would isolate MCP files")
        mcp_moved = 0
    else:
        mcp_moved = organize_root_mcp()
    _log(f"ACTION: organize_root_mcp -> RESULT: {mcp_moved} MCP files isolated")

    # 4. Junk cleanup
    if dry_run:
        _log("[DRY-RUN] Would clean junk files")
        junk_removed = 0
    else:
        junk_removed = clean_junk_files()
    _log(f"ACTION: clean_junk_files -> RESULT: {junk_removed} junk files removed")

    # 5. Structure verification
    structure = verify_structure()
    all_ok = all(structure.values())
    failed = [k for k, v in structure.items() if not v]
    _log(f"ACTION: verify_structure -> RESULT: {'PASS' if all_ok else 'FAIL: ' + str(failed)}")

    elapsed = round(time.time() - start, 2)
    _log(f"=== Auto-Maintenance DONE in {elapsed}s ===")
    _log(f"NEXT STEP: {'System clean, ready for work.' if all_ok else 'Fix missing: ' + str(failed)}")

    return {
        "diacritics_cleaned": diac_count,
        "scripts_moved": scripts_moved,
        "mcp_isolated": mcp_moved,
        "junk_removed": junk_removed,
        "structure_ok": all_ok,
        "elapsed_sec": elapsed,
    }


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = run_all(dry_run=dry)
    print(json.dumps(result, indent=2))
