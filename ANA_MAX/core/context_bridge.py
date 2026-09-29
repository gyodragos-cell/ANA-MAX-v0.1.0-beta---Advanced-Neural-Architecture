"""
ANA MAX - Context Bridge unificat (ANAContextBridge)
=====================================================
Colecteaza contextul OS, tool-uri, watchdog, telemetry, events, erori si metrics
intr-un singur obiect context_snapshot.

Foloseste:
 - CodeContextPackTool, GraphContextPackTool
 - CodeSearchTool
 - WorkspaceSituationalAwarenessTool
 - WindowsInsightTool, WindowsDeepSightTool (daca exista)
 - EventStreamTool
 - Watchdog bus + logs (ana_max.log, planner.log)

Expune: build_context(task_desc) -> dict
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger("context_bridge")

ANA_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ANA_ROOT / "logs"
ANA_MAX_LOG = LOG_DIR / "ana_max.log"
PLANNER_LOG = LOG_DIR / "planner.log"


def _safe_read_tail(log_path: Path, lines: int = 50) -> List[str]:
    try:
        if not log_path.exists():
            return []
        raw = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return raw[-lines:]
    except Exception:
        return []


def _safe_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return {
            "success": bool(result.get("success", result.get("is_success", False))),
            "data": result.get("data"),
            "message": result.get("message", ""),
            "error": result.get("error"),
        }
    is_ok = getattr(result, "is_success", False) or (
        getattr(result, "status", None) and str(getattr(result, "status")).lower() == "success"
    )
    return {
        "success": bool(is_ok),
        "data": getattr(result, "data", None),
        "message": getattr(result, "message", ""),
        "error": getattr(result, "error", str(result) if not is_ok else None),
    }


def _compact(obj: Any, max_len: int = 4000, _depth: int = 0, _max_depth: int = 5) -> Any:
    if _depth > _max_depth:
        try:
            s = json.dumps(obj, ensure_ascii=False, default=str)
        except Exception:
            s = str(obj)
        if len(s) > max_len:
            return {"_truncated_deep": True, "_size": len(s), "_preview": s[:max_len]}
        return obj

    if obj is None or isinstance(obj, (bool, int, float)):
        return obj

    if isinstance(obj, str):
        if len(obj) > max_len:
            return obj[:max_len] + f"\n..._truncated_{len(obj)}"
        return obj

    if isinstance(obj, (list, tuple)):
        items = list(obj)
        total = len(items)
        limit = max(6, min(50, max_len // 80)) if items else 0
        out = [_compact(x, max_len=max_len, _depth=_depth + 1) for x in items[:limit]]
        if total > limit:
            out.append({"_list_remaining": total - limit, "_list_total": total})
        return out

    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in list(obj.items())[:80]:
            out[str(k)] = _compact(v, max_len=max_len, _depth=_depth + 1)
        if len(obj) > 80:
            out["_dict_remaining"] = len(obj) - 80
        return out

    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        return {"_truncated": True, "_size": len(s), "_preview": s[:max_len]}
    return obj


class ANAContextBridge:
    """Context Bridge: colecteaza si normalizeaza contextul complet."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        self._registry = None
        self._code_ctx = None
        self._graph_ctx = None
        self._code_search = None
        self._workspace_awareness = None
        self._windows_insight = None
        self._windows_deep_sight = None
        self._event_stream = None
        self._bus = None
        self._init_components()

    def _init_components(self) -> None:
        try:
            from tools.base import registry
            self._registry = registry
        except Exception as exc:
            logger.warning("ContextBridge: registry unavailable - %s", exc)

        try:
            from tools.code_context_pack_tool import CodeContextPackTool
            self._code_ctx = CodeContextPackTool()
        except Exception as exc:
            logger.debug("ContextBridge: CodeContextPackTool unavailable - %s", exc)

        try:
            from tools.graph_context_pack_tool import GraphContextPackTool
            self._graph_ctx = GraphContextPackTool()
        except Exception as exc:
            logger.debug("ContextBridge: GraphContextPackTool unavailable - %s", exc)

        try:
            from tools.code_search import CodeSearchTool
            self._code_search = CodeSearchTool()
        except Exception as exc:
            logger.debug("ContextBridge: CodeSearchTool unavailable - %s", exc)

        try:
            from tools.workspace_situational_awareness import WorkspaceSituationalAwarenessTool
            self._workspace_awareness = WorkspaceSituationalAwarenessTool()
        except Exception as exc:
            logger.debug("ContextBridge: WorkspaceSituationalAwareness unavailable - %s", exc)

        try:
            from tools.windows_insight_tool import WindowsInsightTool
            self._windows_insight = WindowsInsightTool()
        except Exception as exc:
            logger.debug("ContextBridge: WindowsInsightTool unavailable - %s", exc)

        try:
            from tools.windows_deep_sight import WindowsDeepSightTool
            self._windows_deep_sight = WindowsDeepSightTool()
        except Exception as exc:
            logger.debug("ContextBridge: WindowsDeepSightTool unavailable - %s", exc)

        try:
            from tools.event_stream_tool import EventStreamTool
            self._event_stream = EventStreamTool()
        except Exception as exc:
            logger.debug("ContextBridge: EventStreamTool unavailable - %s", exc)

        try:
            from tools.watchdog_bus import bus as watchdog_bus
            self._bus = watchdog_bus
            try:
                self._bus.start()
            except Exception:
                pass
        except Exception as exc:
            logger.debug("ContextBridge: watchdog_bus unavailable - %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_context(self, task_desc: str, memory_cortex: Any = None) -> Dict[str, Any]:
        """Construiteste context_snapshot complet (compact si normalizat)."""
        snapshot: Dict[str, Any] = {
            "task_desc": task_desc or "",
            "built_at": datetime.utcnow().isoformat() + "Z",
            "sources": [],
            "files": {},
            "processes": {},
            "events": [],
            "errors": [],
            "metrics": {},
        }
        if not self.enabled:
            snapshot["sources"].append("cortex_disabled")
            return snapshot

        t0 = time.perf_counter()

        self._collect_workspace_state(snapshot, task_desc)
        self._collect_code_context(snapshot, task_desc)
        self._collect_graph_context(snapshot, task_desc)
        self._collect_windows_state(snapshot)
        self._collect_events(snapshot)
        self._collect_log_errors(snapshot)
        self._collect_metrics(snapshot)
        self._collect_memory_context(snapshot, task_desc, memory_cortex)

        snapshot["build_ms"] = round(1000.0 * (time.perf_counter() - t0), 2)
        snapshot = _compact(snapshot, max_len=12000)  # type: ignore[assignment]
        logger.info(
            "CONTEXT_BRIDGE build task_len=%d sources=%d ms=%.2f",
            len(task_desc or ""),
            len(snapshot.get("sources", []) if isinstance(snapshot, dict) else []),
            snapshot.get("build_ms", 0.0) if isinstance(snapshot, dict) else 0.0,
        )
        self._publish_bus("context_bridge", "built", {"sources": snapshot.get("sources", []) if isinstance(snapshot, dict) else []})
        return snapshot if isinstance(snapshot, dict) else {"_error": "compact_failed", "task_desc": task_desc}

    # ------------------------------------------------------------------
    # Collectors
    # ------------------------------------------------------------------
    def _collect_workspace_state(self, snap: Dict[str, Any], task_desc: str) -> None:
        if self._workspace_awareness is None:
            return
        try:
            res = _safe_result(self._workspace_awareness.safe_execute(include_uia=True, include_errors=True))
            data = res.get("data")
            if data is not None:
                snap["workspace"] = data
                snap["sources"].append("workspace_situational_awareness")
                if isinstance(data, dict):
                    for err in list((data.get("log_signals") or {}).get("recent_errors") or [])[:5]:
                        snap["errors"].append({"source": "watchdog_logs", "error": str(err)})
        except Exception as exc:
            logger.debug("ContextBridge: workspace collect failed - %s", exc)

    def _collect_code_context(self, snap: Dict[str, Any], task_desc: str) -> None:
        if self._code_ctx is None or not task_desc:
            return
        try:
            res = _safe_result(self._code_ctx.safe_execute(task=task_desc, limit=8))
            snap["files"]["code_context"] = res.get("data") or res.get("message")
            if res.get("success"):
                snap["sources"].append("code_context_pack")
        except Exception as exc:
            logger.debug("ContextBridge: code context failed - %s", exc)

    def _collect_graph_context(self, snap: Dict[str, Any], task_desc: str) -> None:
        if self._graph_ctx is None or not task_desc:
            return
        try:
            res = _safe_result(self._graph_ctx.safe_execute(action="query", query=task_desc, limit=6))
            snap["files"]["graph_context"] = res.get("data") or res.get("message")
            if res.get("success"):
                snap["sources"].append("graph_context_pack")
        except Exception as exc:
            logger.debug("ContextBridge: graph context failed - %s", exc)

    def _collect_windows_state(self, snap: Dict[str, Any]) -> None:
        info = {}
        if self._windows_insight is not None:
            try:
                res = _safe_result(self._windows_insight.safe_execute(operation="system_snapshot"))
                if res.get("success"):
                    data = res.get("data")
                    if isinstance(data, dict):
                        info["insight"] = data
                        snap["processes"] = data.get("processes") or data.get("snapshot") or snap["processes"]
                        snap["sources"].append("windows_insight")
            except Exception as exc:
                logger.debug("ContextBridge: windows insight failed - %s", exc)
        if self._windows_deep_sight is not None:
            try:
                res = _safe_result(self._windows_deep_sight.safe_execute(operation="snapshot"))
                if res.get("success"):
                    info["deep_sight"] = res.get("data") or res.get("message")
                    snap["sources"].append("windows_deep_sight")
            except Exception as exc:
                logger.debug("ContextBridge: windows deep sight unavailable - %s", exc)
        if info:
            snap["os"] = info

    def _collect_events(self, snap: Dict[str, Any]) -> None:
        if self._event_stream is None:
            return
        try:
            res = _safe_result(self._event_stream.safe_execute(action="timeline", limit=20))
            if res.get("success"):
                data = res.get("data")
                if isinstance(data, list):
                    snap["events"] = data[:20]
                    snap["sources"].append("event_stream")
        except Exception as exc:
            logger.debug("ContextBridge: event stream failed - %s", exc)

    def _collect_log_errors(self, snap: Dict[str, Any]) -> None:
        seen = set()
        for label, path in (("ana_max", ANA_MAX_LOG), ("planner", PLANNER_LOG)):
            for line in reversed(_safe_read_tail(path, lines=200)):
                low = line.lower()
                if "error" in low or "exception" in low or "traceback" in low or "fail" in low:
                    key = line[-160:]
                    if key in seen:
                        continue
                    seen.add(key)
                    snap["errors"].append({"source": f"log:{label}", "line": line.strip()[:240]})
                    if len(snap["errors"]) >= 20:
                        break
            if len(snap["errors"]) >= 20:
                break
        if snap["errors"]:
            snap["sources"].append("log_tail")

    def _collect_metrics(self, snap: Dict[str, Any]) -> None:
        try:
            import psutil  # type: ignore
            snap["metrics"]["cpu_percent"] = psutil.cpu_percent(interval=0.2)
            mem = psutil.virtual_memory()
            snap["metrics"]["memory_mb_total"] = round(mem.total / (1024 * 1024), 1)
            snap["metrics"]["memory_mb_available"] = round(mem.available / (1024 * 1024), 1)
            snap["metrics"]["memory_percent"] = mem.percent
            try:
                disk = psutil.disk_usage(str(ANA_ROOT))
                snap["metrics"]["disk_gb_free"] = round(disk.free / (1024 ** 3), 2)
                snap["metrics"]["disk_percent"] = disk.percent
            except Exception:
                pass
            snap["sources"].append("native_metrics")
        except Exception as exc:
            logger.debug("ContextBridge: metrics unavailable - %s", exc)

    def _collect_memory_context(self, snap: Dict[str, Any], task_desc: str, memory_cortex: Any) -> None:
        if memory_cortex is None or not task_desc:
            return
        try:
            mem_hits = memory_cortex.query_memory(task_desc, top_k=5)
            if mem_hits:
                snap["memory_hits"] = mem_hits
                snap["sources"].append("memory_cortex")
        except Exception as exc:
            logger.debug("ContextBridge: memory context failed - %s", exc)

    def _publish_bus(self, source: str, event_type: str, data: Dict[str, Any]) -> None:
        if self._bus is None:
            return
        try:
            self._bus.publish(source=source, event_type=event_type, data=data)
        except Exception:
            pass


_bridge_singleton: Optional[ANAContextBridge] = None


def get_context_bridge(config: Optional[Dict[str, Any]] = None) -> ANAContextBridge:
    global _bridge_singleton
    if _bridge_singleton is None:
        _bridge_singleton = ANAContextBridge(config=config)
    return _bridge_singleton
