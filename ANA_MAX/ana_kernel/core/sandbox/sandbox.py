from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from ana.core.error_model.errors import SandboxViolation, ValidationError


SandboxCallable = Callable[[Mapping[str, Any]], Mapping[str, Any]]


# Security: Patterns for detecting dangerous inputs
_PATH_TRAVERSAL_PATTERN = re.compile(r'\.\./|\.\.\|\\')
_SHELL_INJECTION_PATTERN = re.compile(r'[|&;`$()<>]')


@dataclass(frozen=True)
class SandboxPolicy:
    allowed_capabilities: frozenset[str]
    max_input_keys: int = 32
    allow_external_effects: bool = False
    max_string_length: int = 10000  # Prevent DoS via large strings
    validate_paths: bool = True  # Enable path traversal detection
    validate_commands: bool = True  # Enable shell injection detection


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    output: Mapping[str, Any]
    audit: Mapping[str, Any] = field(default_factory=dict)


class DeterministicSandbox:
    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    def execute(
        self,
        capability: str,
        handler: SandboxCallable,
        payload: Mapping[str, Any] | None = None,
        *,
        trace_id: str,
    ) -> SandboxResult:
        if capability not in self.policy.allowed_capabilities:
            raise SandboxViolation(
                f"capability is not allowed: {capability}",
                source="sandbox",
                details={"capability": capability},
            )

        safe_payload = dict(payload or {})

        # Validate input key count
        if len(safe_payload) > self.policy.max_input_keys:
            raise ValidationError(
                "payload exceeds sandbox input key limit",
                source="sandbox",
                details={"limit": self.policy.max_input_keys},
            )

        # Security: Validate and sanitize payload
        safe_payload = self._validate_and_sanitize_payload(safe_payload)

        output = dict(handler(safe_payload))
        return SandboxResult(
            ok=True,
            output=output,
            audit={
                "trace_id": trace_id,
                "capability": capability,
                "external_effects": self.policy.allow_external_effects,
                "sanitized": True,
            },
        )

    def _validate_and_sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize payload to prevent injection attacks."""
        sanitized = {}
        for key, value in payload.items():
            # Validate key
            if not isinstance(key, str):
                raise ValidationError(
                    "payload keys must be strings",
                    source="sandbox",
                    details={"key_type": type(key).__name__},
                )

            # Sanitize value based on type
            if isinstance(value, str):
                # Check for path traversal
                if self.policy.validate_paths and _PATH_TRAVERSAL_PATTERN.search(value):
                    raise SandboxViolation(
                        f"potential path traversal detected in key '{key}'",
                        source="sandbox",
                        details={"key": key},
                    )
                # Check for shell injection
                if self.policy.validate_commands and _SHELL_INJECTION_PATTERN.search(value):
                    raise SandboxViolation(
                        f"potential shell injection detected in key '{key}'",
                        source="sandbox",
                        details={"key": key},
                    )
                # Truncate to prevent DoS
                value = value[:self.policy.max_string_length]
                # Remove null bytes
                value = value.replace("\x00", "")
                sanitized[key] = value
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_value(v) for v in value
                ]
            elif isinstance(value, dict):
                sanitized[key] = self._validate_and_sanitize_payload(value)
            elif value is None:
                sanitized[key] = None
            else:
                # Convert unknown types to string
                sanitized[key] = str(value)[:self.policy.max_string_length]

        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize a single value."""
        if isinstance(value, str):
            value = value[:self.policy.max_string_length]
            value = value.replace("\x00", "")
            return value
        elif isinstance(value, (int, float, bool)):
            return value
        elif isinstance(value, dict):
            return self._validate_and_sanitize_payload(value)
        elif value is None:
            return None
        else:
            return str(value)[:self.policy.max_string_length]
