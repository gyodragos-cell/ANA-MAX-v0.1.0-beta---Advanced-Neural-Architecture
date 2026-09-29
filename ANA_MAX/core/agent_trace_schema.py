"""Local ANA agent trace span schema.

This is intentionally small and local-first. It borrows the useful shape of
OpenTelemetry spans without requiring an OpenTelemetry backend or storing raw
private payloads.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "ana.agent_trace_span.v1"
ALLOWED_OPERATIONS = {
    "agent_run",
    "workflow",
    "tool_call",
    "context_pack",
    "verification",
    "audit",
    "checkpoint",
}
ALLOWED_STATUS = {"ok", "warn", "error", "blocked", "skipped"}
ALLOWED_RISK = {"low", "medium", "high"}
SENSITIVE_KEYS = {"password", "token", "key", "api_key", "secret", "authorization"}
REPO_ROOT = Path(__file__).resolve().parents[2]
ANA_ROOT = REPO_ROOT / "ANA_MAX"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_digest(value: Any) -> str:
    payload = json.dumps(redact(value), sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(secret in key_text.lower() for secret in SENSITIVE_KEYS):
                clean[key_text] = "********"
            else:
                clean[key_text] = redact(item)
        return clean
    if isinstance(value, list):
        return [redact(item) for item in value[:50]]
    if isinstance(value, str):
        text = value.replace(str(REPO_ROOT), "$WORKSPACE").replace(str(ANA_ROOT), "$ANA_MAX")
        text = re.sub(r"C:\\Users\\[^\\\s]+", r"C:\\Users\\<user>", text)
        return text[:500]
    return value


def make_span(
    *,
    run_id: str,
    operation: str,
    status: str,
    tool_name: str = "",
    trace_id: str = "",
    parent_span_id: str = "",
    input_payload: Any = None,
    result_payload: Any = None,
    evidence: Mapping[str, Any] | None = None,
    risk_level: str = "low",
    started_at: float | None = None,
    ended_at: float | None = None,
) -> dict[str, Any]:
    operation = operation.strip()
    status = status.strip()
    risk_level = risk_level.strip()
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"Unsupported trace operation: {operation}")
    if status not in ALLOWED_STATUS:
        raise ValueError(f"Unsupported trace status: {status}")
    if risk_level not in ALLOWED_RISK:
        raise ValueError(f"Unsupported risk level: {risk_level}")

    start = float(started_at if started_at is not None else time.time())
    end = float(ended_at if ended_at is not None else start)
    safe_evidence = redact(dict(evidence or {}))
    span = {
        "schema": SCHEMA,
        "run_id": str(run_id),
        "trace_id": str(trace_id or run_id),
        "span_id": uuid.uuid4().hex[:16],
        "parent_span_id": str(parent_span_id or ""),
        "operation": operation,
        "tool_name": str(tool_name or ""),
        "status": status,
        "risk_level": risk_level,
        "started_at": datetime.fromtimestamp(start, timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_at": datetime.fromtimestamp(end, timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_ms": max(0, round((end - start) * 1000, 3)),
        "input_digest": stable_digest(input_payload or {}),
        "result_digest": stable_digest(result_payload or {}),
        "evidence": safe_evidence,
        "raw_private_payloads": False,
    }
    span["span_digest"] = stable_digest({key: value for key, value in span.items() if key != "span_digest"})
    return span


def validate_span(span: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "schema",
        "run_id",
        "trace_id",
        "span_id",
        "operation",
        "status",
        "risk_level",
        "input_digest",
        "result_digest",
        "span_digest",
    ]
    for key in required:
        if not span.get(key):
            errors.append(f"missing:{key}")
    if span.get("schema") != SCHEMA:
        errors.append("invalid:schema")
    if span.get("operation") not in ALLOWED_OPERATIONS:
        errors.append("invalid:operation")
    if span.get("status") not in ALLOWED_STATUS:
        errors.append("invalid:status")
    if span.get("risk_level") not in ALLOWED_RISK:
        errors.append("invalid:risk_level")
    if span.get("raw_private_payloads") is not False:
        errors.append("invalid:raw_private_payloads")
    return errors
