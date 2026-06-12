from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "ANA_MAX" / "memory" / "os22_launch_audit_report.json"
LOCAL_ENV_PYTHON = ROOT / "local_llm_env" / "Scripts" / "python.exe"
ENV_FILE = ROOT / ".env.local_llm"
LOCAL_MODEL_DIR = ROOT / "local_models"

REQUIRED_LOCAL_MODULES = [
    "llama_cpp",
    "pytest",
    "requests",
    "numpy",
    "torch",
    "transformers",
    "accelerate",
    "peft",
    "gguf",
    "diskcache",
]

OPTIONAL_LOCAL_MODULES = [
    "bs4",
    "ollm",
]

REQUIRED_FILES = [
    "requirements.txt",
    "requirements_local_llm.txt",
    ".env.local_llm",
    "scripts/local_llm/start_local_llm.py",
    "scripts/local_llm/validate_local_llm_setup.py",
    "scripts/local_llm/test_local_brain.py",
    "scripts/os22/start_os22_agent.bat",
    "scripts/os22/os22_infer_smoke.py",
    "ANA_MAX/local/os22_doctor.py",
    "ANA_MAX/local/os22_boot.py",
    "ANA_MAX/local/local_llm_backend.py",
    "ANA_MAX/agents/local_brain_agent.py",
]

FOCUSED_TESTS = [
    "tests/test_os22_launch_audit.py",
    "tests/test_os22_doctor.py",
    "tests/test_os22_web_learning_tools.py",
    "tests/test_start_local_llm_agent.py",
    "tests/test_tool_dispatcher.py",
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ascii(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _run(command: list[str], timeout: int = 120) -> dict[str, Any]:
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
            "success": completed.returncode == 0,
        }
    except Exception as exc:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": _ascii(exc),
            "success": False,
        }


def _parse_json_output(result: dict[str, Any]) -> dict[str, Any]:
    stdout = str(result.get("stdout") or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stdout[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _requirements(path: Path) -> list[str]:
    if not path.exists():
        return []
    result: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            result.append(stripped)
    return result


def _python_info(python_exe: Path | str) -> dict[str, Any]:
    command = [
        str(python_exe),
        "-c",
        "import json,sys; print(json.dumps({'executable': sys.executable, 'version': sys.version.split()[0]}))",
    ]
    result = _run(command, timeout=30)
    info = {
        "exists": Path(str(python_exe)).exists() if "\\" in str(python_exe) or "/" in str(python_exe) else result["success"],
        "executable": str(python_exe),
        "version": "",
    }
    if result["success"]:
        info.update(_parse_json_output(result))
    return info


def _module_available(python_exe: Path, module_name: str) -> bool:
    if not python_exe.exists():
        return False
    code = (
        "import importlib.util,sys; "
        f"raise SystemExit(0 if importlib.util.find_spec({module_name!r}) else 1)"
    )
    return _run([str(python_exe), "-c", code], timeout=30)["success"]


def _file_checks() -> list[dict[str, Any]]:
    checks = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        checks.append(
            {
                "path": relative.replace("\\", "/"),
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
            }
        )
    return checks


def _model_checks(env_values: dict[str, str]) -> dict[str, Any]:
    configured = env_values.get("ANA_LOCAL_LLM_MODEL_PATH", "local_models/phi3-medium-q5_k_m.gguf")
    configured_path = Path(configured)
    if not configured_path.is_absolute():
        configured_path = ROOT / configured_path
    models = []
    if LOCAL_MODEL_DIR.exists():
        for path in sorted(LOCAL_MODEL_DIR.glob("*.gguf")):
            models.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "exists": True,
                }
            )
    return {
        "model_dir": str(LOCAL_MODEL_DIR),
        "model_dir_present": LOCAL_MODEL_DIR.exists(),
        "configured_model": str(configured_path),
        "configured_model_present": configured_path.exists(),
        "models": models,
    }


def _doctor_report(profile: str) -> dict[str, Any]:
    result = _run([sys.executable, "-m", "ANA_MAX.local.os22_doctor", "--profile", profile], timeout=120)
    parsed = _parse_json_output(result)
    return {
        "command": result["command"],
        "returncode": result["returncode"],
        "success": result["success"] and parsed.get("status") == "READY" and not parsed.get("failed_checks"),
        "report": parsed,
    }


def _boot_report(profile: str) -> dict[str, Any]:
    result = _run([sys.executable, "-m", "ANA_MAX.local.os22_boot", "--validate", "--profile", profile], timeout=120)
    parsed = _parse_json_output(result)
    inner = parsed.get("result", parsed)
    return {
        "command": result["command"],
        "returncode": result["returncode"],
        "success": result["success"] and inner.get("status") == "READY" and not inner.get("issues"),
        "report": parsed,
    }


def _local_llm_validation() -> dict[str, Any]:
    if not LOCAL_ENV_PYTHON.exists():
        return {
            "command": [str(LOCAL_ENV_PYTHON), "scripts/local_llm/validate_local_llm_setup.py"],
            "returncode": 1,
            "success": False,
            "report": {"overall_ready": False, "error": "local_llm_python_missing"},
        }
    result = _run(
        [str(LOCAL_ENV_PYTHON), "scripts/local_llm/validate_local_llm_setup.py"],
        timeout=120,
    )
    parsed = _parse_json_output(result)
    return {
        "command": result["command"],
        "returncode": result["returncode"],
        "success": result["success"] and bool(parsed.get("overall_ready")),
        "report": parsed,
    }


def _focused_tests() -> dict[str, Any]:
    existing = [path for path in FOCUSED_TESTS if (ROOT / path).exists()]
    result = _run([sys.executable, "-m", "pytest", *existing, "-q"], timeout=240)
    return {
        "command": result["command"],
        "returncode": result["returncode"],
        "success": result["success"],
        "stdout_tail": "\n".join(str(result.get("stdout", "")).splitlines()[-20:]),
        "stderr_tail": "\n".join(str(result.get("stderr", "")).splitlines()[-20:]),
    }


def _installation_notes(module_status: dict[str, bool], required_ok: bool) -> list[str]:
    notes: list[str] = []
    missing_required = [name for name in REQUIRED_LOCAL_MODULES if not module_status.get(name)]
    if missing_required or not required_ok:
        notes.append("Run: .\\local_llm_env\\Scripts\\python.exe -m pip install -r requirements_local_llm.txt")
    if not module_status.get("bs4", False):
        notes.append("Optional: install beautifulsoup4 only if legacy WebScraperTool parse/extract operations are needed.")
    if not module_status.get("ollm", False):
        notes.append("Optional: install ollm only if switching from llama_cpp to the old ollm backend.")
    if not notes:
        notes.append("No required install action detected.")
    return notes


def build_launch_audit(
    *,
    profile: str = "os22_core",
    run_tests: bool = False,
    write_report: bool = False,
) -> dict[str, Any]:
    env_values = _load_env_file()
    main_python = _python_info(sys.executable)
    local_python = _python_info(LOCAL_ENV_PYTHON)
    local_module_status = {
        name: _module_available(LOCAL_ENV_PYTHON, name)
        for name in [*REQUIRED_LOCAL_MODULES, *OPTIONAL_LOCAL_MODULES]
    }
    files = _file_checks()
    models = _model_checks(env_values)
    doctor = _doctor_report(profile)
    boot = _boot_report(profile)
    local_validation = _local_llm_validation()
    tests = _focused_tests() if run_tests else {"skipped": True, "success": True}

    required_modules_ok = all(local_module_status.get(name, False) for name in REQUIRED_LOCAL_MODULES)
    files_ok = all(item["exists"] for item in files)
    main_python_ok = str(main_python.get("version", "")).startswith("3.12.")
    local_python_ok = str(local_python.get("version", "")).startswith("3.11.")
    env_ok = ENV_FILE.exists() and env_values.get("ANA_LOCAL_LLM_BACKEND", "") == "llama_cpp"

    checks = [
        {"name": "main_python_3_12", "success": main_python_ok, "detail": main_python},
        {"name": "local_python_3_11", "success": local_python_ok, "detail": local_python},
        {"name": "required_files", "success": files_ok, "detail": files},
        {"name": "local_llm_modules", "success": required_modules_ok, "detail": local_module_status},
        {"name": "local_llm_env_file", "success": env_ok, "detail": env_values},
        {"name": "local_models", "success": models["configured_model_present"], "detail": models},
        {"name": "local_llm_validator", "success": local_validation["success"], "detail": local_validation},
        {"name": "os22_doctor", "success": doctor["success"], "detail": doctor},
        {"name": "os22_boot", "success": boot["success"], "detail": boot},
        {"name": "focused_tests", "success": bool(tests.get("success")), "detail": tests},
    ]
    warnings: list[str] = []
    notes: list[str] = []
    if not local_module_status.get("bs4", False):
        notes.append("optional_bs4_missing")
    if not env_values.get("ANA_LOCAL_LLM_ENABLED", "0") == "1":
        notes.append("local_llm_env_flag_disabled_but_cli_launch_is_ready")

    report = {
        "schema": "ana.os22.launch_audit.v1",
        "generated_at": _now(),
        "root": str(ROOT),
        "profile": profile,
        "metadata_only": True,
        "local_only": True,
        "checks": checks,
        "warnings": warnings,
        "notes": notes,
        "install_recommendations": _installation_notes(local_module_status, required_modules_ok),
        "launch_commands": {
            "interactive": "scripts\\os22\\start_os22_agent.bat",
            "doctor": "python -m ANA_MAX.local.os22_doctor --profile os22_core",
            "launch_audit": "python scripts\\os22\\os22_launch_audit.py --write-report",
            "strict_smoke": ".\\local_llm_env\\Scripts\\python.exe .\\scripts\\local_llm\\start_local_llm.py --smoke --profile os22_core --backend llama_cpp --model-path .\\local_models\\phi3-medium-q5_k_m.gguf --prompt \"Return exactly: READY\" --max-tokens 16 --temperature 0",
        },
        "overall_success": all(bool(check["success"]) for check in checks),
        "ready_for_human_testing": all(bool(check["success"]) for check in checks),
        "report_path": str(REPORT_PATH),
    }
    if write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ANA_MAX OS-22 launch readiness audit.")
    parser.add_argument("--profile", default="os22_core", help="Prompt profile to validate.")
    parser.add_argument("--run-tests", action="store_true", help="Run focused OS-22 pytest suite.")
    parser.add_argument("--write-report", action="store_true", help="Write report into ANA_MAX/memory.")
    args = parser.parse_args(argv)
    report = build_launch_audit(
        profile=args.profile,
        run_tests=args.run_tests,
        write_report=args.write_report,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
