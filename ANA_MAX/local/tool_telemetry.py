from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Iterable


TELEMETRY_PATH = Path(__file__).with_name("tool_telemetry.log")


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


@dataclass(frozen=True)
class ToolEvent:
    ts: str
    tool_name: str
    args: dict[str, Any]
    result_preview: str
    duration_ms: float
    status: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=True, sort_keys=True)


def log_tool_event(
    tool_name: str,
    args: dict[str, Any],
    result: str,
    duration_ms: float,
    *,
    status: str = "success",
) -> None:
    try:
        TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        event = ToolEvent(
            ts=datetime.now(timezone.utc).isoformat(),
            tool_name=_ascii_text(tool_name),
            args=dict(args or {}),
            result_preview=_ascii_text(result)[:200],
            duration_ms=round(float(duration_ms), 3),
            status=_ascii_text(status) or "success",
        )
        with TELEMETRY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(event.to_json() + "\n")
    except Exception:
        pass


def read_tool_telemetry(
    path: Path | None = None,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    telemetry_path = Path(path or TELEMETRY_PATH)
    if not telemetry_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    lines = telemetry_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-max(1, int(limit)) :]:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def read_event_stream_tool_telemetry(*, limit: int = 200, hours: int = 24) -> list[dict[str, Any]]:
    try:
        from ANA_MAX.core.event_stream import EventType, get_event_stream
    except Exception:
        return []

    try:
        stream = get_event_stream()
        events = stream.query_events(
            start_time=time.time() - (max(1, int(hours)) * 3600),
            limit=max(1, int(limit)) * 2,
        )
    except Exception:
        return []

    telemetry: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type", ""))
        if event_type not in {EventType.TOOL_RESULT.value, EventType.ERROR.value, EventType.TOOL_CALL.value}:
            continue
        data = event.get("data") or {}
        metadata = event.get("metadata") or {}
        if not isinstance(data, dict):
            data = {"value": data}
        if not isinstance(metadata, dict):
            metadata = {}
        telemetry.append(
            {
                "timestamp": datetime.fromtimestamp(float(event.get("timestamp", 0))).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "tool": str(event.get("source") or data.get("tool") or data.get("tool_name") or "unknown"),
                "args": dict(data.get("args") or data.get("arguments") or {}),
                "latency_sec": float(event.get("duration") or 0.0),
                "status": "success" if bool(event.get("success", True)) else "error",
                "error": data.get("error") or metadata.get("error"),
                "event_type": event_type,
            }
        )
    return telemetry[-max(1, int(limit)) :]


def merge_tool_telemetry(
    primary: Iterable[dict[str, Any]],
    secondary: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in [*primary, *secondary]:
        if not isinstance(entry, dict):
            continue
        key = json.dumps(entry, sort_keys=True, ensure_ascii=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    return merged


def summarize_tool_telemetry(entries: Iterable[dict[str, Any]]) -> dict[str, Any]:
    entries_list = [entry for entry in entries if isinstance(entry, dict)]
    by_tool = Counter()
    by_status = Counter()
    by_event_type = Counter()
    for entry in entries_list:
        tool_name = entry.get("tool") or entry.get("tool_name") or "unknown"
        by_tool[str(tool_name)] += 1
        by_status[str(entry.get("status") or "unknown")] += 1
        if entry.get("event_type"):
            by_event_type[str(entry.get("event_type"))] += 1
    return {
        "schema": "ana.local.tool_telemetry_summary.v1",
        "count": len(entries_list),
        "by_tool": dict(by_tool.most_common()),
        "by_status": dict(by_status.most_common()),
        "by_event_type": dict(by_event_type.most_common()),
        "sources": {
            "jsonl": any("event_type" not in entry for entry in entries_list),
            "event_stream": any("event_type" in entry for entry in entries_list),
        },
    }


def load_tool_telemetry(
    path: Path | None = None,
    *,
    limit: int = 200,
    include_event_stream: bool = True,
) -> list[dict[str, Any]]:
    entries = read_tool_telemetry(path=path, limit=limit)
    if include_event_stream:
        event_entries = read_event_stream_tool_telemetry(limit=limit)
        entries = merge_tool_telemetry(entries, event_entries)
    return entries[-max(1, int(limit)) :]


def build_tool_telemetry_report(
    path: Path | None = None,
    *,
    limit: int = 200,
    include_event_stream: bool = True,
) -> dict[str, Any]:
    entries = load_tool_telemetry(path=path, limit=limit, include_event_stream=include_event_stream)
    return {
        "schema": "ana.local.tool_telemetry_report.v1",
        "entries": entries,
        "summary": summarize_tool_telemetry(entries),
    }
