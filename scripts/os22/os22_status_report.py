from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "ANA_MAX" / "memory" / "os22_launch_audit_report.json"
RECENT_ERRORS_PATH = ROOT / "ANA_MAX" / "memory" / "recent_errors.jsonl"

RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _color(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def _print_status(label: str, ok: bool, detail: str = "") -> None:
    color = GREEN if ok else RED
    print(f"{_color(label, color)} {detail}")


def _print_warn(label: str, detail: str = "") -> None:
    print(f"{_color(label, YELLOW)} {detail}")


def main() -> int:
    report = _load_json(REPORT_PATH)
    overall = bool(report.get("overall_success"))
    checks = report.get("checks", []) if isinstance(report.get("checks"), list) else []
    failed = [item for item in checks if isinstance(item, dict) and not item.get("success")]
    warnings = [item for item in checks if isinstance(item, dict) and item.get("warnings")]
    recent_errors = _load_json(RECENT_ERRORS_PATH)

    print(_color("ANA MAX OS-22 STATUS", CYAN + BOLD))
    print(f"Root: {ROOT}")
    print(f"Launch audit: {REPORT_PATH}")
    _print_status("Launch audit:", overall, "READY" if overall else "NEEDS ATTENTION")
    if failed:
        print(_color("Failed checks:", RED))
        for item in failed:
            print(f"- {item.get('name')}: {item.get('detail')}")
    else:
        print(_color("Failed checks: none", GREEN))
    if warnings:
        print(_color("Warnings:", YELLOW))
        for item in warnings:
            print(f"- {item}")
    else:
        print(_color("Warnings: none", GREEN))

    if isinstance(recent_errors, dict):
        entries = recent_errors.get("entries", []) if isinstance(recent_errors.get("entries"), list) else []
        if entries:
            print(_color("Recent errors:", YELLOW))
            for entry in entries[-5:]:
                if isinstance(entry, dict):
                    print(f"- {entry.get('timestamp')} [{entry.get('source')}] {entry.get('issue_class')}: {entry.get('message')}")
        else:
            print(_color("Recent errors: none", GREEN))
    elif RECENT_ERRORS_PATH.exists():
        lines = RECENT_ERRORS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            print(_color("Recent errors:", YELLOW))
            for line in lines[-5:]:
                try:
                    entry = json.loads(line)
                    print(f"- {entry.get('timestamp')} [{entry.get('source')}] {entry.get('issue_class')}: {entry.get('message')}")
                except json.JSONDecodeError:
                    print(f"- raw: {line[:160]}")
        else:
            print(_color("Recent errors: none", GREEN))
    else:
        print(_color("Recent errors: none", GREEN))

    print()
    print("Quick commands:")
    print("- lab: chat + live logs")
    print("- logs-errors: live error/warning log window")
    print("- logs-tools: live tool telemetry")
    print("- logs-rag: live RAG telemetry")
    print("- logs-senior: live Senior Engineer Mode handoffs")
    print("- chat: chat only")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
