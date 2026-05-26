"""ANA MAX v22 runtime configuration scaffolding.

RuntimeConfig centralizes the first wave of v22 defaults so the orchestrator,
router, execution layer, and observability layer do not each invent their own
policy constants. This module is intentionally static for now; loading and
adaptive configuration belong to later phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SUPPORTED_MODES = {"dev", "release"}
__all__ = ["RuntimeConfig", "SUPPORTED_MODES"]


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for default runtime state."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class RuntimeConfig:
    """Provide static ANA MAX v22 runtime defaults for a mode."""

    mode: str = "dev"
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Validate the selected runtime mode."""
        normalized = (self.mode or "dev").strip().lower()
        if normalized not in SUPPORTED_MODES:
            raise ValueError(f"unsupported runtime mode: {self.mode}")
        object.__setattr__(self, "mode", normalized)
        # TODO(v22): load config from file after scaffold modules stabilize.
        # TODO(v22): add environment variable overrides for CI and lab sessions.
        # TODO(v22): support encrypted config storage for sensitive settings.
        # TODO(v22): add per-user adaptive config once observability matures.

    def get_safety_envelope(self) -> dict[str, Any]:
        """Return default safety policy values for the current mode."""
        base = {
            "mode": self.mode,
            "allow_mutation": False,
            "requires_confirmation": True,
            "allow_public_release_writes": False,
            "allow_desktop_control": False,
            "allow_network_actions": False,
        }
        if self.mode == "dev":
            base.update(
                {
                    "allow_dev_workspace_writes": True,
                    "allow_fake_tool_execution": True,
                }
            )
        else:
            base.update(
                {
                    "allow_dev_workspace_writes": False,
                    "allow_fake_tool_execution": False,
                }
            )
        return base

    def get_output_limits(self) -> dict[str, int]:
        """Return default byte limits for execution output handling."""
        if self.mode == "release":
            return {
                "max_text_bytes": 2048,
                "summary_bytes": 384,
                "max_events_kept": 100,
            }
        return {
            "max_text_bytes": 4096,
            "summary_bytes": 512,
            "max_events_kept": 250,
        }

    def get_scoring_defaults(self) -> dict[str, float]:
        """Return default router scoring weights."""
        return {
            "relevance": 0.4,
            "risk": -0.25,
            "cost": -0.15,
            "context_fit": 0.15,
            "latency": -0.05,
        }

    def get_fallback_defaults(self) -> dict[str, Any]:
        """Return default execution and routing fallback policies."""
        return {
            "enabled": True,
            "max_attempts": 1 if self.mode == "release" else 2,
            "candidate_tools": (
                "workspace_situational_awareness",
                "grep_file",
                "file_operations",
            ),
            "stop_on_policy_failure": True,
        }

    def get_runtime_state_defaults(self) -> dict[str, Any]:
        """Return initial runtime state values for ANAMaxRuntime."""
        return {
            "mode": self.mode,
            "created_at": self.created_at,
            "last_stage": None,
            "runs": 0,
            "streaming_enabled": False,
            "multi_step_enabled": False,
            "adaptive_routing_enabled": False,
        }
