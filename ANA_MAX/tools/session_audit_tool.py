"""Session audit and trust-score report tool."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.event_stream import get_event_stream
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.conversation_audit import summarize_conversation_audit


ANA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ANA_ROOT.parent
DEFAULT_AUDIT_DIR = ANA_ROOT / "dev_artifacts" / "audit"
DEFAULT_REPORT_DIR = ANA_ROOT / "dev_artifacts" / "reports"
IDENTITY_CHECK_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_identity_surface_check.py"
SENSITIVE_KEYS = {"password", "token", "key", "api_key", "secret", "authorization"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            key_text = str(key)
            if any(secret in key_text.lower() for secret in SENSITIVE_KEYS):
                clean[key_text] = "********"
            else:
                clean[key_text] = _redact(item)
        return clean
    if isinstance(value, list):
        return [_redact(item) for item in value[:50]]
    if isinstance(value, str):
        text = value.replace(str(REPO_ROOT), "$WORKSPACE").replace(str(ANA_ROOT), "$ANA_MAX")
        text = re.sub(r"C:\\Users\\[^\\\s]+", r"C:\\Users\\<user>", text)
        return text[:500]
    return value


def _compact_event(event: dict[str, Any], run_id: str, prev_hash: str, index: int) -> tuple[dict[str, Any], str]:
    data = _redact(event.get("data") or {})
    metadata = _redact(event.get("metadata") or {})
    source = str(event.get("source") or "unknown")
    args = data.get("args") if isinstance(data, dict) else {}
    status = data.get("status") if isinstance(data, dict) else None

    dispatch = {
        "step_id": index,
        "event_type": event.get("event_type"),
        "tool": data.get("tool") if isinstance(data, dict) else source,
        "source": source,
        "status": status or ("success" if event.get("success") else "error"),
        "duration_sec": event.get("duration"),
    }
    approval = "confirmed" if isinstance(args, dict) and str(args.get("confirm", "")).lower() in {"true", "1"} else "not_required_or_not_seen"
    replay = {
        "step_id": index,
        "tool_call": {
            "tool": dispatch["tool"] or source,
            "args_hash": _sha256(args or {}),
        },
        "result_hash": _sha256({
            "status": dispatch["status"],
            "error": data.get("error") if isinstance(data, dict) else None,
            "source": source,
        }),
        "files_touched": _extract_files(args if isinstance(args, dict) else {}),
        "test_output_summary": _summarize_test_output(data),
        "ui_snapshot_digest": _ui_digest(event, data),
    }
    payload = {
        "event_id": event.get("id"),
        "run_id": run_id,
        "actor": "ana_local_agent",
        "policy": {
            "mode": "local-dev",
            "raw_private_payloads": False,
            "redacted": True,
        },
        "approval": approval,
        "dispatch": dispatch,
        "replay": replay,
        "ts": datetime.fromtimestamp(float(event.get("timestamp") or time.time()), timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadata": metadata,
    }
    payload_hash = _sha256(payload)
    chain_hash = _sha256({"prev_hash": prev_hash, "payload_hash": payload_hash})
    payload["integrity"] = {
        "payload_hash": payload_hash,
        "prev_hash": prev_hash,
        "chain_hash": chain_hash,
    }
    return payload, chain_hash


def _extract_files(args: dict[str, Any]) -> list[str]:
    files = []
    for key, value in args.items():
        if key.lower() not in {"path", "file", "file_path", "target", "source", "destination"}:
            continue
        text = str(value)
        if len(text) > 260:
            continue
        text = text.replace(str(REPO_ROOT), "").replace("\\", "/").strip("/")
        if text and not text.startswith("$"):
            files.append(text)
    return sorted(set(files))[:12]


def _summarize_test_output(data: Any) -> str | None:
    text = json.dumps(data, ensure_ascii=True, default=str)
    if "passed" in text.lower() or "failed" in text.lower() or "pytest" in text.lower():
        return text[:240]
    return None


def _ui_digest(event: dict[str, Any], data: Any) -> str | None:
    if event.get("source") not in {"foreground_ui_snapshot", "desktop_capture", "vision_region_capture"}:
        return None
    return _sha256(data)


def _latest_report(pattern: str, report_dir: Path | None = None) -> Path | None:
    report_dir = report_dir or DEFAULT_REPORT_DIR
    try:
        matches = sorted(report_dir.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        return None
    return matches[0] if matches else None


def _trace_summary(report_dir: Path | None = None) -> dict[str, Any] | None:
    report_dir = report_dir or DEFAULT_REPORT_DIR
    path = _latest_report("trace_report_*.json", report_dir=report_dir)
    if not path:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema": "ana.session_trace_summary.v1",
            "available": False,
            "status": "unreadable",
            "file": path.name,
        }
    if payload.get("schema") != "ana.trace_report.v1":
        return {
            "schema": "ana.session_trace_summary.v1",
            "available": False,
            "status": "invalid_schema",
            "file": path.name,
        }
    return {
        "schema": "ana.session_trace_summary.v1",
        "available": True,
        "status": "PASS" if payload.get("ok") else "FAIL",
        "file": path.name,
        "run_id": payload.get("run_id"),
        "autonomy_status": payload.get("autonomy_status"),
        "trust_score": payload.get("trust_score"),
        "steps": payload.get("steps"),
        "spans": payload.get("spans"),
        "aligned": bool(payload.get("aligned")),
        "operations": payload.get("operations") or {},
        "span_errors": len(payload.get("span_errors") or []),
        "raw_private_payloads": False,
    }


def _conversation_audit_summary(hours: int = 1, limit: int = 80) -> dict[str, Any]:
    try:
        summary = summarize_conversation_audit(hours=hours, limit=limit)
    except Exception as exc:
        return {
            "schema": "ana.conversation_audit.summary.v1",
            "status": "UNKNOWN",
            "available": False,
            "events": 0,
            "spoken_events": 0,
            "sensitive_skipped": 0,
            "sources": {},
            "message": str(exc)[:160],
        }
    return {
        "schema": summary.get("schema"),
        "status": summary.get("status"),
        "available": bool(summary.get("events")),
        "path": _redact(summary.get("path")),
        "hours": summary.get("hours"),
        "events": summary.get("events"),
        "spoken_events": summary.get("spoken_events"),
        "sensitive_skipped": summary.get("sensitive_skipped"),
        "sources": summary.get("sources") or {},
        "message": summary.get("message"),
    }


def _identity_surface_summary() -> dict[str, Any]:
    if not IDENTITY_CHECK_SCRIPT.exists():
        return {
            "schema": "ana.session_identity_surface.v1",
            "available": False,
            "status": "UNKNOWN",
            "reason": "identity_check_script_missing",
        }
    try:
        spec = importlib.util.spec_from_file_location("ana_identity_surface_check_for_audit", IDENTITY_CHECK_SCRIPT)
        if not spec or not spec.loader:
            raise RuntimeError("identity_check_load_failed")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.build_report()
    except Exception as exc:
        return {
            "schema": "ana.session_identity_surface.v1",
            "available": False,
            "status": "UNKNOWN",
            "reason": str(exc)[:160],
        }
    return {
        "schema": "ana.session_identity_surface.v1",
        "available": True,
        "status": report.get("status"),
        "files_checked": report.get("files_checked"),
        "violations": len(report.get("violations") or []),
        "missing_required": len(report.get("missing_required") or []),
        "raw_private_payloads": False,
    }


def _score(
    events: list[dict[str, Any]],
    identity_surface: dict[str, Any] | None = None,
    conversation_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = max(1, len(events))
    successes = [event for event in events if bool(event.get("success"))]
    sources = {str(event.get("source") or "") for event in events if event.get("success")}

    has_pack = "code_context_pack" in sources
    has_ui = "foreground_ui_snapshot" in sources or has_pack
    has_code_map = has_pack or any("code_map" in json.dumps(event.get("data", {}), default=str) for event in events)
    context = 1.0 if has_pack else 0.75 if has_ui and has_code_map else 0.5 if has_ui or has_code_map else 0.0

    schema_errors = 0
    for event in events:
        data = event.get("data") or {}
        error = str(data.get("error") if isinstance(data, dict) else "")
        if error.startswith(("Missing required parameter", "Invalid value", "Invalid type")):
            schema_errors += 1
    schema_validated = max(0.0, 1.0 - (schema_errors / total))

    has_error_radar = "error_radar" in sources
    has_health = "tool_healthcheck" in sources or "ana_health_check" in sources
    recent_failures = total - len(successes)
    if has_error_radar and has_health and recent_failures == 0:
        verification = 1.0
    elif has_error_radar or has_health:
        verification = 0.75 if recent_failures <= 1 else 0.55
    else:
        verification = 0.4 if recent_failures == 0 else 0.2

    identity_surface = identity_surface or _identity_surface_summary()
    identity_status = identity_surface.get("status")
    identity_cap_applied = identity_status not in {"PASS", "UNKNOWN"}
    conversation_audit = conversation_audit or _conversation_audit_summary()
    has_conversation_audit = bool(conversation_audit.get("available") or conversation_audit.get("events"))

    weighted = (context * 0.4) + (schema_validated * 0.3) + (verification * 0.3)
    if identity_cap_applied:
        weighted = min(weighted, 0.7)
    return {
        "score": int(round(weighted * 100)),
        "weights": {
            "context_found": 0.4,
            "schema_validated": 0.3,
            "verification_passed": 0.3,
        },
        "signals": {
            "context_found": round(context, 3),
            "schema_validated": round(schema_validated, 3),
            "verification_passed": round(verification, 3),
            "has_code_context_pack": has_pack,
            "has_ui_snapshot": has_ui,
            "has_code_map": has_code_map,
            "has_error_radar": has_error_radar,
            "has_tool_healthcheck": has_health,
            "recent_failures": recent_failures,
            "schema_errors": schema_errors,
            "identity_surface_status": identity_status,
            "identity_surface_violations": identity_surface.get("violations"),
            "identity_surface_missing_required": identity_surface.get("missing_required"),
            "identity_cap_applied": identity_cap_applied,
            "has_conversation_audit": has_conversation_audit,
            "conversation_audit_events": conversation_audit.get("events"),
            "conversation_audit_spoken_events": conversation_audit.get("spoken_events"),
        },
        "message": f"Gata cu {int(round(weighted * 100))}% incredere.",
    }


class SessionAuditTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="session_audit",
            description=(
                "Generate public-safe session audit reports with hash-chain integrity, "
                "deterministic replay-lite signatures, and trust score."
            ),
            parameters=[
                ToolParameter("action", "generate, trust, replay", "string", False, "generate", choices=["generate", "trust", "replay"]),
                ToolParameter("hours", "Time range in hours", "integer", False, 1),
                ToolParameter("limit", "Maximum events", "integer", False, 80),
                ToolParameter("run_id", "Optional run/session id", "string", False, ""),
            ],
            category="diagnostics",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = str(kwargs.get("action") or "generate")
        hours = max(1, min(int(kwargs.get("hours") or 1), 168))
        limit = max(1, min(int(kwargs.get("limit") or 80), 500))
        run_id = str(kwargs.get("run_id") or f"ana-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}")

        events = self._events(hours=hours, limit=limit)
        identity_surface = _identity_surface_summary()
        conversation_audit = _conversation_audit_summary(hours=hours, limit=limit)
        trust = _score(events, identity_surface=identity_surface, conversation_audit=conversation_audit)

        if action == "trust":
            trace = _trace_summary()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "schema": "ana.session_trust.v1",
                    "run_id": run_id,
                    "trust": trust,
                    "identity_surface": identity_surface,
                    "conversation_audit": conversation_audit,
                    "trace": trace,
                },
                message=trust["message"],
            )

        audit_events, chain_head = self._audit_events(events, run_id)
        replay = [event["replay"] for event in audit_events]
        trace = _trace_summary()
        if action == "replay":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "schema": "ana.replay_lite.v1",
                    "run_id": run_id,
                    "chain_head": chain_head,
                    "steps": replay,
                    "identity_surface": identity_surface,
                    "conversation_audit": conversation_audit,
                    "trace": trace,
                },
                message=f"{len(replay)} replay-lite steps.",
            )

        report = {
            "schema": "ana.session_audit.v1",
            "run_id": run_id,
            "generated_at": _now_iso(),
            "scope": {"hours": hours, "limit": limit, "events": len(audit_events)},
            "trust": trust,
            "identity_surface": identity_surface,
            "conversation_audit": conversation_audit,
            "trace": trace,
            "integrity": {"algorithm": "sha256", "chain_head": chain_head},
            "events": audit_events,
        }
        DEFAULT_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        target = DEFAULT_AUDIT_DIR / f"session_audit_{run_id}.json"
        target.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        return ToolResult(status=ToolStatus.SUCCESS, data={**report, "file": str(target)}, message=f"{trust['message']} Audit saved.")

    def _events(self, hours: int, limit: int) -> list[dict[str, Any]]:
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        events = get_event_stream().query_events(start_time=start_time, end_time=end_time, limit=limit)
        events.reverse()
        return events

    def _audit_events(self, events: list[dict[str, Any]], run_id: str) -> tuple[list[dict[str, Any]], str]:
        chain = "0" * 64
        audit_events = []
        for index, event in enumerate(events, 1):
            audit_event, chain = _compact_event(event, run_id, chain, index)
            audit_events.append(audit_event)
        return audit_events, chain
