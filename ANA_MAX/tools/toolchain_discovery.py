#!/usr/bin/env python3
"""ANA MAX OS-4 Dynamic Toolchain Discovery.

Discovers active and archived tool modules without importing or registering
them. Validation is static/syntax-only and dangerous tools are report-only.
"""

from __future__ import annotations

import argparse
import ast
import json
import py_compile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANA_MAX_ROOT = PROJECT_ROOT / "ANA_MAX"
TOOLS_DIR = ANA_MAX_ROOT / "tools"
ARCHIVES_DIR = ANA_MAX_ROOT / "archives"
MEMORY_DIR = ANA_MAX_ROOT / "memory"
DOCS_DIR = PROJECT_ROOT / "docs"
MANIFEST_PATH = MEMORY_DIR / "toolchain_manifest.json"

DANGEROUS_MARKERS = frozenset(
    {
        "adb",
        "apk",
        "desktop_control",
        "frida",
        "mitm",
        "network_pentest",
        "remote_control",
        "terminal",
        "uia_click",
        "uia_type",
        "windows_deep_sight",
    }
)

SKIP_DIRS = frozenset({"__pycache__", "venv", ".venv", "node_modules", ".pytest_cache"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _is_dangerous(name: str, path: Path) -> bool:
    text = f"{name} {_rel(path)}".lower()
    return any(marker in text for marker in DANGEROUS_MARKERS)


def _class_names(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    except SyntaxError:
        return []
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _syntax_ok(path: Path) -> tuple[bool, str]:
    try:
        py_compile.compile(str(path), doraise=True)
        return True, ""
    except py_compile.PyCompileError as exc:
        return False, str(exc)
    except OSError as exc:
        return False, str(exc)


def _iter_python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def discover_tools() -> dict[str, Any]:
    active: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    for path in _iter_python_files(TOOLS_DIR):
        if path.name == "__init__.py":
            continue
        ok, error = _syntax_ok(path)
        dangerous = _is_dangerous(path.stem, path)
        active.append(
            {
                "name": path.stem,
                "path": _rel(path),
                "status": "active",
                "classes": _class_names(path),
                "syntax_ok": ok,
                "syntax_error": error,
                "dangerous": dangerous,
                "requires_explicit_enable": dangerous,
            }
        )

    for path in _iter_python_files(ARCHIVES_DIR):
        if "duplicates" not in path.parts:
            continue
        ok, error = _syntax_ok(path)
        dangerous = _is_dangerous(path.stem, path)
        candidates.append(
            {
                "name": path.stem,
                "path": _rel(path),
                "status": "candidate",
                "classes": _class_names(path),
                "syntax_ok": ok,
                "syntax_error": error,
                "dangerous": dangerous,
                "requires_explicit_enable": True,
            }
        )

    return {
        "active": active,
        "candidates": candidates,
        "counts": {
            "active": len(active),
            "candidate": len(candidates),
            "dangerous_active": sum(1 for item in active if item["dangerous"]),
            "dangerous_candidate": sum(1 for item in candidates if item["dangerous"]),
            "syntax_failed_active": sum(1 for item in active if not item["syntax_ok"]),
            "syntax_failed_candidate": sum(1 for item in candidates if not item["syntax_ok"]),
        },
    }


def verify(manifest: dict[str, Any]) -> dict[str, Any]:
    counts = manifest.get("counts", {})
    active = manifest.get("tools", {}).get("active", [])
    checks = {
        "schema_present": manifest.get("schema") == "ana.os4.toolchain_manifest.v1",
        "active_tools_present": isinstance(active, list) and len(active) > 0,
        "dangerous_require_explicit_enable": all(
            not item.get("dangerous") or item.get("requires_explicit_enable")
            for item in active
        ),
        "counts_present": all(key in counts for key in ["active", "candidate"]),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    discovered = discover_tools()
    manifest = {
        "schema": "ana.os4.toolchain_manifest.v1",
        "generated_at": _utc_now(),
        "dry_run": dry_run,
        "project_root": str(PROJECT_ROOT),
        "tools_dir": str(TOOLS_DIR),
        "archives_dir": str(ARCHIVES_DIR),
        "tools": {
            "active": discovered["active"],
            "candidates": discovered["candidates"],
        },
        "counts": discovered["counts"],
        "policy": {
            "auto_enable": False,
            "dangerous_tools": "report_only_requires_explicit_enable",
            "validation": "syntax_only_no_import_no_registration",
        },
    }
    manifest["verification"] = verify(manifest)
    manifest["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)

    if not dry_run:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "engine": "toolchain_discovery",
        "dry_run": dry_run,
        "elapsed_ms": manifest["elapsed_ms"],
        "verification": manifest["verification"],
        "manifest_path": str(MANIFEST_PATH),
        "summary": manifest["counts"],
        "policy": manifest["policy"],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-4 Toolchain Discovery")
    parser.add_argument("--dry-run", action="store_true", help="Scan without writing manifest.")
    parser.add_argument("--cycle", action="store_true", help="Run safe discovery and write manifest.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
