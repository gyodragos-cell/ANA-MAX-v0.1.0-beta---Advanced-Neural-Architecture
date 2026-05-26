"""ANA MAX v22 scenario simulator scaffolding.

The scenario simulator provides deterministic fake workflows for validating
router, context, execution, and safety behavior without touching real user data.
This first version is intentionally small and in-memory so it can become a CI
fixture later without depending on a live desktop or MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


DEFAULT_SCENARIOS = {
    "dirty_git_tree": {
        "candidate_tools": ("git_operations", "grep_file", "workspace_situational_awareness"),
        "expected_signal": "dirty_worktree",
    },
    "failed_test_diagnosis": {
        "candidate_tools": ("terminal", "error_radar", "file_operations"),
        "expected_signal": "test_failure",
    },
    "ui_error_detection": {
        "candidate_tools": ("foreground_ui_snapshot", "ocr_tool", "desktop_capture"),
        "expected_signal": "visible_error",
    },
    "public_release_hygiene": {
        "candidate_tools": ("security_audit", "grep_file", "project_navigator"),
        "expected_signal": "release_boundary_check",
    },
    "tool_timeout_fallback": {
        "candidate_tools": ("web_search", "web_fetch", "grep_file"),
        "expected_signal": "timeout_then_fallback",
    },
    "invalid_tool_output": {
        "candidate_tools": ("invalid_tool_output", "error_radar"),
        "expected_signal": "normalization_required",
    },
    "slow_tool_response": {
        "candidate_tools": ("slow_tool_response", "grep_file"),
        "expected_signal": "latency_budget_pressure",
    },
    "chained_fallback": {
        "candidate_tools": ("primary_fake_tool", "secondary_fake_tool", "grep_file"),
        "expected_signal": "fallback_chain_review",
    },
    "partial_failure_chain": {
        "candidate_tools": ("partial_failure_tool", "grep_file"),
        "expected_signal": "partial_failure_then_recover",
    },
    "ambiguous_task_routing": {
        "candidate_tools": ("workspace_situational_awareness", "project_navigator", "grep_file"),
        "expected_signal": "needs_clarifying_context",
    },
}


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for scenario records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ScenarioResult:
    """Result payload returned by a simulated scenario run."""

    name: str
    success: bool
    context: Mapping[str, Any]
    router_decision: Mapping[str, Any]
    tool_result: Mapping[str, Any]
    created_at: str = field(default_factory=_utc_now)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe scenario result."""
        return {
            "name": self.name,
            "success": self.success,
            "context": dict(self.context),
            "router_decision": dict(self.router_decision),
            "tool_result": dict(self.tool_result),
            "created_at": self.created_at,
            "notes": list(self.notes),
        }


class ScenarioSimulator:
    """Run fake v22 scenarios without executing real tools."""

    def __init__(self, fake_tools: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        """Initialize scenario definitions and fake tool outputs."""
        self.scenarios = dict(DEFAULT_SCENARIOS)
        self.fake_tools = dict(fake_tools or {})
        self.run_history: list[ScenarioResult] = []
        # TODO(v22): add deterministic replay seeds and trace snapshots.
        # TODO(v22): export scenario coverage metrics to observability.
        # TODO(v22): package scenario bundles for CI.

    def run_scenario(self, name: str, task_envelope: Any) -> ScenarioResult:
        """Run a named fake scenario for a task envelope."""
        if name not in self.scenarios:
            raise ValueError(f"unknown scenario: {name}")

        scenario = self.scenarios[name]
        candidate_tools = tuple(scenario.get("candidate_tools", ()))
        context = self._simulate_context(task_envelope)
        router_decision = self._simulate_router_decision(candidate_tools)
        selected_tool = str(router_decision.get("selected_tool") or "")
        tool_result = self._simulate_tool_result(selected_tool)
        result = ScenarioResult(
            name=name,
            success=bool(tool_result.get("success", False)),
            context=context,
            router_decision=router_decision,
            tool_result=tool_result,
            notes=(f"expected_signal={scenario.get('expected_signal', 'unknown')}",),
        )
        self.run_history.append(result)
        # TODO(v22): record scenario run events through Observability.
        return result

    def _simulate_context(self, task_envelope: Any) -> dict[str, Any]:
        """Return compact fake context for a scenario run."""
        task = self._read_value(task_envelope, "task", "unspecified task")
        workspace = self._read_value(task_envelope, "workspace", "")
        return {
            "summary": f"simulated context for: {task}",
            "workspace": workspace,
            "facts": ["scenario simulator active", "no real tools executed"],
            "blind_spots": ["fake context only", "no live workspace inspection"],
            "confidence": 0.5,
            "created_at": _utc_now(),
        }

    def _simulate_tool_result(self, tool_name: str) -> dict[str, Any]:
        """Return a fake result for a selected tool name."""
        if not tool_name:
            return {
                "tool": None,
                "success": False,
                "summary": "no tool selected",
                "output_bytes": 0,
            }
        if tool_name == "invalid_tool_output":
            return {
                "tool": tool_name,
                "success": False,
                "summary": "fake invalid output shape detected",
                "output_bytes": 0,
            }
        if tool_name == "slow_tool_response":
            return {
                "tool": tool_name,
                "success": True,
                "summary": "fake slow response within simulated timeout budget",
                "latency_ms": 2500,
                "output_bytes": 128,
            }
        if tool_name == "primary_fake_tool":
            return {
                "tool": tool_name,
                "success": False,
                "summary": "fake primary failed; fallback would be considered",
                "next_fallback": "secondary_fake_tool",
                "output_bytes": 64,
            }
        if tool_name == "partial_failure_tool":
            return {
                "tool": tool_name,
                "success": False,
                "summary": "fake partial failure with recoverable output",
                "recoverable": True,
                "output_bytes": 96,
            }
        if tool_name in self.fake_tools:
            result = dict(self.fake_tools[tool_name])
            result.setdefault("tool", tool_name)
            result.setdefault("success", True)
            return result
        return {
            "tool": tool_name,
            "success": True,
            "summary": f"fake result from {tool_name}",
            "output_bytes": len(tool_name.encode("utf-8")),
        }

    def _simulate_router_decision(self, candidate_tools: Sequence[str]) -> dict[str, Any]:
        """Return a deterministic fake router decision for candidates."""
        candidates = [str(tool).strip() for tool in candidate_tools if str(tool).strip()]
        if not candidates:
            return {
                "selected_tool": None,
                "candidates": [],
                "rationale": "no fake candidates provided",
            }
        selected = candidates[0]
        return {
            "selected_tool": selected,
            "candidates": candidates,
            "rationale": f"selected first deterministic candidate: {selected}",
        }

    @staticmethod
    def _read_value(obj: Any, name: str, default: Any = None) -> Any:
        """Read a value from a mapping or TaskEnvelope-like object."""
        if isinstance(obj, Mapping):
            return obj.get(name, default)
        return getattr(obj, name, default)
