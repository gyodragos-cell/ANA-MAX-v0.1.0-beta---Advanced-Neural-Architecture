from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from ana.config.loader import Config
from ana.core.error_model.errors import (
    BoundaryViolation,
    ErrorPacket,
    RoutingFailure,
    ValidationError,
    packet_from_exception,
)
from ana.core.event_bus.bus import EventBus
from ana.core.fallback.fallback import FallbackEngine, FallbackStep, RetryPolicy
from ana.core.fallback.rules import resolve_declarative_fallbacks
from ana.core.logging.logger import StructuredLogger
from ana.core.orchestrator.cooperation import CooperationEngine, RepairPlan
from ana.core.sandbox.sandbox import DeterministicSandbox, SandboxPolicy
from ana.tools.registry.registry import ToolSpec, ToolRegistry
from ana.tools.registry.skill_engine import SkillEngine
from ana.tools.router.router import ToolRouter


class RequestState(str, Enum):
    RECEIVED = "received"
    ROUTED = "routed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OSRequest:
    capability: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = "trace-0001"


@dataclass(frozen=True)
class OSResponse:
    ok: bool
    state: RequestState
    trace_id: str
    output: Mapping[str, Any] = field(default_factory=dict)
    error: ErrorPacket | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "state": self.state.value,
            "trace_id": self.trace_id,
            "output": dict(self.output),
            "error": self.error.to_dict() if self.error else None,
        }


class Orchestrator:
    def __init__(
        self,
        *,
        config: Config,
        event_bus: EventBus,
        registry: ToolRegistry,
        router: ToolRouter,
        fallback: FallbackEngine,
        sandbox: DeterministicSandbox,
        cooperation: CooperationEngine | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.registry = registry
        self.router = router
        self.fallback = fallback
        self.sandbox = sandbox
        self.cooperation = cooperation or CooperationEngine()
        self.logger = logger or StructuredLogger(self.event_bus, level=config.log_level)
        self._cancelled: set[str] = set()
        # Performance: Cache routing decisions (LRU with max 256 entries)
        self._routing_cache: dict[str, ToolSpec] = {}
        self._routing_cache_max_size = 256

    def cancel(self, trace_id: str) -> None:
        self._cancelled.add(trace_id)
        self.event_bus.publish(
            "orchestrator.cancelled",
            {"trace_id": trace_id},
            trace_id=trace_id,
        )

    def handle(self, request: OSRequest) -> OSResponse:
        fallback_attempted = False
        self_repair_attempted = False
        repair_plan: RepairPlan | None = None
        try:
            self._validate_request(request)
            self._fail_if_cancelled(request.trace_id)
            self._publish_state(RequestState.RECEIVED, request)
            try:
                # Performance: Use routing cache
                if request.capability in self._routing_cache:
                    tool = self._routing_cache[request.capability]
                else:
                    tool = self.router.route(request.capability, self.registry)
                    # Update cache with LRU eviction
                    if len(self._routing_cache) >= self._routing_cache_max_size:
                        # Simple FIFO eviction (could be improved to true LRU)
                        self._routing_cache.pop(next(iter(self._routing_cache)))
                    self._routing_cache[request.capability] = tool
            except RoutingFailure as exc:
                self_repair_attempted = True
                repair_plan = self.cooperation.self_repair.repair_missing_tool(
                    capability=request.capability,
                    registry=self.registry,
                    error=exc,
                )
                if not repair_plan.repaired or repair_plan.fallback is None:
                    raise
                fallback_tool = repair_plan.fallback
                tool = ToolSpec(
                    name=f"self_repair.{fallback_tool.name}",
                    capability=fallback_tool.capability,
                    handler=fallback_tool.handler,
                    priority=0,
                )
                self._publish_state(
                    RequestState.ROUTED,
                    request,
                    {
                        "tool": tool.name,
                        "self_repair": True,
                        "reason": repair_plan.reason,
                    },
                )
            else:
                self._publish_state(RequestState.ROUTED, request, {"tool": tool.name})
            self._fail_if_cancelled(request.trace_id)
            self._publish_state(RequestState.RUNNING, request, {"tool": tool.name})

            def run_primary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
                result = self.sandbox.execute(
                    request.capability,
                    tool.handler,
                    payload,
                    trace_id=request.trace_id,
                )
                return {"result": dict(result.output), "audit": dict(result.audit)}

            declared_fallbacks = resolve_declarative_fallbacks(request.capability, self.registry)
            fallback_sources = list(self.registry.fallbacks_for(request.capability)) + declared_fallbacks
            seen_names: set[str] = set()
            fallback_steps = []
            for step in fallback_sources:
                if step.name in seen_names:
                    continue
                seen_names.add(step.name)
                if repair_plan is not None and step.name == repair_plan.fallback.name:
                    continue
                # Skip fallback specs without handlers
                if step.handler is None:
                    continue
                fallback_steps.append(
                    FallbackStep(
                        name=step.name,
                        handler=self._sandboxed_handler(
                            request.capability,
                            step.handler,
                            request.trace_id,
                        ),
                    )
                )
            fallback_attempted = bool(fallback_steps) or repair_plan is not None

            output = self.fallback.run(
                run_primary,
                request.payload,
                fallbacks=fallback_steps,
            )
            output.setdefault(
                "cooperation",
                self.cooperation.success_context(repaired=repair_plan),
            )
            self._publish_state(RequestState.COMPLETED, request, {"tool": tool.name})
            return OSResponse(
                ok=True,
                state=RequestState.COMPLETED,
                trace_id=request.trace_id,
                output=output,
            )
        except Exception as exc:
            packet = packet_from_exception(exc, source="orchestrator")
            packet = self.cooperation.enrich_packet(
                packet,
                fallback_attempted=fallback_attempted,
                self_repair_attempted=self_repair_attempted,
            )
            self._publish_state(
                RequestState.FAILED,
                request,
                {"error": packet.to_dict()},
            )
            return OSResponse(
                ok=False,
                state=RequestState.FAILED,
                trace_id=request.trace_id,
                output={"cooperation": self.cooperation.failure_context(packet)},
                error=packet,
            )

    def _validate_request(self, request: OSRequest) -> None:
        if not request.capability:
            raise ValidationError("capability is required", source="orchestrator")
        if "." in request.capability:
            service = request.capability.split(".", 1)[0]
            if service not in self.config.services:
                raise RoutingFailure(
                    "service is not enabled",
                    source="orchestrator",
                    details={"service": service},
                )

    def _fail_if_cancelled(self, trace_id: str) -> None:
        if trace_id in self._cancelled:
            raise BoundaryViolation(
                "request was cancelled",
                source="orchestrator",
                details={"trace_id": trace_id},
            )

    def _publish_state(
        self,
        state: RequestState,
        request: OSRequest,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        event_payload = {"capability": request.capability} | dict(payload or {})
        self.event_bus.publish(
            f"orchestrator.{state.value}",
            event_payload,
            trace_id=request.trace_id,
        )
        self.logger.info(
            f"orchestrator.{state.value}",
            event_payload,
            trace_id=request.trace_id,
        )

    def _sandboxed_handler(self, capability, handler, trace_id):
        def run(payload: Mapping[str, Any]) -> Mapping[str, Any]:
            result = self.sandbox.execute(
                capability,
                handler,
                payload,
                trace_id=trace_id,
            )
            return {"result": dict(result.output), "audit": dict(result.audit)}

        return run


class ANAMaxOS:
    def __init__(
        self,
        *,
        config: Config,
        registry: ToolRegistry,
        event_bus: EventBus | None = None,
        cooperation: CooperationEngine | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus or EventBus(
            replay_limit=config.event_bus_replay_limit
        )
        self.logger = StructuredLogger(self.event_bus, level=config.log_level)
        self.registry = registry
        self.skill_engine = SkillEngine()
        self.skill_engine.load_skills(
            self._skill_root(),
            mapping=self.config.skills,
        )
        self.skill_engine.register_skills(self.registry)
        self.router = ToolRouter()
        self.fallback = FallbackEngine(RetryPolicy(config.max_attempts))
        self.cooperation = cooperation or CooperationEngine()
        self.sandbox = DeterministicSandbox(
            SandboxPolicy(
                allowed_capabilities=frozenset(self.registry.all_capabilities()),
                max_input_keys=config.sandbox_max_input_keys,
                allow_external_effects=config.allow_external_effects,
            )
        )
        self.orchestrator = Orchestrator(
            config=config,
            event_bus=self.event_bus,
            registry=self.registry,
            router=self.router,
            fallback=self.fallback,
            sandbox=self.sandbox,
            cooperation=self.cooperation,
            logger=self.logger,
        )

    def _skill_root(self) -> Path:
        return Path(__file__).resolve().parents[2] / "skills" / "skills"

    def execute(
        self,
        capability: str,
        payload: Mapping[str, Any] | None = None,
        *,
        trace_id: str = "trace-0001",
    ) -> OSResponse:
        return self.orchestrator.handle(
            OSRequest(
                capability=capability,
                payload=dict(payload or {}),
                trace_id=trace_id,
            )
        )
