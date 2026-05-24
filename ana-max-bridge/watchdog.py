"""Safety watchdog for ANA MAX bridge calls."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WatchdogVerdict:
    allowed: bool
    reason: str = ""


class BridgeWatchdog:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.local_dev = bool(self.config.get("local_dev", False))
        safety = self.config.get("watchdog", {})
        self.blocked_tools = set(safety.get("blocked_tools", []))
        self.max_payload_bytes = int(safety.get("max_payload_bytes", 200000))
        self.block_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in safety.get(
                "blocked_patterns",
                [
                    r"\bgit\s+reset\s+--hard\b",
                    r"\bRemove-Item\b.*\s-Recurse\b",
                    r"\brm\s+-rf\b",
                    r"\bformat\s+[a-z]:",
                    r"\bshutdown\b",
                ],
            )
        ]
        self.blocked_calls = 0
        self.checked_calls = 0
        self.last_check = None

    def validate_call(self, tool_name: str | None, params: Dict[str, Any]) -> WatchdogVerdict:
        self.checked_calls += 1
        self.last_check = time.time()
        if not tool_name:
            self.blocked_calls += 1
            return WatchdogVerdict(False, "Missing tool name")
        if tool_name in self.blocked_tools:
            self.blocked_calls += 1
            return WatchdogVerdict(False, f"Tool is blocked by bridge policy: {tool_name}")

        serialized = repr(params)
        if len(serialized.encode("utf-8", errors="ignore")) > self.max_payload_bytes:
            self.blocked_calls += 1
            return WatchdogVerdict(False, "Request payload is too large")

        for pattern in self.block_patterns:
            if pattern.search(serialized):
                self.blocked_calls += 1
                return WatchdogVerdict(False, f"Request matched blocked pattern: {pattern.pattern}")

        return WatchdogVerdict(True)

    def validate_response(self, tool_name: str | None, response: Dict[str, Any]) -> WatchdogVerdict:
        serialized = repr(response)
        if len(serialized.encode("utf-8", errors="ignore")) > self.max_payload_bytes * 2:
            return WatchdogVerdict(False, f"Response from {tool_name} is too large")
        return WatchdogVerdict(True)

    def should_report_auth_warning(self) -> bool:
        return not self.local_dev

    def snapshot(self) -> Dict[str, Any]:
        return {
            "local_dev": self.local_dev,
            "suppress_auth_warnings": self.local_dev,
            "checked_calls": self.checked_calls,
            "blocked_calls": self.blocked_calls,
            "blocked_tools": sorted(self.blocked_tools),
            "max_payload_bytes": self.max_payload_bytes,
            "last_check": self.last_check,
        }
