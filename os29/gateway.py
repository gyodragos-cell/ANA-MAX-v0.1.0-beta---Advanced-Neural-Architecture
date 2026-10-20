from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .models import TraceEvent
from .store import Store


ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 1_048_576


class OS29Handler(BaseHTTPRequestHandler):
    server_version = "OS29-Loopback-Gateway/0.1"

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

    @property
    def token(self) -> str:
        return self.server.token  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Never put request headers or credentials in default HTTP access logs.
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        expected = "Bearer " + self.token
        # Compare constant-length strings in constant time.
        import hmac
        return hmac.compare_digest(header.encode("utf-8"), expected.encode("utf-8"))

    def _body(self) -> dict[str, Any] | None:
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError:
            self._send(411, {"error": "content_length_required"})
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self._send(413, {"error": "payload_too_large"})
            return None
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, {"error": "invalid_json"})
            return None
        if not isinstance(value, dict):
            self._send(400, {"error": "json_object_required"})
            return None
        return value

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            self._send(200, {"status": "ok", "service": "os29-loopback-gateway", "schema_version": "os29.api.v1"})
            return
        if not self._authorized():
            self._send(401, {"error": "authentication_required"})
            return
        if path == "/status":
            self._send(200, self.store.stats())
        elif path == "/capabilities":
            self._send(200, {"capabilities": self.store.list_capabilities()})
        elif path == "/capability-edges":
            self._send(200, {"edges": self.store.list_capability_edges()})
        elif path.startswith("/traces/"):
            trace_id = unquote(path[len("/traces/"):])
            events = self.store.list_trace(trace_id)
            self._send(200, {"trace_id": trace_id, "events": events, "summary": self.store.trace_summary(trace_id)})
        elif path.startswith("/capsules/"):
            mission_id = unquote(path[len("/capsules/"):])
            capsule = self.store.get_capsule(mission_id)
            self._send(200 if capsule else 404, capsule or {"error": "capsule_not_found"})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if not self._authorized():
            self._send(401, {"error": "authentication_required"})
            return
        value = self._body()
        if value is None:
            return
        try:
            if path == "/events":
                event = TraceEvent.from_dict(value)
                result = self.store.record_event(event)
                self._send(201, {"success": True, **result})
            elif path == "/capsules":
                mission_id = str(value.pop("mission_id", ""))
                capsule = value.pop("capsule", None)
                if not isinstance(capsule, dict):
                    self._send(400, {"error": "capsule_object_required"})
                    return
                result = self.store.save_capsule(mission_id, capsule)
                self._send(201, {"success": True, **result})
            elif path == "/capabilities":
                result = self.store.upsert_capability(
                    kind=str(value.get("kind", "")),
                    name=str(value.get("name", "")),
                    status=str(value.get("status", "unknown")),
                    owner=str(value["owner"]) if value.get("owner") else None,
                    evidence=value.get("evidence", {}) if isinstance(value.get("evidence", {}), dict) else {},
                )
                self._send(201, {"success": True, **result})
            else:
                self._send(404, {"error": "not_found"})
        except (ValueError, TypeError) as exc:
            self._send(400, {"error": str(exc)})


def make_server(db_path: str | Path, token: str, host: str = "127.0.0.1", port: int = 8790) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("OS29 gateway may bind only to loopback")
    if len(token) < 32:
        raise ValueError("OS29_GATEWAY_TOKEN must contain at least 32 characters")
    server = ThreadingHTTPServer((host, int(port)), OS29Handler)
    server.daemon_threads = True
    server.store = Store(db_path)  # type: ignore[attr-defined]
    server.token = token  # type: ignore[attr-defined]
    return server


def main() -> None:
    root = ROOT
    db = Path(os.environ.get("OS29_DB_PATH", str(root / "data" / "os29.db")))
    token = os.environ.get("OS29_GATEWAY_TOKEN", "")
    host = "127.0.0.1"
    port = int(os.environ.get("OS29_GATEWAY_PORT", "8790"))
    server = make_server(db, token, host, port)
    print(f"OS29 gateway listening on http://{host}:{port} (loopback only; token value not displayed)")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()