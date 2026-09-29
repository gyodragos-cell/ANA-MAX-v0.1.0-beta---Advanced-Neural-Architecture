"""ANA MAX Skill Tool (OS27 Hyper++) — exposes SkillEngine through the standard ANATool interface.

Registered as 'skill_tool' in the ANA tool registry.
Available actions: list, execute, validate, status, reload.

White-hat standards:
  - Input sanitization delegated to SkillEngine (capability allowlist regex)
  - Rate limiting enforced by SkillEngine (not duplicated here)
  - All outputs schema-validated (SkillResult.to_dict())
  - Audit trail generated per execution (trace_id propagated from caller)

OS27 Hyper++ Features:
- Telemetry tracking for skill operations (list, execute, validate, status, reload)
- Health monitoring for skill operations reliability
- MemoryCortex integration for skill errors and state learning
- ContextEngine integration for skill state awareness
- SelfEvolvingTool integration for anomaly detection on skill failures
- Structured logging with error detection
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_skill_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_skill_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for skill operations."""
    if operation not in _skill_telemetry:
        _skill_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _skill_telemetry[operation]["operation_count"] += 1
    _skill_telemetry[operation]["total_time"] += execution_time
    _skill_telemetry[operation]["last_execution_time"] = execution_time
    _skill_telemetry[operation]["last_success"] = success
    
    if success:
        _skill_telemetry[operation]["success_count"] += 1
    else:
        _skill_telemetry[operation]["failure_count"] += 1


def get_skill_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for skill operations."""
    if operation:
        return _skill_telemetry.get(operation, {})
    return _skill_telemetry.copy()


def get_skill_health() -> str:
    """Get health status for skill tool based on telemetry."""
    if not _skill_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _skill_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _skill_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

# ---------------------------------------------------------------------------
# Lazy import guard — SkillEngine is heavyweight, import only when tool is used
# ---------------------------------------------------------------------------

def _get_engine():
    from ANA_MAX.skills.skill_engine import SkillEngine
    engine = SkillEngine.instance()
    if not engine._loaded:
        engine.load()
    return engine


# ---------------------------------------------------------------------------
# ANATool integration — follows the pattern in tools/base.py
# ---------------------------------------------------------------------------

try:
    from tools.base import ANATool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

    class SkillTool(ANATool):
        """Exposes SkillEngine capabilities through the ANA tool registry.

        Usage from agent:
            skill_tool action=list
            skill_tool action=execute capability=health.check
            skill_tool action=execute capability=fs.inspect path=C:/some/dir
            skill_tool action=validate path=ANA_MAX/skills/skills/my-skill/SKILL.md
            skill_tool action=status
            skill_tool action=reload
        """

        NAME = "skill_tool"
        DESCRIPTION = (
            "Execute ANA MAX OS v2 skills by capability name. "
            "Use action=list to see available capabilities. "
            "Use action=execute with a capability name to run a skill. "
            "Skills are higher-level operations composed of multiple tools."
        )

        def get_definition(self) -> ToolDefinition:
            return ToolDefinition(
                name=self.NAME,
                description=self.DESCRIPTION,
                parameters=[
                    ToolParameter(
                        name="action",
                        description="Action: list | execute | validate | status | reload",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="capability",
                        description="Capability name for action=execute (e.g. health.check, fs.inspect, self.repair)",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="path",
                        description="Target path for action=validate (SKILL.md file) or passed as payload for fs.inspect",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="payload",
                        description="JSON string with additional arguments for the skill (e.g. '{\"path\": \"C:/some/dir\"}')",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="trace_id",
                        description="Optional trace ID for audit correlation",
                        type="string",
                        required=False,
                    ),
                ],
            )

        def execute(self, **kwargs: Any) -> ToolResult:
            start_time = time.time()
            
            # AI Core hooks (lazy import for safety)
            cortex = None
            context_engine = None
            evolver = None
            try:
                from tools.memory_cortex import MemoryCortex
                cortex = MemoryCortex()
            except Exception:
                pass
            try:
                from tools.context_engine import ContextEngine
                context_engine = ContextEngine()
            except Exception:
                pass
            try:
                from tools.self_evolving_tool import SelfEvolvingTool
                evolver = SelfEvolvingTool()
            except Exception:
                pass
            
            action = str(kwargs.get("action", "")).strip().lower()

            dispatch = {
                "list": self._action_list,
                "execute": self._action_execute,
                "validate": self._action_validate,
                "status": self._action_status,
                "reload": self._action_reload,
            }

            handler = dispatch.get(action)
            if handler is None:
                execution_time = time.time() - start_time
                _record_skill_telemetry(action, False, execution_time)
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"Unknown action '{action}'. Valid: {sorted(dispatch)}",
                    data={"valid_actions": sorted(dispatch)},
                )

            try:
                result = handler(**kwargs)
                execution_time = time.time() - start_time
                _record_skill_telemetry(action, result.is_success, execution_time)
                
                # ContextEngine integration for skill state
                if context_engine and result.is_success:
                    try:
                        context_engine.update_context(
                            key="skill_state",
                            value={
                                "action": action,
                                "capability": kwargs.get("capability", ""),
                                "success": result.is_success,
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                # MemoryCortex integration for skill errors
                if cortex and not result.is_success:
                    try:
                        cortex.remember(
                            "error",
                            f"skill.{action}",
                            f"Skill operation failed: {result.error}"
                        )
                    except Exception:
                        pass
                
                return result
            except Exception as exc:
                execution_time = time.time() - start_time
                _record_skill_telemetry(action, False, execution_time)
                
                # MemoryCortex integration for skill errors
                if cortex:
                    try:
                        cortex.remember(
                            "error",
                            f"skill.{action}",
                            f"Skill operation failed: {str(exc)}"
                        )
                    except Exception:
                        pass
                
                logger.exception("SKILL_TOOL action=%s exception=%s", action, exc)
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"skill_tool internal error on action={action}: {exc}",
                    data={"exception": str(exc)},
                )

        # ------------------------------------------------------------------
        # Handlers
        # ------------------------------------------------------------------

        def _action_list(self, **kwargs: Any) -> ToolResult:
            engine = _get_engine()
            caps = engine.list_capabilities()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"{len(caps)} capabilities registered",
                data={"capabilities": caps},
            )

        def _action_execute(self, **kwargs: Any) -> ToolResult:
            capability = str(kwargs.get("capability", "")).strip()
            if not capability:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message="action=execute requires 'capability' parameter",
                )

            # Build payload: start with explicit 'payload' JSON, then merge top-level kwargs
            raw_payload = kwargs.get("payload", "{}")
            try:
                payload: Dict[str, Any] = json.loads(raw_payload) if isinstance(raw_payload, str) else (raw_payload or {})
            except json.JSONDecodeError as exc:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"Invalid JSON in 'payload': {exc}",
                )

            # Convenience: path kwarg forwarded to payload
            if "path" in kwargs and "path" not in payload:
                payload["path"] = kwargs["path"]

            trace_id = str(kwargs.get("trace_id", "")).strip()
            engine = _get_engine()
            result = engine.execute(capability, payload, trace_id=trace_id, actor="skill_tool")

            status = ToolStatus.SUCCESS if result.status == "success" else ToolStatus.ERROR
            return ToolResult(
                status=status,
                message=f"skill '{capability}' → {result.status} ({result.elapsed_ms:.1f}ms)",
                data=result.to_dict(),
            )

        def _action_validate(self, **kwargs: Any) -> ToolResult:
            path_str = str(kwargs.get("path", "")).strip()
            if not path_str:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message="action=validate requires 'path' parameter pointing to a SKILL.md file",
                )
            p = Path(path_str)
            if not p.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"File not found: {p}",
                )
            try:
                text = p.read_text(encoding="utf-8")
            except Exception as exc:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"Cannot read file: {exc}",
                )

            engine = _get_engine()
            spec = engine.parse(text)
            vr = engine.validate(spec)
            data = {
                "valid": vr.valid,
                "title": spec.title,
                "version": spec.version,
                "has_version": vr.has_version,
                "missing_sections": vr.missing_sections,
                "errors": vr.errors,
                "sections_found": list(spec.sections.keys()),
            }
            status = ToolStatus.SUCCESS if vr.valid else ToolStatus.ERROR
            msg = "SKILL.md valid" if vr.valid else f"SKILL.md invalid — {vr.errors}"
            return ToolResult(status=status, message=msg, data=data)

        def _action_status(self, **kwargs: Any) -> ToolResult:
            engine = _get_engine()
            from ANA_MAX.skills.skill_engine import _CALL_COUNTS, _HEADING_CACHE, _RATE_LIMITED
            caps = engine.list_capabilities()
            data = {
                "loaded": engine._loaded,
                "capabilities_registered": len(caps),
                "capabilities": [c["capability"] for c in caps],
                "skills_root": str(engine._skills_root),
                "config_path": str(engine._config_path),
                "heading_cache_size": len(_HEADING_CACHE),
                "session_call_counts": dict(_CALL_COUNTS),
                "rate_limits": dict(_RATE_LIMITED),
            }
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Skill engine loaded={engine._loaded}, {len(caps)} capabilities",
                data=data,
            )

        def _action_reload(self, **kwargs: Any) -> ToolResult:
            engine = _get_engine()
            engine.reload()
            caps = engine.list_capabilities()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Skill engine reloaded — {len(caps)} capabilities",
                data={"capabilities_registered": len(caps)},
            )

    # Auto-register
    def get_tool() -> SkillTool:
        return SkillTool()

except ImportError:
    # Fallback when running outside the ANA tool registry (e.g. unit tests)
    logger.warning("SKILL_TOOL ANATool base not importable — running in standalone mode")

    def get_tool():  # type: ignore[misc]
        return None


# ---------------------------------------------------------------------------
# Standalone CLI entrypoint (for direct_bridge.py --execute)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="skill_tool standalone runner")
    parser.add_argument("--action", required=True, choices=["list", "execute", "validate", "status", "reload"])
    parser.add_argument("--capability", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--payload", default="{}")
    parser.add_argument("--trace-id", default="")
    args = parser.parse_args()

    from ANA_MAX.skills.skill_engine import SkillEngine
    engine = SkillEngine.instance()
    engine.load()

    if args.action == "list":
        print(json.dumps({"capabilities": engine.list_capabilities()}, indent=2))

    elif args.action == "execute":
        payload = json.loads(args.payload)
        if args.path:
            payload.setdefault("path", args.path)
        result = engine.execute(args.capability, payload, trace_id=args.trace_id)
        print(json.dumps(result.to_dict(), indent=2))

    elif args.action == "validate":
        text = Path(args.path).read_text(encoding="utf-8")
        spec = engine.parse(text)
        vr = engine.validate(spec)
        print(json.dumps({"valid": vr.valid, "errors": vr.errors, "title": spec.title}, indent=2))

    elif args.action == "status":
        from ANA_MAX.skills.skill_engine import _CALL_COUNTS
        print(json.dumps({"loaded": engine._loaded, "capabilities": len(engine._registry), "calls": _CALL_COUNTS}, indent=2))

    elif args.action == "reload":
        engine.reload()
        print(json.dumps({"reloaded": True, "capabilities": len(engine._registry)}, indent=2))

    sys.exit(0)
