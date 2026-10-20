from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .diagnosis import diagnose_trace
from .intelligence import build_intelligence_report
from .models import TraceEvent, new_id
from .runtime_snapshot import snapshot_loopback
from .scope import ScopePolicy
from .retrieval import search_memory
from .store import Store
from .tools import terminal_exec, file_read, file_write, code_search
from .telemetry import log_tool_call, log_tool_result, log_error, log_startup, log_shutdown


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("OS29_DB_PATH", str(ROOT / "data" / "os29.db")))
SCOPE_PATH = Path(os.environ.get("OS29_SCOPE_PATH", str(ROOT / "config" / "lab_scope.json")))
PROTOCOL_VERSION = "2024-11-05"


def schemas() -> list[dict[str, Any]]:
    def obj(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
        return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}
    string = {"type": "string"}
    integer = {"type": "integer", "minimum": 1, "maximum": 2000}
    return [
        {"name": "os29_status", "description": "Read-only counts/status of the persistent OS29 evidence store.", "inputSchema": obj()},
        {"name": "os29_runtime_snapshot", "description": "Read-only HTTP health probes against fixed 127.0.0.1 OS28 ports; never starts/stops a service.", "inputSchema": obj()},
        {"name": "os29_scope_check", "description": "Check an HTTP(S) target against the explicit OS29 lab allowlist; does not contact the target.", "inputSchema": obj({"target": string}, ["target"])},
        {"name": "os29_trace_get", "description": "Read one persisted OS29 trace by trace_id.", "inputSchema": obj({"trace_id": string}, ["trace_id"])},
        {"name": "os29_trace_diagnose", "description": "Summarize observed failures for a trace and create an incident record; root cause remains explicitly unverified.", "inputSchema": obj({"trace_id": string}, ["trace_id"])},
        {"name": "os29_capabilities_list", "description": "Read the observed capability/world-model nodes and their evidence freshness timestamps.", "inputSchema": obj({"limit": integer})},
        {"name": "os29_capability_edges_list", "description": "Read observed relationships between capability/world-model nodes.", "inputSchema": obj({"limit": integer})},
        {"name": "os29_mission_capsule_get", "description": "Read a persistent OS29 mission capsule.", "inputSchema": obj({"mission_id": string}, ["mission_id"])},
        {"name": "os29_mission_capsule_save", "description": "Persist an operator/agent mission checkpoint. Secrets are redacted; required state fields must be present.", "inputSchema": obj({"mission_id": string, "capsule": obj({"project": string, "objective": string, "current_state": {}, "known_good": {"type": "array"}, "known_bad": {"type": "array"}, "open_issues": {"type": "array"}, "next_steps": {"type": "array"}}, ["project", "objective", "current_state", "known_good", "known_bad", "open_issues", "next_steps"])}, ["mission_id", "capsule"])},
        {"name": "os29_trace_record", "description": "Persist one normalized os29.trace.v1 observation with automatic redaction.", "inputSchema": obj({"event": {"type": "object"}}, ["event"])},
        {"name": "os29_experience_search", "description": "Search evidence-linked experience; only validated lessons are returned by default.", "inputSchema": obj({"query": string, "include_candidates": {"type": "boolean"}, "limit": integer}, ["query"])},
        {"name": "os29_memory_search", "description": "Search the persistent local memory across trace events, incidents, mission capsules, capabilities, experiences and explicitly approved local text documents using redacted SQLite FTS5/BM25 retrieval. Candidate lessons are excluded by default; semantic embeddings are not enabled.", "inputSchema": obj({"query": string, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "include_candidates": {"type": "boolean"}, "source_types": {"type": "array", "items": {"type": "string", "enum": ["event", "incident", "capsule", "experience", "capability", "document"]}}}, ["query"])},
        {"name": "os29_experience_candidate_add", "description": "Record an unvalidated candidate lesson linked to persisted source event IDs. This tool cannot mark a lesson validated.", "inputSchema": obj({"problem_key": string, "cause": string, "solution": string, "outcome": {"type": "string", "enum": ["success", "failure", "partial", "unknown"]}, "source_event_ids": {"type": "array", "items": string}}, ["problem_key", "cause", "solution", "outcome", "source_event_ids"])},
        {"name": "os29_intelligence_report", "description": "Unified evidence-first Agent DNA, Memory of Failure/REM, Regret candidates, Skill Distillation and Discovery report. No auto-start, unverified causal claims or candidate promotion.", "inputSchema": obj({"event_limit": {"type": "integer", "minimum": 1, "maximum": 1000}})},
        {"name": "os29_terminal_exec", "description": "Execute a shell command locally in the lab with timeout and captured output.", "inputSchema": obj({"command": string, "cwd": string, "timeout_seconds": integer}, ["command"])},
        {"name": "os29_file_read", "description": "Read file lines with safe bounds and encoding handling.", "inputSchema": obj({"path": string, "start_line": integer, "end_line": integer}, ["path"])},
        {"name": "os29_file_write", "description": "Write or overwrite a file in the workspace.", "inputSchema": obj({"path": string, "content": string, "overwrite": {"type": "boolean"}}, ["path", "content"])},
        {"name": "os29_code_search", "description": "Search regex pattern across code and files.", "inputSchema": obj({"pattern": string, "search_path": string, "max_results": integer, "case_sensitive": {"type": "boolean"}}, ["pattern"])},
    ]


TOOL_NAMES = {tool["name"] for tool in schemas()}


def _content(value: Any, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)}],
        "isError": is_error,
    }


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    store    = Store(DB_PATH)
    trace_id = f"mcp-{new_id()[:8]}"
    _start   = log_tool_call(name, trace_id)
    try:
        result  = _dispatch(store, name, args, trace_id)
        outcome = "failure" if isinstance(result, dict) and result.get("isError") else "success"
        log_tool_result(name, trace_id, _start, outcome)
        return result
    except Exception as exc:
        log_error(name, exc, trace_id)
        raise


def _dispatch(store: Store, name: str, args: dict[str, Any], trace_id: str) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        raise ValueError(f"unknown OS29 tool: {name}")
    if name == "os29_status":
        return store.stats()
    if name == "os29_runtime_snapshot":
        return snapshot_loopback(store)
    if name == "os29_scope_check":
        decision = ScopePolicy(SCOPE_PATH).check_target(args["target"])
        # Persist the decision and reason, but not the full target URL/path/query.
        store.record_event(TraceEvent(
            trace_id=f"scope-check-{new_id()}",
            source="os29.scope",
            component="scope_policy",
            kind="scope.decision",
            action="check_target",
            outcome="observed" if decision.get("allowed") else "blocked",
            attributes={
                "allowed": bool(decision.get("allowed")),
                "reason": str(decision.get("reason", "unknown")),
                "host": str(decision.get("host", ""))[:255],
                "port": decision.get("port"),
                "scheme": str(decision.get("scheme", ""))[:16],
            },
        ))
        return decision
    if name == "os29_trace_get":
        trace_id = str(args["trace_id"])
        events = store.list_trace(trace_id)
        return {"trace_id": trace_id, "event_count": len(events), "events": events, "summary": store.trace_summary(trace_id)}
    if name == "os29_trace_diagnose":
        return diagnose_trace(store, str(args["trace_id"]))
    if name == "os29_capabilities_list":
        return {"capabilities": store.list_capabilities(limit=int(args.get("limit", 500)))}
    if name == "os29_capability_edges_list":
        return {"edges": store.list_capability_edges(limit=int(args.get("limit", 1000)))}
    if name == "os29_mission_capsule_get":
        value = store.get_capsule(str(args["mission_id"]))
        if not value:
            raise ValueError("mission capsule not found")
        return value
    if name == "os29_mission_capsule_save":
        return store.save_capsule(str(args["mission_id"]), args["capsule"])
    if name == "os29_trace_record":
        event = TraceEvent.from_dict(args["event"])
        return store.record_event(event)
    if name == "os29_experience_search":
        include_candidates = bool(args.get("include_candidates", False))
        return {
            "query": str(args["query"]),
            "include_candidates": include_candidates,
            "experiences": store.search_experiences(
                str(args["query"]), include_candidates=include_candidates, limit=int(args.get("limit", 20))
            ),
        }
    if name == "os29_memory_search":
        return search_memory(
            store,
            str(args["query"]),
            limit=int(args.get("limit", 10)),
            include_candidates=bool(args.get("include_candidates", False)),
            source_types=args.get("source_types", []),
        )
    if name == "os29_experience_candidate_add":
        return store.record_experience(
            problem_key=str(args["problem_key"]),
            cause=str(args["cause"]),
            solution=str(args["solution"]),
            outcome=str(args["outcome"]),
            source_event_ids=[str(x) for x in args["source_event_ids"]],
            outcome_verified=False,
            verified_by=None,
            confidence=0.0,
        )
    if name == "os29_intelligence_report":
        return build_intelligence_report(store, event_limit=int(args.get("event_limit", 500)))
    if name == "os29_terminal_exec":
        return terminal_exec(
            str(args["command"]),
            cwd=args.get("cwd"),
            timeout_seconds=int(args.get("timeout_seconds", 60)),
            store=store,
            trace_id=trace_id,
        )
    if name == "os29_file_read":
        return file_read(str(args["path"]), start_line=args.get("start_line"), end_line=args.get("end_line"))
    if name == "os29_file_write":
        return file_write(str(args["path"]), str(args["content"]), overwrite=bool(args.get("overwrite", True)))
    if name == "os29_code_search":
        return code_search(str(args["pattern"]), search_path=args.get("search_path"), max_results=int(args.get("max_results", 50)), case_sensitive=bool(args.get("case_sensitive", False)))
    raise ValueError(f"unimplemented OS29 tool: {name}")


def handle(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    method = message.get("method")
    request_id = message.get("id")
    if not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}
    params = message.get("params") or {}
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": "os29-operational-intelligence", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": schemas()}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return {"jsonrpc": "2.0", "id": request_id, "result": _content({"error": "arguments_must_be_object"}, True)}
        try:
            result = call_tool(str(name), args)
            return {"jsonrpc": "2.0", "id": request_id, "result": _content(result)}
        except (ValueError, KeyError, TypeError, OSError) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": _content({"error": str(exc)}, True)}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}


def encode_response(response: dict[str, Any]) -> str:
    """Serialize one JSON-RPC response using ASCII escapes for Windows code-page safety."""
    return json.dumps(response, ensure_ascii=True, separators=(",", ":")) + "\n"


def main() -> None:
    # MCP stdio framing is one JSON-RPC message per UTF-8 line. stdout is protocol-only.
    log_startup("os29-operational-intelligence", str(DB_PATH))
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                response = handle(json.loads(line))
            except json.JSONDecodeError:
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            except Exception as exc:
                print(f"OS29 MCP internal error: {type(exc).__name__}", file=sys.stderr, flush=True)
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": "Internal error"}}
            if response is not None:
                sys.stdout.write(encode_response(response))
                sys.stdout.flush()
    finally:
        log_shutdown()


if __name__ == "__main__":
    main()