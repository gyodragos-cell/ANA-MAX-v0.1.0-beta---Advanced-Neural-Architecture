"""
ANA MAX - System Integrity Check (OS27 Hyper++)
==============================================

Enterprise-grade integrity auditor pentru ANA MAX:

- Verifica ToolRegistry vs filesystem
- Verifica backends (ollama / omniroute / openrouter)
- Verifica settings.yaml
- Verifica dependente critice
- Verifica Ollama server
- Verifica loguri (cu LargeFileReaderHyperTool pentru fisiere mari)
- Verifica fisiere temporare
- Integreaza cu:
    - MemoryCortex (episodic + error memory)
    - ContextEngine (daca exista)
    - SelfEvolvingTool (auto-fix hooks)
    - Telemetrie OS27 (health scoring)
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import logging

logger = logging.getLogger("ANA.SystemIntegrity")

# Asiguram root-ul ANA_MAX in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Importuri ANA MAX
from tools.base import Tool, ToolResult, ToolDefinition, ToolStatus  # type: ignore
from tools.base import ToolRegistry  # type: ignore

# Optional AI Core
try:
    from tools.memory_cortex import MemoryCortex  # type: ignore
except Exception:
    MemoryCortex = None  # type: ignore

try:
    from tools.self_evolving_tool import SelfEvolvingTool  # type: ignore
except Exception:
    SelfEvolvingTool = None  # type: ignore

try:
    from tools.context_engine import ContextEngine  # type: ignore
except Exception:
    ContextEngine = None  # type: ignore

try:
    from tools.large_file_reader_ultimate import LargeFileReaderHyperTool  # type: ignore
except Exception:
    LargeFileReaderHyperTool = None  # type: ignore


# Telemetrie OS27 Hyper++
_integrity_telemetry: Dict[str, Dict[str, Any]] = {
    "runs": {
        "operation_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "last_status": "unknown",
    },
    "sections": {},
}


def _record_telemetry(section: str, success: bool) -> None:
    sec = _integrity_telemetry["sections"].setdefault(
        section,
        {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
        },
    )
    sec["operation_count"] += 1
    if success:
        sec["success_count"] += 1
    else:
        sec["failure_count"] += 1


def get_integrity_telemetry() -> Dict[str, Dict[str, Any]]:
    return _integrity_telemetry


def get_integrity_health() -> str:
    runs = _integrity_telemetry["runs"]
    if runs["failure_count"] == 0 and runs["success_count"] > 0:
        return "healthy"
    if runs["failure_count"] > 0 and runs["success_count"] > 0:
        return "degraded"
    if runs["success_count"] == 0 and runs["failure_count"] > 0:
        return "broken"
    return "unknown"


class SystemIntegrityHyperTool(Tool):
    """
    OS27 Hyper++ System Integrity Tool.

    MCP-ready, integrat cu ANA MAX AI Core.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="system_integrity_hyper",
            description=(
                "OS27 Hyper++ System Integrity Auditor pentru ANA MAX. "
                "Verifica registry, backends, config, dependente, Ollama, loguri, fisiere temporare, "
                "si raporteaza health + telemetrie."
            ),
            parameters=[],
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        logger.info("SystemIntegrityHyperTool: start audit")
        _integrity_telemetry["runs"]["operation_count"] += 1

        # AI Core hooks
        cortex = MemoryCortex() if MemoryCortex else None
        evolver = SelfEvolvingTool() if SelfEvolvingTool else None
        context_engine = ContextEngine() if ContextEngine else None

        report: Dict[str, Any] = {
            "tool_registry": {},
            "backends": {},
            "config": {},
            "dependencies": {},
            "ollama": {},
            "logs": {},
            "cleanup": {},
            "health": {},
        }

        base_dir = ROOT
        tools_dir = base_dir / "tools"
        config_dir = base_dir / "config"
        logs_dir = base_dir / "logs"

        # 1. TOOL REGISTRY
        try:
            section = "tool_registry"
            registry = ToolRegistry()
            registered_tools = registry.list_tools()
            tool_files = [
                f for f in tools_dir.glob("*.py")
                if f.name not in ("__init__.py", "base.py")
            ]

            tool_names = [f.stem for f in tool_files]
            registered_names = list(registered_tools)

            missing_in_registry = sorted(set(tool_names) - set(registered_names))
            orphaned_in_registry = sorted(set(registered_names) - set(tool_names))

            report["tool_registry"] = {
                "registered_count": len(registered_tools),
                "file_count": len(tool_files),
                "missing_in_registry": missing_in_registry,
                "orphaned_in_registry": orphaned_in_registry,
            }

            _record_telemetry(section, True)
        except Exception as e:
            logger.exception("Tool registry integrity failed")
            report["tool_registry"] = {"error": str(e)}
            _record_telemetry("tool_registry", False)
            if cortex:
                cortex.remember(
                    "error",
                    "system_integrity.tool_registry",
                    f"Tool registry check failed: {e}",
                )

        # 2. BACKENDS
        backends = ["ollama", "omniroute", "openrouter"]
        backend_status: Dict[str, Any] = {}
        for backend in backends:
            try:
                module = importlib.import_module(f"core.backends.{backend}_backend")
                has_init = hasattr(module, "init")
                backend_status[backend] = {
                    "import": True,
                    "has_init": has_init,
                }
                _record_telemetry(f"backend_{backend}", True)
            except ImportError as e:
                backend_status[backend] = {
                    "import": False,
                    "error": str(e),
                }
                _record_telemetry(f"backend_{backend}", False)
                if cortex:
                    cortex.remember(
                        "error",
                        f"system_integrity.backend.{backend}",
                        f"Backend import failed: {e}",
                    )
        report["backends"] = backend_status

        # 3. CONFIG
        settings_file = config_dir / "settings.yaml"
        config_info: Dict[str, Any] = {}
        try:
            if settings_file.exists():
                import yaml  # type: ignore

                with open(settings_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}

                config_info["exists"] = True
                config_info["primary_backend"] = cfg.get("primary_backend")
                config_info["fallback_backend"] = cfg.get("fallback_backend")
                config_info["defined_backends"] = list((cfg.get("backends") or {}).keys())
                _record_telemetry("config", True)
            else:
                config_info["exists"] = False
                config_info["error"] = "settings.yaml missing"
                _record_telemetry("config", False)
        except Exception as e:
            config_info["error"] = str(e)
            _record_telemetry("config", False)
            if cortex:
                cortex.remember(
                    "error",
                    "system_integrity.config",
                    f"Config parsing failed: {e}",
                )
        report["config"] = config_info

        # 4. DEPENDENCIES
        critical_deps = [
            ("pydantic", "pydantic"),
            ("requests", "requests"),
            ("frida", "frida"),
            ("opencv", "cv2"),
            ("numpy", "numpy"),
        ]
        deps_status: Dict[str, Any] = {}
        for module_name, import_name in critical_deps:
            try:
                importlib.import_module(import_name)
                deps_status[module_name] = {"available": True}
                _record_telemetry(f"dep_{module_name}", True)
            except ImportError:
                deps_status[module_name] = {"available": False}
                _record_telemetry(f"dep_{module_name}", False)
                if cortex:
                    cortex.remember(
                        "error",
                        f"system_integrity.dep.{module_name}",
                        f"Dependency missing: {module_name}",
                    )
        report["dependencies"] = deps_status

        # 5. OLLAMA
        ollama_info: Dict[str, Any] = {}
        try:
            import requests  # type: ignore

            resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            ollama_info["reachable"] = resp.status_code == 200
            ollama_info["status_code"] = resp.status_code
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                ollama_info["models_count"] = len(models)
                ollama_info["models_sample"] = [
                    m.get("name", "unknown") for m in models[:5]
                ]
                _record_telemetry("ollama", True)
            else:
                _record_telemetry("ollama", False)
        except Exception as e:
            ollama_info["reachable"] = False
            ollama_info["error"] = str(e)
            _record_telemetry("ollama", False)
            if cortex:
                cortex.remember(
                    "error",
                    "system_integrity.ollama",
                    f"Ollama check failed: {e}",
                )
        report["ollama"] = ollama_info

        # 6. LOGS (cu LargeFileReaderHyperTool daca exista)
        logs_info: Dict[str, Any] = {}
        try:
            if logs_dir.exists():
                log_files = list(logs_dir.glob("*.log"))
                logs_info["log_files_count"] = len(log_files)
                total_errors = 0
                per_file: Dict[str, Any] = {}

                for lf in log_files:
                    errors = 0
                    if LargeFileReaderHyperTool:
                        # folosim reader-ul hyper pentru fisiere mari
                        reader = LargeFileReaderHyperTool()
                        result = reader.execute(
                            file_path=str(lf),
                            chunk_size=2000,
                            max_chunks=1,
                        )
                        if result.status == ToolStatus.SUCCESS:
                            chunks = result.data.get("chunks", [])
                            if chunks:
                                # chunks are dicts with "text" field
                                content = chunks[0].get("text", "")
                                errors = content.count("ERROR") + content.count("Exception")
                        else:
                            # fallback: citire simpla
                            with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                errors = content.count("ERROR") + content.count("Exception")
                    else:
                        with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            errors = content.count("ERROR") + content.count("Exception")

                    total_errors += errors
                    per_file[lf.name] = {"errors": errors}

                logs_info["total_errors"] = total_errors
                logs_info["files"] = per_file
                _record_telemetry("logs", True)
            else:
                logs_info["error"] = "logs directory missing"
                _record_telemetry("logs", False)
        except Exception as e:
            logs_info["error"] = str(e)
            _record_telemetry("logs", False)
            if cortex:
                cortex.remember(
                    "error",
                    "system_integrity.logs",
                    f"Log analysis failed: {e}",
                )
        report["logs"] = logs_info

        # 7. CLEANUP
        cleanup_info: Dict[str, Any] = {}
        try:
            temp_patterns = ["*.tmp", "*.bak", "*.old", "*.temp", "*~"]
            temp_files: List[str] = []
            for root_dir, dirs, files in os.walk(str(base_dir.parent)):
                for file in files:
                    for pattern in temp_patterns:
                        suffix = pattern.replace("*", "")
                        if file.endswith(suffix):
                            temp_files.append(os.path.join(root_dir, file))
                            break

            cleanup_info["temp_files_count"] = len(temp_files)
            cleanup_info["sample"] = temp_files[:20]
            _record_telemetry("cleanup", True)
        except Exception as e:
            cleanup_info["error"] = str(e)
            _record_telemetry("cleanup", False)
        report["cleanup"] = cleanup_info

        # HEALTH SUMMARY
        health = {
            "integrity_health": get_integrity_health(),
            "telemetry": get_integrity_telemetry(),
        }
        report["health"] = health

        # ContextEngine update
        if context_engine:
            try:
                context_engine.start_observing()
                context_engine.apply_feedback(
                    source="system_integrity",
                    feedback={
                        "health": health["integrity_health"],
                        "ollama": ollama_info,
                        "backends": backend_status,
                        "dependencies": deps_status,
                    },
                )
            except Exception:
                logger.warning("ContextEngine integration failed in SystemIntegrityHyperTool")

        # SelfEvolvingTool hooks (daca ceva e broken)
        if evolver and health["integrity_health"] in ("degraded", "broken"):
            try:
                evolver.analyze_anomaly(
                    anomaly_type="system_integrity",
                    details={
                        "report": report,
                    },
                )
            except Exception:
                logger.warning("SelfEvolvingTool integration failed in SystemIntegrityHyperTool")

        # MemoryCortex episodic
        if cortex:
            try:
                cortex.remember(
                    "episodic",
                    "system_integrity.run",
                    f"System integrity run: health={health['integrity_health']}",
                )
            except Exception:
                logger.warning("MemoryCortex episodic integration failed in SystemIntegrityHyperTool")

        _integrity_telemetry["runs"]["last_status"] = health["integrity_health"]
        if health["integrity_health"] in ("healthy", "degraded"):
            _integrity_telemetry["runs"]["success_count"] += 1
        else:
            _integrity_telemetry["runs"]["failure_count"] += 1

        logger.info("SystemIntegrityHyperTool: audit completed (%s)", health["integrity_health"])

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=report,
        )
