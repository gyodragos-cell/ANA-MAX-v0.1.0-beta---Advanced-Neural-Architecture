"""Install or inspect the optional OLLM backend inside local_llm_env.

Default mode is dry-run. Use --apply to call pip.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DEFAULT_ENV_DIR = ROOT / "local_llm_env"
DEFAULT_REQUIREMENTS = ROOT / "requirements_local_llm.txt"
OLLM_PACKAGE = "ollm"
LLAMA_CPP_WHEEL_INDEX = "https://abetlen.github.io/llama-cpp-python/whl/cpu"


def _env_python(env_dir: Path) -> Path:
    return env_dir / "Scripts" / "python.exe"


def _run(command: list[str], timeout: int = 300) -> dict[str, Any]:
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


def _module_available(python_exe: Path, module_name: str) -> bool:
    if not python_exe.exists():
        return False
    result = _run(
        [
            str(python_exe),
            "-c",
            f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec('{module_name}') else 1)",
        ],
        timeout=30,
    )
    return result["returncode"] == 0


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env_dir = Path(args.env_dir).resolve() if args.env_dir else DEFAULT_ENV_DIR
    requirements = Path(args.requirements).resolve() if args.requirements else DEFAULT_REQUIREMENTS
    python_exe = _env_python(env_dir)
    install_ollm_command = [str(python_exe), "-m", "pip", "install", "--no-deps", OLLM_PACKAGE]
    install_deps_command = [
        str(python_exe),
        "-m",
        "pip",
        "install",
        "--prefer-binary",
        "--extra-index-url",
        LLAMA_CPP_WHEEL_INDEX,
        "--timeout",
        str(max(60, int(args.pip_timeout))),
        "--retries",
        str(max(1, int(args.retries))),
        "-r",
        str(requirements),
    ]
    report: dict[str, Any] = {
        "schema": "ana.local_llm.ollm_install.v1",
        "root": str(ROOT),
        "apply": bool(args.apply),
        "strategy": "windows_cpu_safe_no_flash",
        "env_dir": str(env_dir),
        "python_exists": python_exe.exists(),
        "requirements": str(requirements),
        "requirements_exists": requirements.exists(),
        "ollm_available_before": _module_available(python_exe, "ollm"),
        "llama_cpp_available_before": _module_available(python_exe, "llama_cpp"),
        "planned_commands": [install_ollm_command, install_deps_command],
        "success": False,
        "error": "",
    }

    if not args.apply:
        report["success"] = True
        report["error"] = "dry_run_no_changes"
        return report
    if not python_exe.exists():
        report["error"] = "local_llm_env_python_missing"
        return report
    if not requirements.exists():
        report["error"] = "requirements_local_llm_missing"
        return report

    ollm_result = _run(install_ollm_command, timeout=max(60, int(args.timeout)))
    deps_result = _run(install_deps_command, timeout=max(60, int(args.timeout)))
    report["install_results"] = {
        "ollm_no_deps": ollm_result,
        "cpu_safe_dependencies": deps_result,
    }
    report["ollm_available_after"] = _module_available(python_exe, "ollm")
    report["llama_cpp_available_after"] = _module_available(python_exe, "llama_cpp")
    report["success"] = (
        ollm_result["returncode"] == 0
        and deps_result["returncode"] == 0
        and bool(report["ollm_available_after"])
        and bool(report["llama_cpp_available_after"])
    )
    if not report["success"]:
        report["error"] = (
            ollm_result.get("stderr")
            or deps_result.get("stderr")
            or "ollm_install_failed"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install optional OLLM backend in local_llm_env.")
    parser.add_argument("--apply", action="store_true", help="Run pip install")
    parser.add_argument("--env-dir", default="", help="Optional environment directory")
    parser.add_argument("--requirements", default="", help="Optional requirements file")
    parser.add_argument("--timeout", type=int, default=600, help="Pip timeout seconds")
    parser.add_argument("--pip-timeout", type=int, default=180, help="Per-package pip network timeout seconds")
    parser.add_argument("--retries", type=int, default=5, help="Pip retry count")
    args = parser.parse_args(argv)
    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
