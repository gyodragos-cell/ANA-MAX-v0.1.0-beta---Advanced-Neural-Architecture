from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ana.core.error_model.errors import ErrorPacket, RoutingFailure
from ana.core.fallback.rules import resolve_declarative_fallbacks
from ana.tools.registry.registry import FallbackToolSpec, ToolRegistry


OS_V2_DISCIPLINES = (
    "determinism",
    "single_source_of_truth",
    "zero_guessing",
    "strict_boundaries",
    "fail_fast",
    "observability",
)


@dataclass(frozen=True)
class CooperationPolicy:
    cooperative: bool = True
    explain_instead_of_refuse: bool = True
    fallback_on_blocker: bool = True
    self_repair_missing_pieces: bool = True
    zero_unnecessary_blockers: bool = True
    disciplines: tuple[str, ...] = OS_V2_DISCIPLINES


@dataclass(frozen=True)
class RepairPlan:
    repaired: bool
    reason: str
    fallback: FallbackToolSpec | None = None


class SelfRepairEngine:
    def repair_missing_tool(
        self,
        *,
        capability: str,
        registry: ToolRegistry,
        error: RoutingFailure,
    ) -> RepairPlan:
        fallbacks = registry.fallbacks_for(capability)
        if not fallbacks:
            fallbacks = resolve_declarative_fallbacks(capability, registry)
        if not fallbacks:
            return RepairPlan(
                repaired=False,
                reason="No deterministic fallback is registered for this capability.",
            )
        return RepairPlan(
            repaired=True,
            reason="Primary tool is missing; using a deterministic fallback based on registered fallback handlers or declarative rules.",
            fallback=fallbacks[0],
        )


class CooperationEngine:
    def __init__(
        self,
        policy: CooperationPolicy | None = None,
        self_repair: SelfRepairEngine | None = None,
    ) -> None:
        self.policy = policy or CooperationPolicy()
        self.self_repair = self_repair or SelfRepairEngine()

    def success_context(
        self,
        *,
        repaired: RepairPlan | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "cooperative": self.policy.cooperative,
            "disciplines": list(self.policy.disciplines),
            "zero_guessing": True,
        }
        if repaired is not None:
            context["self_repair"] = {
                "repaired": repaired.repaired,
                "reason": repaired.reason,
                "fallback": repaired.fallback.name if repaired.fallback else None,
            }
        return context

    def failure_context(self, packet: ErrorPacket) -> dict[str, Any]:
        return {
            "cooperative": self.policy.cooperative,
            "explanation": self._explain(packet),
            "next_action": self._next_action(packet),
            "fallback_attempted": packet.details.get("fallback_attempted", False),
            "self_repair_attempted": packet.details.get("self_repair_attempted", False),
            "disciplines": list(self.policy.disciplines),
            "zero_guessing": True,
        }

    def enrich_packet(
        self,
        packet: ErrorPacket,
        *,
        fallback_attempted: bool,
        self_repair_attempted: bool,
    ) -> ErrorPacket:
        details = dict(packet.details)
        details.setdefault("fallback_attempted", fallback_attempted)
        details.setdefault("self_repair_attempted", self_repair_attempted)
        details.setdefault("cooperative_explanation", self._explain(packet))
        details.setdefault("next_action", self._next_action(packet))
        details.setdefault("disciplines", list(self.policy.disciplines))
        return ErrorPacket(
            code=packet.code,
            message=packet.message,
            severity=packet.severity,
            recoverable=packet.recoverable,
            source=packet.source,
            details=details,
        )

    def _explain(self, packet: ErrorPacket) -> str:
        if packet.code == "ROUTING_FAILURE":
            return (
                "ANA could not route this capability with registered deterministic data. "
                "No guess was made; register a primary tool or a fallback for the capability."
            )
        if packet.recoverable:
            return (
                "ANA hit a recoverable blocker and preserved the structured error so the "
                "caller can continue with a registered fallback or corrected input."
            )
        return (
            "ANA stopped this request because a fatal boundary or sandbox rule was hit. "
            "The explanation is returned instead of a silent refusal."
        )

    def _next_action(self, packet: ErrorPacket) -> str:
        if packet.code == "ROUTING_FAILURE":
            return "Register ToolSpec or FallbackToolSpec for the requested capability."
        if packet.code == "VALIDATION_ERROR":
            return "Correct the payload and retry with the same capability."
        if packet.code in {"BOUNDARY_VIOLATION", "SANDBOX_VIOLATION"}:
            return "Change the capability, root, or sandbox policy before retrying."
        return "Inspect error details and retry with a deterministic fallback."
