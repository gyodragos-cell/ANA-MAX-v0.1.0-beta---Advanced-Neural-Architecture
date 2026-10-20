from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from .diagnosis import diagnose_trace
from .intelligence import build_intelligence_report
from .models import TraceEvent, new_id
from .runtime_snapshot import snapshot_loopback
from .scope import ScopePolicy
from .retrieval import refresh_memory_index, search_memory
from .store import Store


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(os.environ.get("OS29_DB_PATH", str(ROOT / "data" / "os29.db"))).expanduser()
DEFAULT_SCOPE = Path(os.environ.get("OS29_SCOPE_PATH", str(ROOT / "config" / "lab_scope.json"))).expanduser()


def _json(value: Any) -> None:
    # Keep redirected Windows-console output safe on legacy code pages.
    # Artifact writers use UTF-8 files directly; this function is console output.
    print(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True))


def _store(args: argparse.Namespace) -> Store:
    return Store(Path(args.db).expanduser() if getattr(args, "db", None) else DEFAULT_DB)


def _event(trace_id: str, source: str, component: str, kind: str, action: str,
           outcome: str = "observed", parent_event_id: str | None = None,
           mission_id: str | None = None, target: str | None = None,
           attributes: dict[str, Any] | None = None) -> TraceEvent:
    return TraceEvent(
        trace_id=trace_id, source=source, component=component, kind=kind,
        action=action, outcome=outcome, parent_event_id=parent_event_id,
        mission_id=mission_id, target=target, attributes=attributes or {},
    )


def cmd_status(args: argparse.Namespace) -> int:
    _json(_store(args).stats())
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    _json(snapshot_loopback(_store(args), timeout=args.timeout))
    return 0


def cmd_scope_check(args: argparse.Namespace) -> int:
    decision = ScopePolicy(args.scope).check_target(args.target)
    _json(decision)
    return 0 if decision["allowed"] else 3


def cmd_trace(args: argparse.Namespace) -> int:
    store = _store(args)
    if args.diagnose:
        _json(diagnose_trace(store, args.trace_id))
    else:
        _json({"summary": store.trace_summary(args.trace_id), "events": store.list_trace(args.trace_id)})
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    store = _store(args)
    trace_id = f"demo-{new_id()}"
    mission_id = "os29-demo-vertical-slice"
    first = store.record_event(_event(
        trace_id, "os29.demo", "test_harness", "demo.started", "start", "success",
        mission_id=mission_id, attributes={"synthetic": True, "purpose": "validate persistent trace pipeline"},
    ).to_dict())
    request = store.record_event(_event(
        trace_id, "mitmproxy.demo", "demo_api", "http.request", "GET /health", "observed",
        parent_event_id=first["event_id"], mission_id=mission_id, target="http://127.0.0.1:8766/health",
        attributes={"method": "GET", "request_id": "demo-request-1", "synthetic": True, "headers": {"Authorization": "Bearer demo-secret-not-persisted"}},
    ).to_dict())
    failure = store.record_event(_event(
        trace_id, "mitmproxy.demo", "demo_api", "http.response", "HTTP response", "failure",
        parent_event_id=request["event_id"], mission_id=mission_id, target="http://127.0.0.1:8766/health",
        attributes={"status_code": 503, "request_id": "demo-request-1", "synthetic": True},
    ).to_dict())
    frida = store.record_event(_event(
        trace_id, "frida.demo", "ExampleApiClient", "frida.method.exit", "fetchHealth", "error",
        parent_event_id=failure["event_id"], mission_id=mission_id,
        attributes={"span_id": "demo-span-1", "exception_type": "DemoIOException", "synthetic": True},
    ).to_dict())
    verified = store.record_event(_event(
        trace_id, "os29.demo", "test_harness", "test.completed", "persistence and redaction checks", "success",
        parent_event_id=frida["event_id"], mission_id=mission_id,
        attributes={"synthetic": True, "ground_truth": "fixture_assertions_passed"},
    ).to_dict())

    incident = store.create_incident(trace_id)
    lesson = store.record_experience(
        problem_key="demo: http health unavailable",
        cause="Example cause is intentionally unverified in the synthetic demo.",
        solution="Use this synthetic trace to verify ingestion/persistence; do not reuse it as a production fix.",
        outcome="partial",
        source_event_ids=[failure["event_id"], frida["event_id"], verified["event_id"]],
        outcome_verified=False,
        confidence=0.1,
    )
    capsule = {
        "project": "OS29_LAB",
        "status": "demo",
        "objective": "Prove trace -> redaction -> incident -> candidate experience -> persistent retrieval.",
        "current_state": {"trace_id": trace_id, "events": 5, "synthetic": True},
        "known_good": ["SQLite persistence", "trace identity", "secret redaction"],
        "known_bad": ["No production root cause was asserted."],
        "open_issues": ["Connect actual OS28 tool spans to external Frida/MITM traces."],
        "next_steps": ["Configure an explicitly approved app process", "Run a benign authorized test flow"],
        "tests": ["Synthetic event pipeline demo"],
        "notes": "All events are synthetic fixtures; not evidence of a real service incident.",
    }
    saved_capsule = store.save_capsule(mission_id, capsule)
    _json({
        "result": "OS29_DEMO_PASS",
        "note": "Synthetic fixture only; incident cause remains unverified and experience stays candidate.",
        "stats": store.stats(),
        "trace_id": trace_id,
        "trace_summary": store.trace_summary(trace_id),
        "incident": incident,
        "experience": lesson,
        "capsule": saved_capsule,
    })
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    store = _store(args)
    count = 0
    failures = []
    with Path(args.file).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = TraceEvent.from_dict(json.loads(line))
                store.record_event(event)
                count += 1
            except Exception as exc:
                failures.append({"line": line_number, "error": str(exc)})
                if not args.continue_on_error:
                    break
    _json({"ingested": count, "failed": len(failures), "errors": failures[:50]})
    return 1 if failures else 0


def cmd_capsule_get(args: argparse.Namespace) -> int:
    value = _store(args).get_capsule(args.mission_id)
    _json(value if value else {"error": "mission capsule not found", "mission_id": args.mission_id})
    return 0 if value else 4


def cmd_capsule_save(args: argparse.Namespace) -> int:
    capsule = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(capsule, dict):
        raise ValueError("capsule file must contain a JSON object")
    _json(_store(args).save_capsule(args.mission_id, capsule))
    return 0


def cmd_experience_search(args: argparse.Namespace) -> int:
    _json(_store(args).search_experiences(args.query, include_candidates=not args.validated_only, limit=args.limit))
    return 0


def cmd_experience_validate(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("experience validation requires an interactive local terminal")
    store = _store(args)
    candidate = store.get_experience(args.lesson_id)
    if not candidate:
        raise ValueError("experience not found")
    if candidate["status"] != "candidate":
        raise ValueError("only candidate experiences can be validated")
    if args.verification_event_id not in candidate["source_event_ids"]:
        raise ValueError("verification event must already be linked to the candidate")
    verification = store.get_event(args.verification_event_id)
    if not verification:
        raise ValueError("verification event not found")
    print("Candidate experience:")
    _json(candidate)
    print("Linked verification event:")
    _json(verification)
    verifier = input("Operator/verifier identifier: ").strip()
    if not verifier:
        raise ValueError("verifier identifier cannot be empty")
    expected = f"VALIDATE {args.lesson_id}"
    typed = input(f"To promote this candidate after reviewing the evidence, type exactly [{expected}]: ").strip()
    if typed != expected:
        print("Validation cancelled; experience remains candidate.")
        return 5
    result = store.validate_experience(
        lesson_id=args.lesson_id,
        verification_event_id=args.verification_event_id,
        verified_by=verifier,
        confidence=args.confidence,
    )
    _json({"result": "EXPERIENCE_VALIDATED", "experience": result})
    return 0


def cmd_intelligence(args: argparse.Namespace) -> int:
    _json(build_intelligence_report(_store(args), event_limit=args.event_limit))
    return 0


def cmd_memory_index(args: argparse.Namespace) -> int:
    _json(refresh_memory_index(_store(args)))
    return 0


def cmd_memory_search(args: argparse.Namespace) -> int:
    _json(search_memory(
        _store(args), args.query, limit=args.limit,
        include_candidates=args.include_candidates, source_types=args.source_type,
    ))
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    _json(_store(args).list_capabilities(limit=args.limit))
    return 0


def cmd_capability_edges(args: argparse.Namespace) -> int:
    _json(_store(args).list_capability_edges(limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="os29", description="OS29 evidence-first operational intelligence CLI")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path (default: OS29_LAB/data/os29.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="show persistent store status")
    status.set_defaults(func=cmd_status)

    intelligence = commands.add_parser(
        "intelligence",
        help="build evidence-first Agent DNA, REM, Regret, Skill Distillation and Discovery report",
    )
    intelligence.add_argument("--event-limit", type=int, default=500)
    intelligence.set_defaults(func=cmd_intelligence)

    memory_index = commands.add_parser("memory-index", help="refresh the local lexical memory/RAG index from redacted OS29 evidence")
    memory_index.set_defaults(func=cmd_memory_index)

    memory_search = commands.add_parser("memory-search", help="search indexed events, incidents, capsules, capabilities and experiences")
    memory_search.add_argument("query")
    memory_search.add_argument("--limit", type=int, default=10)
    memory_search.add_argument("--include-candidates", action="store_true", help="include clearly labeled unvalidated/rejected experience records")
    memory_search.add_argument("--source-type", choices=["event", "incident", "capsule", "experience", "capability", "document"], action="append", default=[])
    memory_search.set_defaults(func=cmd_memory_search)

    snapshot = commands.add_parser("snapshot", help="perform read-only loopback service health probes and persist capability observations")
    snapshot.add_argument("--timeout", type=float, default=1.2)
    snapshot.set_defaults(func=cmd_snapshot)

    scope = commands.add_parser("scope-check", help="check whether a target is explicitly approved")
    scope.add_argument("target")
    scope.add_argument("--scope", default=str(DEFAULT_SCOPE))
    scope.set_defaults(func=cmd_scope_check)

    demo = commands.add_parser("demo", help="run a synthetic end-to-end evidence pipeline")
    demo.set_defaults(func=cmd_demo)

    trace = commands.add_parser("trace", help="inspect a trace and optionally create an evidence-first diagnosis")
    trace.add_argument("trace_id")
    trace.add_argument("--diagnose", action="store_true")
    trace.set_defaults(func=cmd_trace)

    ingest = commands.add_parser("ingest-jsonl", help="ingest normalized os29.trace.v1 JSONL events")
    ingest.add_argument("file")
    ingest.add_argument("--continue-on-error", action="store_true")
    ingest.set_defaults(func=cmd_ingest)

    capsule = commands.add_parser("capsule", help="inspect a mission capsule")
    capsule_sub = capsule.add_subparsers(dest="capsule_action", required=True)
    capsule_get = capsule_sub.add_parser("get")
    capsule_get.add_argument("mission_id")
    capsule_get.set_defaults(func=cmd_capsule_get)
    capsule_save = capsule_sub.add_parser("save", help="persist a mission capsule JSON file")
    capsule_save.add_argument("mission_id")
    capsule_save.add_argument("file")
    capsule_save.set_defaults(func=cmd_capsule_save)

    experience = commands.add_parser("experience-search", help="search evidence-linked experience records")
    experience.add_argument("query")
    experience.add_argument("--validated-only", action="store_true")
    experience.add_argument("--limit", type=int, default=20)
    experience.set_defaults(func=cmd_experience_search)

    validate = commands.add_parser("experience-validate", help="manually review a candidate and linked test evidence in an interactive terminal")
    validate.add_argument("lesson_id")
    validate.add_argument("verification_event_id")
    validate.add_argument("--confidence", type=float, default=0.8)
    validate.set_defaults(func=cmd_experience_validate)

    capabilities = commands.add_parser("capabilities", help="list observed capability/world-model nodes")
    capabilities.add_argument("--limit", type=int, default=500)
    capabilities.set_defaults(func=cmd_capabilities)

    edges = commands.add_parser("capability-edges", help="list observed relationships in the capability/world model")
    edges.add_argument("--limit", type=int, default=1000)
    edges.set_defaults(func=cmd_capability_edges)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()