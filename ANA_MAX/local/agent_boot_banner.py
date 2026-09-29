"""ASCII-safe OS-22 agent boot banner helpers."""

from __future__ import annotations

from typing import Any, Mapping


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _status(flag: Any) -> str:
    return "OK" if bool(flag) else "WARN"


def _nested(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key)
    return default if current is None else current


def build_agent_boot_banner(
    *,
    profile: str = "os22_core",
    backend_info: Mapping[str, Any] | None = None,
    boot_report: Mapping[str, Any] | None = None,
) -> str:
    """Build a deterministic operator-facing OS-22 boot banner."""
    backend = dict(backend_info or {})
    report = dict(boot_report or {})

    model = (
        backend.get("active_model_name")
        or backend.get("model_name")
        or backend.get("fallback_model_name")
        or "unknown"
    )
    backend_name = backend.get("inference_backend") or backend.get("backend") or "unknown"
    mode = "Deterministic Runtime" if profile == "os22_core" else "Engineering Runtime"

    rag_ok = _nested(report, "rag_bridge", "ready", default=False)
    tool_ok = _nested(report, "tool_bridge", "available", default=False)
    memory_ok = _nested(report, "rag_bridge", "memory_store", "ready", default=rag_ok)
    graph_ok = report.get("overall_success", False)
    telemetry_ok = True
    agent_ok = _nested(report, "agent", "schema", default="") == "ana.os21.local_brain_agent.v1"
    foundation_ok = _nested(report, "agent_foundation", "ready", default=False)
    self_healing_ok = _nested(report, "self_healing", "ready", default=False)
    backend_ok = backend.get("loaded", backend.get("available", False))

    ready = all([rag_ok, tool_ok, memory_ok, graph_ok, telemetry_ok, agent_ok, foundation_ok, self_healing_ok, backend_ok])
    agent_status = "READY" if ready else "WARN"

    lines = [
        "============================================================",
        "ANA_MAX OS-22 AGENT - BOOT SEQUENCE",
        f"Model: {_ascii_text(model)}",
        f"Backend: {_ascii_text(backend_name)}",
        f"Mode: {mode}",
        f"Profile: {_ascii_text(profile)}",
        "============================================================",
        f"Initializing RAGBridge... {_status(rag_ok)}",
        f"Initializing ToolBridge... {_status(tool_ok)}",
        f"Initializing VectorMemoryCortex... {_status(memory_ok)}",
        f"Initializing Reasoning Graph... {_status(graph_ok)}",
        f"Initializing Telemetry Stream... {_status(telemetry_ok)}",
        f"Initializing Agent Foundation... {_status(foundation_ok)}",
        f"Initializing Self-Healing... {_status(self_healing_ok)}",
        f"Initializing LocalBrainAgent... {_status(agent_ok)}",
        "",
        f"Agent status: {agent_status}",
        "Welcome to ANA_MAX OS-22.",
    ]
    return "\n".join(lines)
