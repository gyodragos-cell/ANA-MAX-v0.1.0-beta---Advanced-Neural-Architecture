"""Validate optional dual-Python local LLM setup."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DEFAULT_ENV_DIR = ROOT / "local_llm_env"
DEFAULT_MODEL_DIR = ROOT / "local_models"
DEFAULT_ENV_FILE = ROOT / ".env.local_llm"
BACKEND_MODULES = {
    "llama_cpp": "llama_cpp",
    "ollm": "ollm",
}


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


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _module_available(python_exe: Path, module_name: str) -> bool:
    if not python_exe.exists():
        return False
    result = _run(
        [
            str(python_exe),
            "-c",
            f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec('{module_name}') else 1)",
        ]
    )
    return result["returncode"] == 0


def _python_info(python_exe: Path) -> dict[str, Any]:
    if not python_exe.exists():
        return {"exists": False, "version": "", "executable": str(python_exe)}
    result = _run(
        [
            str(python_exe),
            "-c",
            "import sys,json; print(json.dumps({'version': sys.version.split()[0], 'executable': sys.executable}))",
        ]
    )
    info = {"exists": True, "version": "", "executable": str(python_exe)}
    if result["returncode"] == 0:
        try:
            info.update(json.loads(result["stdout"]))
        except json.JSONDecodeError:
            pass
    return info


def _python_command_info(command: list[str]) -> dict[str, Any]:
    result = _run(
        command
        + [
            "-c",
            "import sys,json; print(json.dumps({'version': sys.version.split()[0], 'executable': sys.executable}))",
        ]
    )
    info: dict[str, Any] = {
        "command": command,
        "exists": result["returncode"] == 0,
        "version": "",
        "executable": "",
    }
    if result["returncode"] == 0:
        try:
            info.update(json.loads(result["stdout"]))
        except json.JSONDecodeError:
            pass
    return info


def _detect_main_python312() -> dict[str, Any]:
    candidates: list[list[str]] = []
    if sys.version_info[:2] == (3, 12):
        candidates.append([sys.executable])
    python_on_path = shutil.which("python")
    if python_on_path:
        candidates.append([python_on_path])
    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append([py_launcher, "-3.12"])

    seen: set[tuple[str, ...]] = set()
    for command in candidates:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        info = _python_command_info(command)
        if str(info.get("version", "")).startswith("3.12."):
            info["detected"] = True
            return info
    return {
        "command": [],
        "exists": False,
        "version": "",
        "executable": "",
        "detected": False,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env_dir = Path(args.env_dir).resolve() if args.env_dir else DEFAULT_ENV_DIR
    model_dir = Path(args.model_dir).resolve() if args.model_dir else DEFAULT_MODEL_DIR
    env_file = Path(args.env_file).resolve() if args.env_file else DEFAULT_ENV_FILE
    env_python = env_dir / "Scripts" / "python.exe"
    env_values = _load_env_file(env_file)
    main_python = _detect_main_python312()
    configured_backend = env_values.get("ANA_LOCAL_LLM_BACKEND", "ollm").strip().lower()
    active_backend_module = BACKEND_MODULES.get(configured_backend, configured_backend)
    active_backend_available = _module_available(env_python, active_backend_module)
    model_path = Path(env_values.get("ANA_LOCAL_LLM_MODEL_PATH", "local_models/phi3-medium-q5_k_m.gguf"))
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    model_files = sorted(str(path.relative_to(model_dir)) for path in model_dir.glob("*.gguf")) if model_dir.exists() else []
    checks = {
        "main_python_3_12": str(main_python.get("version", "")).startswith("3.12."),
        "local_llm_env_present": env_dir.exists(),
        "local_llm_python_present": env_python.exists(),
        "local_llm_python_3_11": str(_python_info(env_python).get("version", "")).startswith("3.11."),
        "ollm_installed": _module_available(env_python, "ollm"),
        "llama_cpp_installed": _module_available(env_python, "llama_cpp"),
        "active_backend_available": active_backend_available,
        "env_file_present": env_file.exists(),
        "model_dir_present": model_dir.exists(),
        "configured_model_present": model_path.exists(),
    }
    readiness_checks = [
        "main_python_3_12",
        "local_llm_env_present",
        "local_llm_python_present",
        "local_llm_python_3_11",
        "active_backend_available",
        "env_file_present",
        "model_dir_present",
        "configured_model_present",
    ]
    return {
        "schema": "ana.local_llm.validation.v1",
        "root": str(ROOT),
        "main_python": main_python,
        "local_env": {
            "env_dir": str(env_dir),
            "python": _python_info(env_python),
            "ollm_installed": checks["ollm_installed"],
            "llama_cpp_installed": checks["llama_cpp_installed"],
            "active_backend": configured_backend,
            "active_backend_module": active_backend_module,
            "active_backend_available": active_backend_available,
        },
        "env_file": {
            "path": str(env_file),
            "exists": env_file.exists(),
            "values": env_values,
        },
        "models": {
            "model_dir": str(model_dir),
            "model_dir_present": model_dir.exists(),
            "configured_model_path": str(model_path),
            "configured_model_present": model_path.exists(),
            "gguf_files": model_files,
        },
        "checks": checks,
        "overall_ready": all(bool(checks[name]) for name in readiness_checks),
        "runtime_safe_without_ready": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate optional ANA local LLM setup.")
    parser.add_argument("--env-dir", default="", help="Optional environment directory")
    parser.add_argument("--model-dir", default="", help="Optional model directory")
    parser.add_argument("--env-file", default="", help="Optional env file")
    args = parser.parse_args(argv)
    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
