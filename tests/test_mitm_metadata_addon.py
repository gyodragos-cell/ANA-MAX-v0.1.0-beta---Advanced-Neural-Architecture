from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import integrations.mitmproxy.os29_addon as addon_module
from integrations.mitmproxy.os29_addon import OS29MitmAddon
from os29.store import Store


class Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def make_flow(url: str, *, status: int = 200, trace_id: str = "approved-flow-1"):
    request = SimpleNamespace(
        pretty_url=url,
        method="GET",
        host="127.0.0.1",
        port=8766,
        raw_content=b"request body must never be persisted",
        headers=Headers({
            "X-OS29-Trace-ID": trace_id,
            "Authorization": "Bearer this-secret-must-not-be-stored",
            "Content-Type": "application/json",
        }),
        timestamp_start=100.0,
    )
    response = SimpleNamespace(
        status_code=status,
        raw_content=b"response body must never be persisted",
        headers=Headers({
            "Set-Cookie": "session=this-secret-also-must-not-be-stored",
            "Content-Type": "application/json",
        }),
        timestamp_end=100.125,
    )
    return SimpleNamespace(id="fake-flow-1", request=request, response=response, metadata={})


def test_mitm_addon_persists_only_metadata_for_scoped_request(tmp_path: Path, monkeypatch):
    db = tmp_path / "mitm-addon.db"
    monkeypatch.setenv("OS29_DB_PATH", str(db))
    monkeypatch.setattr(addon_module, "DB_PATH", db)
    monkeypatch.setattr(
        addon_module,
        "SCOPE_PATH",
        Path(__file__).resolve().parents[1] / "config" / "lab_scope.json",
    )
    addon = OS29MitmAddon()
    flow = make_flow("http://127.0.0.1:8766/health", status=503)

    addon.request(flow)
    addon.response(flow)

    assert flow.metadata["os29_scoped"] is True
    events = Store(db).list_trace("approved-flow-1")
    assert len(events) == 2
    assert events[0]["kind"] == "http.request"
    assert events[1]["kind"] == "http.response"
    assert events[1]["parent_event_id"] == events[0]["event_id"]
    assert events[1]["outcome"] == "failure"
    assert events[1]["duration_ms"] == 125.0
    serialized = str(events)
    assert "this-secret-must-not-be-stored" not in serialized
    assert "this-secret-also-must-not-be-stored" not in serialized
    assert "request body must never be persisted" not in serialized
    assert "response body must never be persisted" not in serialized
    assert events[0]["attributes"]["capture_mode"] == "metadata_only"


def test_mitm_addon_does_not_persist_out_of_scope_request(tmp_path: Path, monkeypatch):
    db = tmp_path / "mitm-out-of-scope.db"
    monkeypatch.setenv("OS29_DB_PATH", str(db))
    monkeypatch.setattr(addon_module, "DB_PATH", db)
    monkeypatch.setattr(
        addon_module,
        "SCOPE_PATH",
        Path(__file__).resolve().parents[1] / "config" / "lab_scope.json",
    )
    addon = OS29MitmAddon()
    flow = make_flow("https://example.com/private-data", status=200)
    addon.request(flow)
    addon.response(flow)
    assert flow.metadata.get("os29_scoped") is False
    assert Store(db).stats()["events"] == 0