from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ErrorPacket:
    code: str
    message: str
    severity: str
    recoverable: bool
    source: str
    details: Mapping[str, Any]
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "recoverable": self.recoverable,
            "source": self.source,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }


class ANAError(Exception):
    code = "ANA_ERROR"
    severity = "error"
    recoverable = False

    def __init__(
        self,
        message: str,
        *,
        source: str = "unknown",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.source = source
        self.details = dict(details or {})

    def packet(self) -> ErrorPacket:
        from datetime import datetime, timezone
        return ErrorPacket(
            code=self.code,
            message=self.message,
            severity=self.severity,
            recoverable=self.recoverable,
            source=self.source,
            details=self.details,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class RecoverableANAError(ANAError):
    code = "ANA_RECOVERABLE"
    recoverable = True


class FatalANAError(ANAError):
    code = "ANA_FATAL"
    severity = "fatal"
    recoverable = False


class ValidationError(RecoverableANAError):
    code = "VALIDATION_ERROR"


class BoundaryViolation(FatalANAError):
    code = "BOUNDARY_VIOLATION"


class TimeoutFailure(RecoverableANAError):
    code = "TIMEOUT_FAILURE"


class RoutingFailure(RecoverableANAError):
    code = "ROUTING_FAILURE"


class SandboxViolation(FatalANAError):
    code = "SANDBOX_VIOLATION"


class SecurityViolation(FatalANAError):
    code = "SECURITY_VIOLATION"
    severity = "critical"


class ResourceExhaustedError(RecoverableANAError):
    code = "RESOURCE_EXHAUSTED"


class ConfigurationError(RecoverableANAError):
    code = "CONFIGURATION_ERROR"


def packet_from_exception(exc: Exception, source: str = "unknown") -> ErrorPacket:
    if isinstance(exc, ANAError):
        return exc.packet()
    from datetime import datetime, timezone
    return ErrorPacket(
        code="UNHANDLED_EXCEPTION",
        message=str(exc),
        severity="fatal",
        recoverable=False,
        source=source,
        details={"type": type(exc).__name__},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
