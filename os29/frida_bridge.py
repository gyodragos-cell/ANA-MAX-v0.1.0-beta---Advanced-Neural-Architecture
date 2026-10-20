from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .models import TraceEvent
from .scope import ScopePolicy
from .store import Store


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Attach Frida to one explicitly approved lab process and stream metadata traces.")
    parser.add_argument("--device-id", required=True, help="Exact Frida device ID; must be present in approved_device_ids in lab_scope.json")
    parser.add_argument("--pid", type=int, required=True, help="Exact already-running process ID on that device")
    parser.add_argument("--class-name", required=True, help="Exact application class to instrument")
    parser.add_argument("--method-name", required=True, help="Exact method on that class")
    parser.add_argument("--trace-id", required=True, help="Trace ID shared with the test app's X-OS29-Trace-ID header")
    parser.add_argument("--scope", default=str(ROOT / "config" / "lab_scope.json"))
    parser.add_argument("--db", default=str(ROOT / "data" / "os29.db"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    policy = ScopePolicy(args.scope)
    try:
        import frida
    except ImportError:
        raise SystemExit("Frida Python bindings are unavailable in this interpreter.")
    device_decision = policy.check_device(args.device_id)
    if not device_decision["allowed"]:
        raise SystemExit(
            f"Frida device refused: {device_decision['reason']}; add the exact device ID to approved_device_ids first."
        )
    try:
        device = frida.get_device_manager().get_device(args.device_id, timeout=5)
    except Exception as exc:
        raise SystemExit(f"Approved Frida device could not be resolved: {type(exc).__name__}")
    processes = [p for p in device.enumerate_processes() if int(p.pid) == args.pid]
    if not processes:
        raise SystemExit(f"PID {args.pid} is not visible on approved device {args.device_id}; no attach was attempted.")
    process = processes[0]
    decision = policy.check_process(process.name)
    if not decision["allowed"]:
        raise SystemExit(
            f"Frida attach refused: process name {process.name!r} is not in approved_process_names in {args.scope}"
        )
    if not args.trace_id or len(args.trace_id) > 128:
        raise SystemExit("A non-empty trace ID of at most 128 characters is required.")

    store = Store(args.db)
    script_path = ROOT / "integrations" / "frida" / "os29_trace.js"
    source = script_path.read_text(encoding="utf-8")
    session = None
    script = None

    def on_message(message, _data):
        if message.get("type") != "send":
            # Do not print script errors or message data that may contain target-app content.
            print("FRIDA_MESSAGE_TYPE", message.get("type", "unknown"), file=sys.stderr)
            return
        payload = message.get("payload", {})
        if not isinstance(payload, dict) or payload.get("type") != "os29.trace":
            print("FRIDA_NON_TRACE_MESSAGE_IGNORED", file=sys.stderr)
            return
        try:
            event = TraceEvent.from_dict(payload["event"])
            result = store.record_event(event)
            print(json.dumps({"stored": True, **result}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"stored": False, "error_type": type(exc).__name__}), file=sys.stderr)

    try:
        session = device.attach(args.pid)
        script = session.create_script(source)
        script.on("message", on_message)
        script.load()
        script.exports_sync.settraceid(args.trace_id)
        result = script.exports_sync.configure({"className": args.class_name, "methodName": args.method_name})
        print(json.dumps({
            "status": "attached",
            "pid": args.pid,
            "process_name": process.name,
            "class_name": result.get("className"),
            "method_name": result.get("methodName"),
            "hooked_overloads": result.get("hooked_overloads"),
            "trace_id": args.trace_id,
            "mode": "metadata_only",
        }))
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("FRIDA_TRACE_STOP_REQUESTED")
    finally:
        if script is not None:
            try:
                script.unload()
            except Exception:
                pass
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass


if __name__ == "__main__":
    main()