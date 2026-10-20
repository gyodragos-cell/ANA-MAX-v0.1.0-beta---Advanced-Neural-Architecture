"""Metadata-only mitmproxy addon for explicitly scoped OS29 lab traffic.

Load with mitmdump -s integrations/mitmproxy/os29_addon.py from OS29_LAB.
Request/response bodies and raw headers are never persisted by this addon.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from os29.models import TraceEvent, new_id
from os29.scope import ScopePolicy
from os29.store import Store


ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = Path(os.environ.get("OS29_SCOPE_PATH", str(ROOT / "config" / "lab_scope.json")))
DB_PATH = Path(os.environ.get("OS29_DB_PATH", str(ROOT / "data" / "os29.db")))
TRACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    default = (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)
    return f"{parsed.scheme.lower()}://{host}" if default else f"{parsed.scheme.lower()}://{host}:{port}"


class OS29MitmAddon:
    def __init__(self) -> None:
        self.scope = ScopePolicy(SCOPE_PATH)
        self.store = Store(DB_PATH)
        self.name = "OS29 scoped metadata trace"

    def request(self, flow) -> None:
        url = flow.request.pretty_url
        decision = self.scope.check_target(url)
        if not decision.get("allowed"):
            # Do not log out-of-scope URLs or traffic; do not interfere with the request.
            flow.metadata["os29_scoped"] = False
            return
        incoming = str(flow.request.headers.get("X-OS29-Trace-ID", "")).strip()
        trace_id = incoming if TRACE_RE.fullmatch(incoming) else f"mitm-{new_id()}"
        event = TraceEvent(
            trace_id=trace_id,
            source="mitmproxy",
            component="http_client",
            kind="http.request",
            action=str(flow.request.method).upper(),
            outcome="observed",
            mission_id=os.environ.get("OS29_MISSION_ID") or None,
            target=_origin(url),
            attributes={
                "request_id": str(flow.id),
                "method": str(flow.request.method).upper(),
                "host": str(flow.request.host).lower(),
                "port": int(flow.request.port),
                "url_path_sha256": hashlib.sha256(urlsplit(url).path.encode("utf-8", "replace")).hexdigest(),
                "request_bytes": len(flow.request.raw_content or b""),
                "content_type": str(flow.request.headers.get("Content-Type", ""))[:120],
                "capture_mode": "metadata_only",
            },
        )
        stored = self.store.record_event(event)
        flow.metadata["os29_scoped"] = True
        flow.metadata["os29_trace_id"] = trace_id
        flow.metadata["os29_request_event_id"] = stored["event_id"]
        flow.metadata["os29_start"] = getattr(flow.request, "timestamp_start", None)

    def response(self, flow) -> None:
        if not flow.metadata.get("os29_scoped"):
            return
        status_code = int(flow.response.status_code)
        start = flow.metadata.get("os29_start")
        end = getattr(flow.response, "timestamp_end", None)
        duration_ms = round((end - start) * 1000, 3) if start and end and end >= start else None
        event = TraceEvent(
            trace_id=flow.metadata["os29_trace_id"],
            parent_event_id=flow.metadata.get("os29_request_event_id"),
            source="mitmproxy",
            component="http_client",
            kind="http.response",
            action="HTTP response",
            outcome="failure" if status_code >= 500 else "observed",
            mission_id=os.environ.get("OS29_MISSION_ID") or None,
            target=_origin(flow.request.pretty_url),
            duration_ms=duration_ms,
            attributes={
                "request_id": str(flow.id),
                "status_code": status_code,
                "response_bytes": len(flow.response.raw_content or b""),
                "content_type": str(flow.response.headers.get("Content-Type", ""))[:120],
                "capture_mode": "metadata_only",
            },
        )
        self.store.record_event(event)


addons = [OS29MitmAddon()]