"""ANA MAX session lifecycle orchestration.

This module is intentionally small: it coordinates existing tools instead of
duplicating their behavior. The lifecycle is:

start -> wake -> recommend -> rest

`wake` has an explicit first-run branch so agents do not silently start blind
when no REM Sleep report exists yet. `rest` defaults to an analyze-only preview
and writes persistent REM output only when `consolidate=True`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

ANA_ROOT = Path(__file__).resolve().parents[1]
if str(ANA_ROOT) not in sys.path:
    sys.path.insert(0, str(ANA_ROOT))


class SessionLifecycle:
    """Coordinate ANA MAX session startup, wake context, routing, and rest."""

    def __init__(self, root: Optional[Path] = None, tools: Optional[Mapping[str, Any]] = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        self.docs_dir = self.root / "docs"
        self.memory_dir = self.root / "memory"
        self.manifest_path = self.memory_dir / "session_manifest.json"
        self.tools = dict(tools or {})

    def start(self) -> Dict[str, Any]:
        """Run safe health and wake context for a new runtime session."""
        health = self._execute_tool("tool_healthcheck", scope="safe")
        wake = self.wake()
        manifest = self._write_manifest(
            {
                "status": "started",
                "phase": "start",
                "health": self._compact_tool_result(health),
                "wake": self._compact_wake(wake),
            }
        )
        return {
            "schema": "ana.session_lifecycle.v1",
            "phase": "start",
            "health": self._compact_tool_result(health),
            "wake": wake,
            "manifest": str(manifest),
            "success": self._tool_success(health),
        }

    def wake(self) -> Dict[str, Any]:
        """Load last REM context, or create an explicit first-run manifest."""
        latest_rem = self._latest_rem_report()
        current_handoff = self.docs_dir / "CURRENT_SESSION_HANDOFF.md"

        if latest_rem is None:
            awareness = self._execute_tool(
                "workspace_situational_awareness",
                include_git=True,
                include_uia=False,
                include_errors=True,
            )
            manifest = self._write_manifest(
                {
                    "status": "first_run",
                    "phase": "wake",
                    "source": "fresh_start",
                    "reason": "No REM Sleep report was found.",
                    "workspace_situational_awareness": self._compact_tool_result(awareness),
                    "next_action": "Ask agent_coach action=recommend before the first risky action.",
                }
            )
            return {
                "schema": "ana.session_lifecycle.v1",
                "phase": "wake",
                "status": "first_run",
                "source": "fresh_start",
                "message": "No REM Sleep report found; captured fresh workspace awareness.",
                "workspace_situational_awareness": self._compact_tool_result(awareness),
                "manifest": str(manifest),
                "success": self._tool_success(awareness),
            }

        rem_text = latest_rem.read_text(encoding="utf-8", errors="replace")
        handoff_text = (
            current_handoff.read_text(encoding="utf-8", errors="replace")
            if current_handoff.exists()
            else ""
        )
        manifest = self._write_manifest(
            {
                "status": "resumed",
                "phase": "wake",
                "source": "last_rem",
                "last_rem_report": str(latest_rem),
                "last_rem_excerpt": self._excerpt(rem_text),
                "current_handoff": str(current_handoff) if current_handoff.exists() else "",
                "current_handoff_excerpt": self._excerpt(handoff_text),
                "next_action": "Use agent_coach action=recommend with the current task before acting.",
            }
        )
        return {
            "schema": "ana.session_lifecycle.v1",
            "phase": "wake",
            "status": "resumed",
            "source": "last_rem",
            "last_rem_report": str(latest_rem),
            "last_rem_excerpt": self._excerpt(rem_text, 1200),
            "current_handoff": str(current_handoff) if current_handoff.exists() else "",
            "manifest": str(manifest),
            "success": True,
        }

    def recommend(self, task: str, error: str = "", max_tools: int = 5) -> Dict[str, Any]:
        """Ask agent_coach for the next tool stack."""
        result = self._execute_tool(
            "agent_coach",
            action="recommend",
            task=task,
            error=error,
            max_tools=max_tools,
            include_prompt=False,
        )
        return {
            "schema": "ana.session_lifecycle.v1",
            "phase": "recommend",
            "task": task,
            "recommendation": self._compact_tool_result(result),
            "success": self._tool_success(result),
        }

    def rest(self, consolidate: bool = False, save_memory: bool = True) -> Dict[str, Any]:
        """Preview REM Sleep by default; persist only with consolidate=True."""
        action = "consolidate" if consolidate else "analyze"
        result = self._execute_tool(
            "session_rem_sleep",
            action=action,
            checkpoint_limit=8,
            telemetry_limit=160,
            lesson_limit=25,
            save_memory=save_memory,
        )
        compact = self._compact_tool_result(result)
        payload = {
            "schema": "ana.session_lifecycle.v1",
            "phase": "rest",
            "action": action,
            "rem_sleep": compact,
            "success": self._tool_success(result),
        }
        if not consolidate:
            payload["write_status"] = "preview_only"
            payload["operator_prompt"] = "REM Sleep analysis is ready. Save it with rest(consolidate=True)?"
        else:
            payload["write_status"] = "consolidated"
        return payload

    def _execute_tool(self, name: str, **kwargs: Any) -> Any:
        tool = self.tools.get(name)
        if tool is None:
            tool = self._default_tool(name)
        return tool.execute(**kwargs)

    def _default_tool(self, name: str) -> Any:
        if name == "tool_healthcheck":
            from tools.tool_healthcheck import ToolHealthcheckTool

            return ToolHealthcheckTool()
        if name == "workspace_situational_awareness":
            from tools.workspace_situational_awareness import WorkspaceSituationalAwarenessTool

            return WorkspaceSituationalAwarenessTool()
        if name == "agent_coach":
            from tools.agent_coach_tool import AgentCoachTool

            return AgentCoachTool()
        if name == "session_rem_sleep":
            from tools.session_rem_sleep_tool import SessionRemSleepTool

            return SessionRemSleepTool()
        raise KeyError(f"Unknown lifecycle tool: {name}")

    def _latest_rem_report(self) -> Optional[Path]:
        reports_dir = self.docs_dir / "rem_sleep"
        if not reports_dir.exists():
            return None
        reports = sorted(
            reports_dir.glob("REM_SLEEP_REPORT_*.md"),
            key=lambda path: path.stat().st_mtime,
        )
        return reports[-1] if reports else None

    def _write_manifest(self, payload: Dict[str, Any]) -> Path:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema": "ana.session_manifest.v1",
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            **payload,
        }
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        return self.manifest_path

    def _compact_tool_result(self, result: Any) -> Dict[str, Any]:
        data = getattr(result, "data", None)
        return {
            "success": self._tool_success(result),
            "status": str(getattr(getattr(result, "status", None), "value", getattr(result, "status", ""))),
            "message": str(getattr(result, "message", "") or ""),
            "error": str(getattr(result, "error", "") or ""),
            "data": self._compact_data(data),
        }

    def _compact_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {str(key): self._compact_data(value) for key, value in list(data.items())[:20]}
        if isinstance(data, list):
            return [self._compact_data(item) for item in data[:20]]
        if isinstance(data, str):
            return self._excerpt(data, 2000)
        return data

    def _compact_wake(self, wake: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": wake.get("status"),
            "source": wake.get("source"),
            "message": wake.get("message", ""),
            "last_rem_report": wake.get("last_rem_report", ""),
        }

    def _tool_success(self, result: Any) -> bool:
        if hasattr(result, "is_success"):
            return bool(result.is_success)
        return bool(getattr(result, "success", False))

    def _excerpt(self, text: str, limit: int = 4000) -> str:
        text = (text or "").strip()
        return text[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA MAX session lifecycle manager.")
    parser.add_argument("action", choices=["start", "wake", "recommend", "rest"])
    parser.add_argument("--task", default="", help="Task for action=recommend.")
    parser.add_argument("--error", default="", help="Optional error for action=recommend.")
    parser.add_argument("--max-tools", type=int, default=5)
    parser.add_argument("--consolidate", action="store_true", help="For rest: write REM Sleep report and memory.")
    args = parser.parse_args()

    lifecycle = SessionLifecycle()
    if args.action == "start":
        payload = lifecycle.start()
    elif args.action == "wake":
        payload = lifecycle.wake()
    elif args.action == "recommend":
        payload = lifecycle.recommend(args.task, error=args.error, max_tools=args.max_tools)
    else:
        payload = lifecycle.rest(consolidate=args.consolidate)

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
