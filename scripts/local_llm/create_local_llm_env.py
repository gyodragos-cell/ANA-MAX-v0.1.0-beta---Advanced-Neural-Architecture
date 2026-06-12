"""Create or inspect the optional Python 3.11 local LLM environment.

Default mode is dry-run. Use --apply to create local_llm_env.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DEFAULT_ENV_DIR = ROOT / "local_llm_env"


def _run(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }


def _python_version(command: list[str]) -> dict[str, Any]:
    result = _run(command + ["-c", "import sys,json; print(json.dumps({'version': sys.version.split()[0], 'executable': sys.executable}))"])
    version = ""
    executable = ""
    if result["returncode"] == 0 and result["stdout"]:
        try:
            data = json.loads(result["stdout"])
            version = str(data.get("version", ""))
            executable = str(data.get("executable", ""))
        except json.JSONDecodeError:
            pass
    return {
        "command": command,
        "available": result["returncode"] == 0,
        "version": version,
        "executable": executable,
        "raw": result,
    }


def _candidate_commands(explicit_python: str = "") -> list[list[str]]:
    candidates: list[list[str]] = []
    if explicit_python:
        candidates.append([explicit_python])
    for name in ("python311", "python3.11"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append([py_launcher, "-3.11"])
        inventory = _run([py_launcher, "-0p"], timeout=10)
        if inventory["returncode"] == 0:
            for line in inventory["stdout"].splitlines():
                if "3.11" not in line:
                    continue
                match = re.search(r"([A-Za-z]:\\.*python(?:3\.11)?\.exe)\s*$", line.strip(), re.IGNORECASE)
                if match:
                    candidates.append([match.group(1)])
    uv_exe = shutil.which("uv")
    if uv_exe:
        uv_find = _run([uv_exe, "python", "find", "3.11"], timeout=10)
        if uv_find["returncode"] == 0 and uv_find["stdout"].strip():
            candidates.append([uv_find["stdout"].splitlines()[0].strip()])

    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for command in candidates:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        unique.append(command)
    return unique


def detect_python311(explicit_python: str = "") -> dict[str, Any]:
    for command in _candidate_commands(explicit_python):
        info = _python_version(command)
        if info["available"] and str(info["version"]).startswith("3.11."):
            return info
    return {
        "command": [],
        "available": False,
        "version": "",
        "executable": "",
        "raw": {"returncode": 1, "stdout": "", "stderr": "python_3_11_not_found"},
    }


def env_status(env_dir: Path) -> dict[str, Any]:
    scripts_dir = env_dir / "Scripts"
    python_exe = scripts_dir / "python.exe"
    pip_exe = scripts_dir / "pip.exe"
    return {
        "env_dir": str(env_dir),
        "exists": env_dir.exists(),
        "python_exists": python_exe.exists(),
        "pip_exists": pip_exe.exists(),
        "activate_ps1": str(scripts_dir / "Activate.ps1"),
        "activate_bat": str(scripts_dir / "activate.bat"),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env_dir = Path(args.env_dir).resolve() if args.env_dir else DEFAULT_ENV_DIR
    python311 = detect_python311(args.python311)
    status = env_status(env_dir)
    command = list(python311["command"]) + ["-m", "venv", str(env_dir)] if python311["available"] else []
    report: dict[str, Any] = {
        "schema": "ana.local_llm.env_setup.v1",
        "root": str(ROOT),
        "apply": bool(args.apply),
        "main_python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "python311": {
            "available": python311["available"],
            "version": python311["version"],
            "executable": python311["executable"],
            "command": python311["command"],
        },
        "environment": status,
        "planned_command": command,
        "created": False,
        "success": False,
        "error": "",
    }

    if not args.apply:
        report["success"] = True
        report["error"] = "dry_run_no_changes"
        return report
    if not python311["available"]:
        report["error"] = "python_3_11_not_found"
        return report
    if status["python_exists"]:
        report["success"] = True
        report["error"] = "env_already_exists"
        return report

    env_dir.parent.mkdir(parents=True, exist_ok=True)
    result = _run(command, timeout=max(60, int(args.timeout)))
    report["create_result"] = result
    report["created"] = result["returncode"] == 0
    report["environment"] = env_status(env_dir)
    report["success"] = bool(report["environment"]["python_exists"])
    if not report["success"]:
        report["error"] = result.get("stderr") or "venv_create_failed"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create optional Python 3.11 local LLM env.")
    parser.add_argument("--apply", action="store_true", help="Create local_llm_env")
    parser.add_argument("--python311", default="", help="Optional python 3.11 executable path")
    parser.add_argument("--env-dir", default="", help="Optional environment directory")
    parser.add_argument("--timeout", type=int, default=180, help="Venv creation timeout seconds")
    args = parser.parse_args(argv)
    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
