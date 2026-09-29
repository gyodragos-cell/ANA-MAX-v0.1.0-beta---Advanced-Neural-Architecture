from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

# Telemetry OS27 Hyper++
_SYSTEM_INTEGRITY_TELEMETRY: Dict[str, Any] = {
    "operation_count": 0,
    "success_count": 0,
    "failure_count": 0,
    "total_time": 0.0,
    "last_execution_time": 0.0,
    "last_success": False,
}


def _record_system_integrity_telemetry(success: bool, duration: float) -> None:
    _SYSTEM_INTEGRITY_TELEMETRY["operation_count"] += 1
    _SYSTEM_INTEGRITY_TELEMETRY["total_time"] += duration
    _SYSTEM_INTEGRITY_TELEMETRY["last_execution_time"] = duration
    _SYSTEM_INTEGRITY_TELEMETRY["last_success"] = bool(success)
    if success:
        _SYSTEM_INTEGRITY_TELEMETRY["success_count"] += 1
    else:
        _SYSTEM_INTEGRITY_TELEMETRY["failure_count"] += 1


def get_system_integrity_telemetry() -> Dict[str, Any]:
    return dict(_SYSTEM_INTEGRITY_TELEMETRY)


def get_system_integrity_health() -> str:
    ops = _SYSTEM_INTEGRITY_TELEMETRY["operation_count"]
    fails = _SYSTEM_INTEGRITY_TELEMETRY["failure_count"]
    if ops == 0:
        return "unknown"
    failure_rate = fails / max(1, ops)
    if failure_rate == 0.0:
        return "healthy"
    if failure_rate < 0.3:
        return "degraded"
    return "broken"


class SystemIntegrityCheckTool(Tool):
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self._root = root
        self._tools_dir = root / "tools"
        self._config_file = root / "config" / "settings.yaml"
        self._logs_dir = root / "logs"
        self._project_root = root.parent

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="system_integrity_check",
            description=(
                "OS27 Hyper++ audit pentru ANA MAX: verifica tool registry, backends, config, "
                "dependinte critice, loguri si fisiere temporare. Returneaza health global."
            ),
            parameters=[
                ToolParameter(
                    name="mode",
                    description="quick sau full (full include logs + temp scan + AI Core check)",
                    type="string",
                    required=False,
                    default="quick",
                    choices=["quick", "full"],
                ),
                ToolParameter(
                    name="include_logs",
                    description="Daca sa scaneze logurile pentru erori",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="include_temp_scan",
                    description="Daca sa caute fisiere temporare/gunoi",
                    type="boolean",
                    required=False,
                    default=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        start = time.perf_counter()
        mode = str(kwargs.get("mode", "quick") or "quick")
        include_logs = bool(kwargs.get("include_logs", mode == "full"))
        include_temp = bool(kwargs.get("include_temp_scan", mode == "full"))

        try:
            registry_info = self._check_tool_registry()
            backend_info = self._check_backends()
            config_info = self._check_config()
            deps_info = self._check_dependencies()

            logs_info: Dict[str, Any] = {}
            if include_logs:
                logs_info = self._check_logs()

            temp_info: Dict[str, Any] = {}
            if include_temp:
                temp_info = self._check_temp_files()

            ai_core_info = self._check_ai_core_components()

            overall_health = self._compute_overall_health(
                registry_info, backend_info, config_info, deps_info, logs_info, ai_core_info
            )

            duration = time.perf_counter() - start
            _record_system_integrity_telemetry(success=True, duration=duration)

            # Lazy MemoryCortex / ContextEngine integration
            self._maybe_record_in_memory(overall_health, registry_info, backend_info, ai_core_info)
            self._maybe_update_context(overall_health)

            data = {
                "schema": "ana.os27.system_integrity.v1",
                "mode": mode,
                "overall_health": overall_health,
                "sections": {
                    "tool_registry": registry_info,
                    "backends": backend_info,
                    "config": config_info,
                    "dependencies": deps_info,
                    "logs": logs_info,
                    "temp_files": temp_info,
                    "ai_core": ai_core_info,
                },
                "telemetry": get_system_integrity_telemetry(),
            }
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                message=f"System integrity: {overall_health} (mode={mode})",
            )
        except Exception as e:
            duration = time.perf_counter() - start
            _record_system_integrity_telemetry(success=False, duration=duration)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"System integrity check failed: {e}",
            )

    # --- Sectiuni de verificare ------------------------------------------------

    def _check_tool_registry(self) -> Dict[str, Any]:
        # Use the actual registry from tools/__init__.py instead of creating a new empty one
        try:
            from tools import get_all_tool_health  # Use the actual registry
            
            tool_health = get_all_tool_health()
            registered_names = set(tool_health.keys())
        except Exception:
            # Fallback to ToolRegistry if get_all_tool_health fails
            from tools.base import ToolRegistry
            registry = ToolRegistry()
            registered = registry.list_tools()
            
            if isinstance(registered, dict):
                registered_names = set(registered.keys())
            elif isinstance(registered, list):
                registered_names = set(registered)
            else:
                registered_names = set()
        
        # Get module names from _CLASS_TO_MODULE for comparison with file stems
        try:
            from tools import _CLASS_TO_MODULE
            module_names = set(_CLASS_TO_MODULE.values())
        except Exception:
            module_names = set()
        
        tool_files = [p for p in self._tools_dir.glob("*.py") if p.name not in {"__init__.py", "base.py"}]
        file_names = {p.stem for p in tool_files}

        # Compare file stems against module names (not class names)
        # Filtram scripturile de utility care nu sunt tool-uri efective
        actual_missing = sorted(file_names - module_names)
        missing_in_registry = [m for m in actual_missing if m.endswith("_tool") or m.endswith("_adapter")]
        orphaned_in_registry = sorted(module_names - file_names)

        health = "healthy" if not missing_in_registry and not orphaned_in_registry else "degraded"

        return {
            "registered_count": len(registered_names),
            "file_count": len(tool_files),
            "module_count": len(module_names),
            "missing_in_registry": missing_in_registry,
            "orphaned_in_registry": orphaned_in_registry,
            "health": health,
        }

    def _check_backends(self) -> Dict[str, Any]:
        import importlib

        backends = ["ollama", "omniroute", "openrouter"]
        results: Dict[str, Any] = {}
        for backend in backends:
            try:
                module = importlib.import_module(f"core.backends.{backend}_backend")
                has_init = hasattr(module, "init")
                results[backend] = {"available": True, "has_init": has_init}
            except ImportError as e:
                results[backend] = {"available": False, "error": str(e)}
        return results

    def _check_config(self) -> Dict[str, Any]:
        if not self._config_file.exists():
            return {"exists": False, "health": "broken", "error": "settings.yaml missing"}
        try:
            import yaml  # lazy

            with self._config_file.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            ai_config = config.get("ai", {})
            primary = ai_config.get("primary_backend")
            fallback = ai_config.get("fallback_backend")
            backends = [b.get("backend") for b in ai_config.get("routing", {}).get("backends", [])] if ai_config.get("routing") else []
            return {
                "exists": True,
                "primary_backend": primary,
                "fallback_backend": fallback,
                "defined_backends": backends,
                "health": "healthy" if primary else "degraded",
            }
        except Exception as e:
            return {"exists": True, "health": "broken", "error": str(e)}

    def _check_dependencies(self) -> Dict[str, Any]:
        import importlib

        critical_deps = [
            ("pydantic", "pydantic"),
            ("requests", "requests"),
            ("frida", "frida"),
            ("opencv", "cv2"),
            ("numpy", "numpy"),
        ]
        results: Dict[str, Any] = {}
        for name, import_name in critical_deps:
            try:
                importlib.import_module(import_name)
                results[name] = {"available": True}
            except ImportError as e:
                results[name] = {"available": False, "error": str(e)}
        return results

    def _check_logs(self) -> Dict[str, Any]:
        if not self._logs_dir.exists():
            return {"exists": False, "health": "unknown"}
        log_files = list(self._logs_dir.glob("*.log"))
        error_count = 0
        per_file: List[Dict[str, Any]] = []

        # Daca logurile devin mari, aici poti integra LargeFileReaderHyperTool
        for log_file in log_files:
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                errors = content.count("ERROR") + content.count("Exception")
                error_count += errors
                per_file.append({"file": log_file.name, "errors": errors})
            except Exception:
                per_file.append({"file": log_file.name, "errors": -1, "error": "read_failed"})

        health = "healthy"
        if error_count > 0:
            health = "degraded"
        if error_count > 100:
            health = "broken"

        return {
            "exists": True,
            "log_files": [f["file"] for f in per_file],
            "per_file": per_file,
            "total_errors": error_count,
            "health": health,
        }

    def _check_temp_files(self) -> Dict[str, Any]:
        import os

        temp_patterns = ["*.tmp", "*.bak", "*.old", "*.temp", "*~"]
        temp_files: List[str] = []
        for root, dirs, files in os.walk(str(self._project_root)):
            for file in files:
                for pattern in temp_patterns:
                    suffix = pattern.replace("*", "")
                    if file.endswith(suffix):
                        temp_files.append(os.path.join(root, file))
                        break

        return {
            "count": len(temp_files),
            "sample": temp_files[:10],
            "health": "healthy" if not temp_files else "degraded",
        }

    def _check_ai_core_components(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        # Check AI Core adapters instead of raw modules
        try:
            from tools.tool_adapters import (
                ContextEngineAdapter, MemoryCortexAdapter, 
                ProactiveInterruptAdapter, SelfEvolvingToolAdapter,
                AnaOrchestratorAdapter, ContextBridgeAdapter
            )
            info["context_engine"] = {"available": True}
            info["memory_cortex"] = {"available": True}
            info["proactive_interrupt"] = {"available": True}
            info["self_evolving_tool"] = {"available": True}
            info["ana_orchestrator"] = {"available": True}
            info["context_bridge"] = {"available": True}
        except Exception as e:
            # If adapters fail to import, check individual components
            try:
                import tools.memory_cortex
                info["memory_cortex"] = {"available": "MemoryCortex" in dir(tools.memory_cortex)}
            except Exception as e2:
                info["memory_cortex"] = {"available": False, "error": str(e2)}
            
            try:
                import tools.context_engine
                info["context_engine"] = {"available": "start_observing" in dir(tools.context_engine)}
            except Exception as e2:
                info["context_engine"] = {"available": False, "error": str(e2)}
            
            try:
                import tools.self_evolving_tool
                info["self_evolving_tool"] = {"available": "SelfEvolvingTool" in dir(tools.self_evolving_tool)}
            except Exception as e2:
                info["self_evolving_tool"] = {"available": False, "error": str(e2)}
            
            try:
                import tools.proactive_interrupt
                info["proactive_interrupt"] = {"available": "ProactiveInterrupt" in dir(tools.proactive_interrupt)}
            except Exception as e2:
                info["proactive_interrupt"] = {"available": False, "error": str(e2)}
            
            try:
                import tools.ana_orchestrator
                info["ana_orchestrator"] = {"available": "AnaOrchestrator" in dir(tools.ana_orchestrator)}
            except Exception as e2:
                info["ana_orchestrator"] = {"available": False, "error": str(e2)}
            
            try:
                import tools.context_bridge
                info["context_bridge"] = {"available": "ContextBridge" in dir(tools.context_bridge)}
            except Exception as e2:
                info["context_bridge"] = {"available": False, "error": str(e2)}
        
        return info

    def _compute_overall_health(
        self,
        registry: Dict[str, Any],
        backends: Dict[str, Any],
        config: Dict[str, Any],
        deps: Dict[str, Any],
        logs: Dict[str, Any],
        ai_core: Dict[str, Any],
    ) -> str:
        scores: List[str] = []

        scores.append(registry.get("health", "unknown"))
        if any(not v.get("available", False) for v in backends.values()):
            scores.append("degraded")
        scores.append(config.get("health", "unknown"))
        if any(not v.get("available", True) for v in deps.values()):
            scores.append("degraded")
        if logs:
            scores.append(logs.get("health", "unknown"))
        if any(not v.get("available", True) for v in ai_core.values()):
            scores.append("degraded")

        if "broken" in scores:
            return "broken"
        if "degraded" in scores:
            return "degraded"
        if "healthy" in scores:
            return "healthy"
        return "unknown"

    # --- Integrare AI Core (lazy) ---------------------------------------------

    def _maybe_record_in_memory(
        self,
        overall_health: str,
        registry: Dict[str, Any],
        backends: Dict[str, Any],
        ai_core: Dict[str, Any],
    ) -> None:
        try:
            from tools.memory_cortex import MemoryCortex  # lazy

            cortex = MemoryCortex()
            cortex.learned_success(
                task_type="system_integrity",
                pattern=f"health={overall_health}",
                notes=f"Registry: {registry.get('health')}, backends: {backends}, ai_core: {ai_core}",
            )
        except Exception:
            # nu rupem toolul daca MemoryCortex nu e disponibil
            pass

    def _maybe_update_context(self, overall_health: str) -> None:
        try:
            from tools.context_engine import ContextEngine  # lazy

            engine = ContextEngine()
            engine.update_context(
                source="system_integrity_check",
                payload={"overall_health": overall_health},
            )
        except Exception:
            pass
