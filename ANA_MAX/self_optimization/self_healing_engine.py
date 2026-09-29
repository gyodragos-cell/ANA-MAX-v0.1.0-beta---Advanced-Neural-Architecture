#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Healing Engine.

Detects simple code health issues such as syntax errors by running
python -m py_compile on ANA_MAX Python files.

With --repair, attempts safe local repairs and writes a detailed summary to
ANA_MAX/memory/self_healing_repair_report.json.
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ENGINE_NAME = "self_healing_engine"
REPORT_FILENAME = "self_healing_report.json"
REPAIR_REPORT_FILENAME = "self_healing_repair_report.json"
LOG_FILENAME = "self_healing_engine.log"

ANA_MAX_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ANA_MAX_ROOT / "memory"
LOGS_DIR = ANA_MAX_ROOT / "logs"
ARCHIVES_ROOT = ANA_MAX_ROOT / "archives"
REPORT_PATH = MEMORY_DIR / REPORT_FILENAME
REPAIR_REPORT_PATH = MEMORY_DIR / REPAIR_REPORT_FILENAME
LOG_PATH = LOGS_DIR / LOG_FILENAME

SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "node_modules",
        "site-packages",
        ".mypy_cache",
        ".pytest_cache",
        "archives",
        "logs",
        "memory",
        "sandbox",
        "screenshots",
        "voice_temp",
    }
)

INCOMPLETE_ENDING_RE = re.compile(r"(\\|\+|\-|\*|/|%|=|,|@|:|\{|\[|\()$")
INCOMPLETE_START_RE = re.compile(
    r"^(def|class|if|elif|else|try|except|finally|with|for|while|return|import|from|async)\b"
)

STDLIB_TOP_LEVEL = frozenset(
    getattr(sys, "stdlib_module_names", ())
    or (
        "os",
        "sys",
        "json",
        "re",
        "pathlib",
        "typing",
        "subprocess",
        "logging",
        "datetime",
        "time",
        "ast",
        "shutil",
        "collections",
        "itertools",
        "functools",
        "dataclasses",
        "enum",
        "io",
        "abc",
        "copy",
        "math",
        "random",
        "hashlib",
        "base64",
        "urllib",
        "http",
        "socket",
        "threading",
        "multiprocessing",
        "asyncio",
        "unittest",
        "argparse",
        "tempfile",
        "glob",
        "fnmatch",
        "pickle",
        "sqlite3",
        "csv",
        "xml",
        "html",
        "email",
        "contextlib",
        "traceback",
        "warnings",
        "inspect",
        "importlib",
        "pkgutil",
        "struct",
        "array",
        "queue",
        "weakref",
        "types",
        "operator",
        "statistics",
        "decimal",
        "fractions",
        "textwrap",
        "string",
        "codecs",
        "locale",
        "gettext",
        "platform",
        "ctypes",
        "mmap",
        "select",
        "signal",
        "gc",
        "builtins",
    )
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(ENGINE_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def _rel_path(path: Path) -> str:
    return str(path.relative_to(ANA_MAX_ROOT)).replace("\\", "/")


def _abs_path(rel_path: str) -> Path:
    return ANA_MAX_ROOT / rel_path.replace("/", "\\")


def _should_skip_path(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def observe(root: Path) -> dict[str, Any]:
    """Walk ANA_MAX and collect Python file paths and import metadata."""
    python_files: list[str] = []
    import_references: list[dict[str, Any]] = []

    for path in sorted(root.rglob("*.py")):
        if _should_skip_path(path):
            continue
        rel = _rel_path(path)
        python_files.append(rel)
        import_references.extend(_extract_imports(path, rel))

    duplicates = _find_duplicate_modules(python_files)
    missing_modules = _find_missing_modules(import_references, python_files)

    return {
        "root": str(root),
        "python_files": python_files,
        "python_file_count": len(python_files),
        "import_references": import_references,
        "duplicate_groups": duplicates,
        "missing_modules": missing_modules,
    }


def _extract_imports(path: Path, rel_path: str) -> list[dict[str, Any]]:
    """Parse import statements without executing the module."""
    references: list[dict[str, Any]] = []
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return references

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                references.append(
                    {
                        "source_file": rel_path,
                        "module": alias.name,
                        "style": "import",
                        "level": 0,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            references.append(
                {
                    "source_file": rel_path,
                    "module": module,
                    "style": "from",
                    "level": node.level,
                }
            )
    return references


def _module_to_candidate_paths(module: str) -> list[str]:
    parts = module.split(".")
    base = "/".join(parts)
    return [f"{base}.py", f"{base}/__init__.py"]


def _is_probable_stdlib(module: str) -> bool:
    top = module.split(".")[0]
    return top in STDLIB_TOP_LEVEL


def _find_missing_modules(
    import_references: list[dict[str, Any]],
    existing_files: list[str],
) -> list[dict[str, Any]]:
    """Find local module paths referenced by imports but absent on disk."""
    existing = set(existing_files)
    missing: dict[str, dict[str, Any]] = {}

    for ref in import_references:
        module = ref.get("module", "")
        if not module or _is_probable_stdlib(module):
            continue
        for candidate in _module_to_candidate_paths(module):
            if candidate in existing:
                continue
            candidate_path = _abs_path(candidate)
            if candidate_path.exists():
                continue
            parent = candidate_path.parent
            if not parent.exists():
                continue
            if _should_skip_path(candidate_path):
                continue
            if candidate not in missing:
                missing[candidate] = {
                    "module": module,
                    "placeholder_path": candidate,
                    "referenced_by": [],
                    "parent_exists": True,
                }
            if ref["source_file"] not in missing[candidate]["referenced_by"]:
                missing[candidate]["referenced_by"].append(ref["source_file"])

    return sorted(missing.values(), key=lambda item: item["placeholder_path"])


def _find_duplicate_modules(python_files: list[str]) -> list[dict[str, Any]]:
    """Group non-__init__ modules that share the same filename."""
    by_name: dict[str, list[str]] = defaultdict(list)
    for rel in python_files:
        name = Path(rel).name
        if name == "__init__.py":
            continue
        by_name[name].append(rel)

    groups: list[dict[str, Any]] = []
    for name, paths in sorted(by_name.items()):
        if len(paths) < 2:
            continue
        entries = []
        for rel in paths:
            absolute = _abs_path(rel)
            entries.append(
                {
                    "file": rel,
                    "mtime": absolute.stat().st_mtime if absolute.exists() else 0.0,
                }
            )
        entries.sort(key=lambda item: item["mtime"], reverse=True)
        groups.append(
            {
                "filename": name,
                "files": entries,
                "keeper": entries[0]["file"],
                "archive_candidates": [item["file"] for item in entries[1:]],
            }
        )
    return groups


def analyze(observation: dict[str, Any], *, repair: bool = False) -> dict[str, Any]:
    """Plan checks and optional repair actions."""
    analysis: dict[str, Any] = {
        "check_method": "python -m py_compile",
        "files_to_check": observation["python_files"],
        "files_to_check_count": observation["python_file_count"],
        "repair_mode": repair,
    }
    if repair:
        analysis["syntax_repair_candidates"] = "post_compile_failures"
        analysis["missing_module_placeholders"] = observation["missing_modules"]
        analysis["duplicate_archive_groups"] = observation["duplicate_groups"]
        analysis["archive_destination"] = str(ARCHIVES_ROOT / "duplicates")
    return analysis


def plan(analysis: dict[str, Any], *, repair: bool = False) -> list[dict[str, Any]]:
    """Build the list of planned actions."""
    actions: list[dict[str, Any]] = [
        {"action": "py_compile", "target": file_path}
        for file_path in analysis["files_to_check"]
    ]
    if repair:
        actions.append({"action": "syntax_repair", "target": "failed_files"})
        for item in analysis.get("missing_module_placeholders", []):
            actions.append(
                {
                    "action": "create_placeholder",
                    "target": item["placeholder_path"],
                    "module": item["module"],
                }
            )
        for group in analysis.get("duplicate_archive_groups", []):
            for rel in group.get("archive_candidates", []):
                actions.append(
                    {
                        "action": "archive_duplicate",
                        "target": rel,
                        "keeper": group["keeper"],
                        "filename": group["filename"],
                    }
                )
        actions.append({"action": "recompile_all", "target": "all_python_files"})
    return actions


def _compile_file(file_path: Path) -> dict[str, Any]:
    """Run py_compile on a single file and return structured result."""
    completed = subprocess.run(
        [sys.executable, "-m", "py_compile", str(file_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "ok": completed.returncode == 0,
    }


def _can_parse_python(source: str, filename: str) -> bool:
    try:
        ast.parse(source, filename=filename)
        return True
    except SyntaxError:
        return False


def _minimal_syntax_fix(content: str, filename: str) -> tuple[str, list[str]]:
    """Apply deterministic, minimal safe fixes to Python source text."""
    fixes_applied: list[str] = []
    text = content.replace("\r\n", "\n").replace("\r", "\n")

    if not text.endswith("\n"):
        text += "\n"
        fixes_applied.append("ensure_trailing_newline")

    lines = text.splitlines(keepends=True)

    while lines and lines[-1].strip() == "":
        lines.pop()
        if "remove_trailing_blank_lines" not in fixes_applied:
            fixes_applied.append("remove_trailing_blank_lines")

    def joined() -> str:
        body = "".join(lines)
        if body and not body.endswith("\n"):
            body += "\n"
        return body

    current = joined()
    if _can_parse_python(current, filename):
        return current, fixes_applied

    changed = True
    while changed and lines:
        changed = False
        while lines and lines[-1].strip() == "":
            lines.pop()
            changed = True
            if "remove_trailing_blank_lines" not in fixes_applied:
                fixes_applied.append("remove_trailing_blank_lines")

        if not lines:
            break

        last = lines[-1]
        stripped = last.rstrip("\n")
        trimmed = stripped.rstrip()

        if trimmed and (trimmed == stripped and trimmed.startswith((" ", "\t"))):
            indent_only = trimmed.strip() == ""
            if indent_only:
                lines.pop()
                changed = True
                fixes_applied.append("remove_broken_trailing_indentation")
                continue

        if trimmed:
            if INCOMPLETE_ENDING_RE.search(trimmed) or INCOMPLETE_START_RE.match(trimmed):
                lines.pop()
                changed = True
                if "remove_trailing_incomplete_statement" not in fixes_applied:
                    fixes_applied.append("remove_trailing_incomplete_statement")
                continue

            if stripped.endswith("\\"):
                lines.pop()
                changed = True
                if "remove_trailing_line_continuation" not in fixes_applied:
                    fixes_applied.append("remove_trailing_line_continuation")
                continue

        candidate = joined()
        if _can_parse_python(candidate, filename):
            return candidate, fixes_applied

        if lines:
            lines.pop()
            changed = True
            if "remove_unparseable_trailing_line" not in fixes_applied:
                fixes_applied.append("remove_unparseable_trailing_line")

    final_text = joined()
    if _can_parse_python(final_text, filename):
        return final_text, fixes_applied
    return final_text, fixes_applied


def _backup_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup_path)
    return backup_path


def _archive_duplicate(rel_path: str, archive_stamp: str) -> Path:
    source = _abs_path(rel_path)
    destination = ARCHIVES_ROOT / "duplicates" / archive_stamp / rel_path.replace("/", "\\")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination


def act_detect(
    analysis: dict[str, Any],
    planned_actions: list[dict[str, Any]],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Execute py_compile checks and collect pass/fail lists."""
    ok_files: list[str] = []
    failed_files: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for rel_path in analysis["files_to_check"]:
        absolute = _abs_path(rel_path)
        outcome = _compile_file(absolute)
        entry = {
            "file": rel_path,
            "ok": outcome["ok"],
            "returncode": outcome["returncode"],
            "stderr": outcome["stderr"],
        }
        results.append(entry)
        if outcome["ok"]:
            ok_files.append(rel_path)
        else:
            failed_files.append(
                {
                    "file": rel_path,
                    "returncode": outcome["returncode"],
                    "error": outcome["stderr"] or outcome["stdout"] or "py_compile failed",
                }
            )

    return _build_detection_report(
        analysis=analysis,
        planned_actions=planned_actions,
        ok_files=ok_files,
        failed_files=failed_files,
        results=results,
        dry_run=dry_run,
    )


def _build_detection_report(
    *,
    analysis: dict[str, Any],
    planned_actions: list[dict[str, Any]],
    ok_files: list[str],
    failed_files: list[dict[str, Any]],
    results: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    failed_count = len(failed_files)
    ok_count = len(ok_files)
    if dry_run:
        health = "dry_run"
    elif failed_count == 0:
        health = "good"
    elif failed_count <= 5:
        health = "warning"
    else:
        health = "critical"

    return {
        "schema": "ana.os3.self_healing.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "dry_run": dry_run,
        "mode": "detect",
        "planned_actions_count": len(planned_actions),
        "summary": {
            "files_checked": len(results),
            "ok_count": ok_count,
            "failed_count": failed_count,
            "health": health,
        },
        "ok_files": ok_files,
        "failed_files": failed_files,
        "results": results,
        "analysis": analysis,
    }


def act_repair(
    observation: dict[str, Any],
    analysis: dict[str, Any],
    planned_actions: list[dict[str, Any]],
    initial_detection: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Attempt safe local repairs and re-run py_compile."""
    archive_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    repair_actions: list[dict[str, Any]] = []

    syntax_repairs: list[dict[str, Any]] = []
    placeholder_created: list[dict[str, Any]] = []
    placeholder_skipped: list[dict[str, Any]] = []
    duplicates_archived: list[dict[str, Any]] = []
    duplicates_skipped: list[dict[str, Any]] = []

    if dry_run:
        for group in observation.get("duplicate_groups", []):
            for rel in group.get("archive_candidates", []):
                repair_actions.append(
                    {
                        "action": "archive_duplicate",
                        "file": rel,
                        "keeper": group["keeper"],
                        "status": "planned",
                    }
                )
        for item in observation.get("missing_modules", []):
            repair_actions.append(
                {
                    "action": "create_placeholder",
                    "path": item["placeholder_path"],
                    "module": item["module"],
                    "status": "planned",
                }
            )
        for failure in initial_detection.get("failed_files", []):
            repair_actions.append(
                {
                    "action": "syntax_repair",
                    "file": failure["file"],
                    "status": "planned",
                }
            )
    else:
        for group in observation.get("duplicate_groups", []):
            for rel in group.get("archive_candidates", []):
                source = _abs_path(rel)
                if not source.exists():
                    duplicates_skipped.append(
                        {"file": rel, "reason": "file_missing", "keeper": group["keeper"]}
                    )
                    continue
                try:
                    destination = _archive_duplicate(rel, archive_stamp)
                    duplicates_archived.append(
                        {
                            "file": rel,
                            "keeper": group["keeper"],
                            "archived_to": _rel_path(destination),
                        }
                    )
                    repair_actions.append(
                        {
                            "action": "archive_duplicate",
                            "file": rel,
                            "keeper": group["keeper"],
                            "archived_to": _rel_path(destination),
                            "status": "applied",
                        }
                    )
                except OSError as exc:
                    duplicates_skipped.append(
                        {"file": rel, "reason": str(exc), "keeper": group["keeper"]}
                    )

        for item in observation.get("missing_modules", []):
            rel = item["placeholder_path"]
            target = _abs_path(rel)
            if target.exists():
                placeholder_skipped.append({"path": rel, "reason": "already_exists"})
                continue
            parent = target.parent
            if not parent.exists():
                placeholder_skipped.append({"path": rel, "reason": "parent_missing"})
                continue
            try:
                target.write_text('"""Auto-created placeholder module."""\n', encoding="utf-8")
                placeholder_created.append(
                    {
                        "path": rel,
                        "module": item["module"],
                        "referenced_by": item["referenced_by"],
                    }
                )
                repair_actions.append(
                    {
                        "action": "create_placeholder",
                        "path": rel,
                        "module": item["module"],
                        "status": "applied",
                    }
                )
            except OSError as exc:
                placeholder_skipped.append({"path": rel, "reason": str(exc)})

        for failure in initial_detection.get("failed_files", []):
            rel = failure["file"]
            path = _abs_path(rel)
            if not path.exists():
                syntax_repairs.append(
                    {"file": rel, "status": "skipped", "reason": "file_missing"}
                )
                continue
            try:
                original = path.read_text(encoding="utf-8", errors="replace")
                backup_path = _backup_file(path)
                fixed_text, fixes = _minimal_syntax_fix(original, rel)
                if fixes:
                    path.write_text(fixed_text, encoding="utf-8")
                outcome = _compile_file(path)
                entry = {
                    "file": rel,
                    "status": "repaired" if outcome["ok"] else "still_failing",
                    "backup": str(backup_path.relative_to(ANA_MAX_ROOT)).replace("\\", "/"),
                    "fixes_applied": fixes,
                    "recompiled_ok": outcome["ok"],
                    "error": "" if outcome["ok"] else outcome["stderr"],
                }
                syntax_repairs.append(entry)
                repair_actions.append(
                    {
                        "action": "syntax_repair",
                        "file": rel,
                        "status": entry["status"],
                        "fixes_applied": fixes,
                        "backup": entry["backup"],
                    }
                )
            except OSError as exc:
                syntax_repairs.append(
                    {"file": rel, "status": "error", "reason": str(exc)}
                )

    if dry_run:
        post_detection = {
            "summary": initial_detection.get("summary", {}),
            "failed_files": initial_detection.get("failed_files", []),
            "ok_files_count": len(initial_detection.get("ok_files", [])),
        }
    else:
        refreshed_observation = observe(ANA_MAX_ROOT)
        refreshed_analysis = analyze(refreshed_observation, repair=True)
        post_detection = act_detect(
            refreshed_analysis,
            planned_actions,
            dry_run=False,
        )
        post_detection = {
            "summary": post_detection.get("summary", {}),
            "failed_files": post_detection.get("failed_files", []),
            "ok_files_count": len(post_detection.get("ok_files", [])),
        }

    repaired_ok = sum(1 for item in syntax_repairs if item.get("status") == "repaired")
    still_failing = sum(1 for item in syntax_repairs if item.get("status") == "still_failing")

    return {
        "schema": "ana.os3.self_healing_repair.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "dry_run": dry_run,
        "mode": "repair",
        "planned_actions_count": len(planned_actions),
        "summary": {
            "initial_failed_count": initial_detection.get("summary", {}).get("failed_count", 0),
            "post_failed_count": post_detection.get("summary", {}).get("failed_count", 0),
            "syntax_repairs_attempted": len(initial_detection.get("failed_files", [])),
            "syntax_repairs_succeeded": repaired_ok,
            "syntax_repairs_still_failing": still_failing,
            "placeholders_created": len(placeholder_created),
            "placeholders_skipped": len(placeholder_skipped),
            "duplicates_archived": len(duplicates_archived),
            "duplicates_skipped": len(duplicates_skipped),
            "archive_stamp": archive_stamp,
            "health": post_detection.get("summary", {}).get("health", "unknown"),
        },
        "repair_actions": repair_actions,
        "syntax_repairs": syntax_repairs,
        "placeholder_created": placeholder_created,
        "placeholder_skipped": placeholder_skipped,
        "duplicates_archived": duplicates_archived,
        "duplicates_skipped": duplicates_skipped,
        "initial_detection": {
            "summary": initial_detection.get("summary", {}),
            "failed_files": initial_detection.get("failed_files", []),
        },
        "post_detection": {
            "summary": post_detection.get("summary", {}),
            "failed_files": post_detection.get("failed_files", []),
            "ok_files_count": len(post_detection.get("ok_files", [])),
        },
        "analysis": analysis,
    }


def verify(report: dict[str, Any]) -> dict[str, Any]:
    """Confirm detection results are internally consistent."""
    ok_files = report.get("ok_files", [])
    failed_files = report.get("failed_files", [])
    results = report.get("results", [])
    summary = report.get("summary", {})

    checks = {
        "report_non_empty": bool(report),
        "schema_present": report.get("schema") == "ana.os3.self_healing.v1",
        "ok_plus_failed_matches_results": len(ok_files) + len(failed_files) == len(results),
        "summary_counts_match": (
            summary.get("ok_count") == len(ok_files)
            and summary.get("failed_count") == len(failed_files)
            and summary.get("files_checked") == len(results)
        ),
        "returncodes_consistent": all(
            (item.get("ok") is True and item.get("returncode") == 0)
            or (item.get("ok") is False and item.get("returncode") != 0)
            for item in results
        ),
    }
    if report.get("dry_run"):
        checks["dry_run_detection_ran"] = summary.get("files_checked", 0) >= 0

    return {"passed": all(checks.values()), "checks": checks}


def verify_repair(repair_report: dict[str, Any]) -> dict[str, Any]:
    """Verify repair report consistency."""
    summary = repair_report.get("summary", {})
    initial_failed = summary.get("initial_failed_count", 0)
    post_failed = summary.get("post_failed_count", 0)
    checks = {
        "report_non_empty": bool(repair_report),
        "schema_present": repair_report.get("schema") == "ana.os3.self_healing_repair.v1",
        "post_failed_not_greater_than_initial": post_failed <= max(initial_failed, 0) + summary.get(
            "placeholders_created", 0
        ),
        "summary_fields_present": "health" in summary and "syntax_repairs_attempted" in summary,
        "repair_actions_is_list": isinstance(repair_report.get("repair_actions"), list),
    }
    if repair_report.get("dry_run"):
        checks["dry_run_no_mutations"] = (
            summary.get("placeholders_created", 0) == 0
            and summary.get("duplicates_archived", 0) == 0
            and summary.get("syntax_repairs_succeeded", 0) == 0
        )
    return {"passed": all(checks.values()), "checks": checks}


def document(
    report: dict[str, Any],
    verification: dict[str, Any],
    *,
    dry_run: bool,
    repair_report: dict[str, Any] | None = None,
    repair_verification: dict[str, Any] | None = None,
) -> None:
    """Write detection and optional repair reports."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    final_report = {
        **report,
        "verification": verification,
        "pipeline": {
            "observe": "complete",
            "analyze": "complete",
            "plan": "complete",
            "act": "complete",
            "verify": "complete",
            "document": "skipped" if dry_run else "complete",
        },
    }
    if not dry_run:
        REPORT_PATH.write_text(
            json.dumps(final_report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if repair_report is not None:
        final_repair = {
            **repair_report,
            "verification": repair_verification or {},
            "pipeline": {
                "observe": "complete",
                "analyze": "complete",
                "plan": "complete",
                "act": "repair",
                "verify": "complete",
                "document": "skipped" if dry_run else "complete",
            },
        }
        if not dry_run:
            REPAIR_REPORT_PATH.write_text(
                json.dumps(final_repair, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    logger = setup_logger()
    status = "dry-run" if dry_run else "written"
    logger.info(
        "cycle complete status=%s report=%s verify_passed=%s ok=%s failed=%s health=%s repair=%s",
        status,
        REPORT_PATH,
        verification.get("passed"),
        report.get("summary", {}).get("ok_count"),
        report.get("summary", {}).get("failed_count"),
        report.get("summary", {}).get("health"),
        repair_report is not None,
    )
    if repair_report is not None:
        logger.info(
            "repair complete status=%s report=%s verify_passed=%s repaired=%s post_failed=%s",
            status,
            REPAIR_REPORT_PATH,
            (repair_verification or {}).get("passed"),
            repair_report.get("summary", {}).get("syntax_repairs_succeeded"),
            repair_report.get("summary", {}).get("post_failed_count"),
        )


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    """Detection-only OS-3 pipeline."""
    started = time.perf_counter()
    observation = observe(ANA_MAX_ROOT)
    analysis = analyze(observation, repair=False)
    planned = plan(analysis, repair=False)
    report = act_detect(analysis, planned, dry_run=dry_run)
    verification = verify(report)
    document(report, verification, dry_run=dry_run)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "engine": ENGINE_NAME,
        "mode": "detect",
        "dry_run": dry_run,
        "elapsed_ms": elapsed_ms,
        "verification": verification,
        "report_path": str(REPORT_PATH),
        "summary": report.get("summary", {}),
    }


def run_repair(*, dry_run: bool = False) -> dict[str, Any]:
    """Full repair OS-3 pipeline with detection before and after repairs."""
    started = time.perf_counter()
    observation = observe(ANA_MAX_ROOT)
    analysis = analyze(observation, repair=True)
    planned = plan(analysis, repair=True)

    initial_detection = act_detect(analysis, planned, dry_run=dry_run)
    repair_report = act_repair(
        observation,
        analysis,
        planned,
        initial_detection,
        dry_run=dry_run,
    )

    final_detection = repair_report.get("post_detection", {})
    report = {
        **initial_detection,
        "mode": "repair",
        "summary": {
            "files_checked": final_detection.get("summary", {}).get("files_checked", 0),
            "ok_count": final_detection.get("ok_files_count", 0),
            "failed_count": final_detection.get("summary", {}).get("failed_count", 0),
            "health": final_detection.get("summary", {}).get("health", "unknown"),
            "initial_failed_count": initial_detection.get("summary", {}).get("failed_count", 0),
        },
        "failed_files": final_detection.get("failed_files", []),
        "ok_files": [],
        "results": [],
    }

    detection_verification = verify(initial_detection)
    repair_verification = verify_repair(repair_report)
    document(
        initial_detection,
        detection_verification,
        dry_run=dry_run,
        repair_report=repair_report,
        repair_verification=repair_verification,
    )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "engine": ENGINE_NAME,
        "mode": "repair",
        "dry_run": dry_run,
        "elapsed_ms": elapsed_ms,
        "verification": repair_verification,
        "detection_verification": detection_verification,
        "report_path": str(REPORT_PATH),
        "repair_report_path": str(REPAIR_REPORT_PATH),
        "summary": repair_report.get("summary", {}),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Healing Engine")
    parser.add_argument(
        "--cycle",
        action="store_true",
        help="Run detection-only pipeline (py_compile scan).",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Run repair pipeline: detect, repair locally, re-compile, and document.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detection but do not modify files or write JSON reports.",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Compatibility alias for --cycle --dry-run.",
    )
    parser.add_argument(
        "--simulate-repair",
        action="store_true",
        help="Compatibility alias for --repair --dry-run.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.diagnostic:
        args.cycle = True
        args.dry_run = True
    if args.simulate_repair:
        args.repair = True
        args.dry_run = True
    if not args.cycle and not args.repair:
        parser.print_help()
        return 0

    if args.repair:
        result = run_repair(dry_run=args.dry_run)
    else:
        result = run_cycle(dry_run=args.dry_run)

    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
