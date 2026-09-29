from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ana.core.error_model.errors import ANAError, FatalANAError, packet_from_exception


FallbackCallable = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_base: float = 0.1
    backoff_max: float = 5.0
    exponential_backoff: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_base < 0:
            raise ValueError("backoff_base must be non-negative")
        if self.backoff_max < self.backoff_base:
            raise ValueError("backoff_max must be >= backoff_base")

    def get_backoff(self, attempt: int) -> float:
        if not self.exponential_backoff:
            return self.backoff_base
        backoff = self.backoff_base * (2 ** (attempt - 1))
        return min(backoff, self.backoff_max)


@dataclass(frozen=True)
class FallbackStep:
    name: str
    handler: FallbackCallable
    timeout: float | None = None


class FallbackEngine:
    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self.policy = policy or RetryPolicy()

    def run(
        self,
        primary: FallbackCallable,
        payload: Mapping[str, Any],
        *,
        fallbacks: list[FallbackStep] | None = None,
    ) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        steps = [FallbackStep("primary", primary)] + list(fallbacks or [])
        for step in steps:
            for attempt in range(1, self.policy.max_attempts + 1):
                try:
                    if attempt > 1:
                        backoff = self.policy.get_backoff(attempt)
                        time.sleep(backoff)
                    result = dict(step.handler(dict(payload)))
                    result.setdefault("fallback", step.name != "primary")
                    result.setdefault("step", step.name)
                    result.setdefault("attempt", attempt)
                    if errors:
                        result["errors"] = errors
                    return result
                except Exception as exc:
                    packet = packet_from_exception(exc, source=f"fallback.{step.name}")
                    error_entry = packet.to_dict() | {"attempt": attempt}
                    errors.append(error_entry)
                    if isinstance(exc, ANAError) and not exc.recoverable:
                        raise FatalANAError(
                            f"non-recoverable error in step '{step.name}'",
                            source="fallback",
                            details={"step": step.name, "error": error_entry},
                        )
        raise FatalANAError(
            "all fallback steps failed",
            source="fallback",
            details={"errors": errors, "total_steps": len(steps)},
        )
