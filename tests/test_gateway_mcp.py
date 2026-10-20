from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from os29 import mcp_stdio
from os29.gateway import make_server
from os29.models import TraceEvent


def _http(url: str, *, method: str = "GET", token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=2) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_gateway_loopback_only_health_auth_and_event_ingest(tmp_path: Path):
    token = "os29-test-token-" + "x" * 40
    server = make_server(tmp_path / "api.db", token, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, health = _http(base + "/health")
        assert status == 200 and health["service"] == "os29-loopback-gateway"

        try:
            _http(base + "/status")
            assert False, "unauthenticated status request should be denied"
        except HTTPError as exc:
            assert exc.code == 401

        status, runtime = _http(base + "/status", token=token)
        assert status == 200 and runtime["events"] == 0

        event = TraceEvent(
            trace_id="api-trace-1", source="test", component="gateway_test",
            kind="test.event", action="persist", outcome="success",
        ).to_dict()
        status, result = _http(base + "/events", method="POST", token=token, body=event)
        assert status == 201 and result["success"] is True

        status, trace = _http(base + "/traces/api-trace-1", token=token)
        assert status == 200 and len(trace["events"]) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mcp_stdio_tools_list_has_no_arbitrary_execution_tool(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "mcp.db")
    monkeypatch.setattr(mcp_stdio, "SCOPE_PATH", Path(__file__).resolve().parents[1] / "config" / "lab_scope.json")
    response = mcp_stdio.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert "os29_status" in names
    assert "os29_trace_record" in names
    assert "os29_scope_check" in names
    assert "terminal" not in names
    assert "bash_exec" not in names
    assert "frida_attach" not in names


def test_mcp_stdio_scope_and_trace_call(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "mcp-call.db")
    monkeypatch.setattr(mcp_stdio, "SCOPE_PATH", Path(__file__).resolve().parents[1] / "config" / "lab_scope.json")
    allow = mcp_stdio.handle({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "os29_scope_check", "arguments": {"target": "http://127.0.0.1:8766/health"}},
    })
    deny = mcp_stdio.handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "os29_scope_check", "arguments": {"target": "https://example.com/"}},
    })
    assert json.loads(allow["result"]["content"][0]["text"])["allowed"] is True
    assert json.loads(deny["result"]["content"][0]["text"])["allowed"] is False
    from os29.store import Store
    decisions = [
        event for event in Store(tmp_path / "mcp-call.db").recent_events(limit=10)
        if event.get("source") == "os29.scope"
    ]
    assert len(decisions) == 2
    blocked = next(event for event in decisions if event["outcome"] == "blocked")
    assert blocked["attributes"]["reason"] == "host_not_in_scope"
    assert blocked.get("target") is None
    assert "private-data" not in str(blocked)

    event = TraceEvent(
        trace_id="mcp-trace", source="test", component="mcp_test", kind="check", action="write", outcome="success",
    ).to_dict()
    recorded = mcp_stdio.handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "os29_trace_record", "arguments": {"event": event}},
    })
    body = json.loads(recorded["result"]["content"][0]["text"])
    assert body["trace_id"] == "mcp-trace"


def test_mcp_does_not_let_agent_validate_experience(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "mcp-experience.db")
    monkeypatch.setattr(mcp_stdio, "SCOPE_PATH", Path(__file__).resolve().parents[1] / "config" / "lab_scope.json")
    event = TraceEvent(
        trace_id="mcp-lesson", source="test", component="lesson_test", kind="result", action="run", outcome="success",
    ).to_dict()
    mcp_stdio.call_tool("os29_trace_record", {"event": event})
    from os29.store import Store
    store = Store(tmp_path / "mcp-experience.db")
    event_id = store.list_trace("mcp-lesson")[0]["event_id"]
    lesson = mcp_stdio.call_tool("os29_experience_candidate_add", {
        "problem_key": "test issue", "cause": "hypothesis", "solution": "try local reproduction",
        "outcome": "partial", "source_event_ids": [event_id],
    })
    assert lesson["status"] == "candidate"


def test_mcp_unified_intelligence_report_is_evidence_first(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "intelligence-mcp.db")
    monkeypatch.setattr(mcp_stdio, "SCOPE_PATH", Path(__file__).resolve().parents[1] / "config" / "lab_scope.json")
    response = mcp_stdio.handle({
        "jsonrpc": "2.0", "id": 77, "method": "tools/call",
        "params": {"name": "os29_intelligence_report", "arguments": {"event_limit": 100}},
    })
    report = json.loads(response["result"]["content"][0]["text"])
    assert report["schema_version"] == "os29.intelligence_report.v1"
    assert report["agent_dna"]["profiles"] == []
    assert report["resource_policy"]["auto_start_performed"] is False
    assert "skill_distillation" in report
    assert "rem_engine" in report
    assert "regret_engine" in report
    assert "discovery_engine" in report


def test_mcp_stdout_json_is_safe_on_legacy_windows_code_pages(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "unicode-safe.db")
    event = TraceEvent(
        trace_id="unicode-trace",
        source="test",
        component="unicode-test",
        kind="observation",
        action="store Unicode",
        outcome="success",
        attributes={"note": "Unicode arrow -> and real arrow \u2192, Romanian ș"},
    ).to_dict()
    response = mcp_stdio.handle({
        "jsonrpc": "2.0", "id": 78, "method": "tools/call",
        "params": {"name": "os29_trace_record", "arguments": {"event": event}},
    })
    unicode_response = {
        "jsonrpc": "2.0",
        "id": 79,
        "result": {"message": "arrow " + chr(0x2192) + " Romanian " + chr(0x0219)},
    }
    wire_line = mcp_stdio.encode_response(unicode_response)
    encoded = wire_line.encode("cp1252")
    assert b"\\u2192" in encoded
    assert b"\\u0219" in encoded
    assert encoded.endswith(b"\n")


def test_mcp_memory_search_uses_persistent_evidence_and_excludes_candidates_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mcp_stdio, "DB_PATH", tmp_path / "mcp-memory.db")
    monkeypatch.setattr(mcp_stdio, "SCOPE_PATH", Path(__file__).resolve().parents[1] / "config" / "lab_scope.json")

    recorded = mcp_stdio.call_tool("os29_trace_record", {"event": TraceEvent(
        trace_id="mcp-memory-trace",
        source="pytest",
        component="gateway-health",
        kind="http.response",
        action="health probe",
        outcome="error",
        attributes={"exception_type": "ReadTimeout", "status_code": 503},
    ).to_dict()})
    mcp_stdio.call_tool("os29_experience_candidate_add", {
        "problem_key": "ReadTimeout gateway recovery",
        "cause": "unverified hypothesis",
        "solution": "bounded retry",
        "outcome": "partial",
        "source_event_ids": [recorded["event_id"]],
    })

    schema = mcp_stdio.handle({"jsonrpc": "2.0", "id": 101, "method": "tools/list", "params": {}})
    assert "os29_memory_search" in {item["name"] for item in schema["result"]["tools"]}

    response = mcp_stdio.call_tool("os29_memory_search", {
        "query": "ReadTimeout gateway",
        "limit": 10,
        "source_types": ["event", "experience"],
    })
    assert response["retrieval_mode"] == "lexical_bm25"
    assert any(item["source_type"] == "event" for item in response["results"])
    assert not any(item["source_type"] == "experience" for item in response["results"])

    with_candidates = mcp_stdio.call_tool("os29_memory_search", {
        "query": "ReadTimeout gateway",
        "limit": 10,
        "include_candidates": True,
        "source_types": ["experience"],
    })
    assert with_candidates["result_count"] == 1
    assert with_candidates["results"][0]["trust_status"] == "candidate"