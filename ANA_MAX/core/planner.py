"""
ANA MAX - Planner intern (ANAPlanner)
======================================
Modul Hermes-style de planificare si executie secventiala a task-urilor.

Primeste: task_desc, context_snapshot, memory_state
Genereaza: lista de pasi (steps), fiecare cu description, tool_name, arguments, checks
Executa: foloseste ToolRouterTool, ToolHealer, AgentCoachTool
Logheaza: in logs/planner.log si pe watchdog_bus
Expune: execute_task(task_desc) -> {success, output, steps, errors}
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


logger = logging.getLogger("planner")

ANA_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ANA_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PLANNER_LOG = LOG_DIR / "planner.log"

if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(PLANNER_LOG) for h in logger.handlers):
    _fh = logging.FileHandler(PLANNER_LOG, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)


class Step(TypedDict, total=False):
    step_id: str
    description: str
    tool_name: Optional[str]
    arguments: Dict[str, Any]
    checks: List[str]
    status: str
    result: Any
    error: Optional[str]
    duration_ms: float


class PlannerResult(TypedDict):
    success: bool
    output: str
    steps: List[Step]
    errors: List[str]
    task_id: str
    started_at: str
    finished_at: str


def _tool_safe_result(result: Any) -> Dict[str, Any]:
    """Normalize ToolResult or dict into a plain dict."""
    if isinstance(result, dict):
        return {
            "success": bool(result.get("success", result.get("is_success", False))),
            "data": result.get("data"),
            "message": result.get("message", ""),
            "error": result.get("error"),
        }
    is_ok = getattr(result, "is_success", False) or getattr(result, "status", None) and str(getattr(result, "status")).lower() == "success"
    return {
        "success": bool(is_ok),
        "data": getattr(result, "data", None),
        "message": getattr(result, "message", ""),
        "error": getattr(result, "error", str(result) if not is_ok else None),
    }


class ANAPlanner:
    """Planificator ANA: genereaza pasi, ii executa, logheaza totul."""

    MAX_STEPS = 20
    MAX_RETRY_PER_STEP = 2
    STEP_TIMEOUT_S = 120.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        self._registry = None
        self._router = None
        self._coach = None
        self._healer = None
        self._bus = None
        self._memory = None
        self._init_components()

    def _init_components(self) -> None:
        registry_ref = None
        try:
            from tools.base import registry
            registry_ref = registry
            self._registry = registry_ref
        except Exception as exc:
            logger.warning("Planner: ToolRegistry unavailable - %s", exc)

        if registry_ref is not None and len(getattr(registry_ref, "_tools", {})) < 5:
            try:
                self._ensure_minimal_tools_registered(registry_ref)
            except Exception as exc:
                logger.debug("Planner: minimal tools register skipped - %s", exc)

        try:
            from tools.tool_router_tool import ToolRouterTool
            if registry_ref is not None and not registry_ref.get("tool_router"):
                try:
                    registry_ref.register(ToolRouterTool())
                except Exception:
                    pass
            self._router = ToolRouterTool()
        except Exception as exc:
            logger.warning("Planner: ToolRouterTool unavailable - %s", exc)

        try:
            from tools.agent_coach_tool import AgentCoachTool
            if registry_ref is not None and not registry_ref.get("agent_coach"):
                try:
                    registry_ref.register(AgentCoachTool())
                except Exception:
                    pass
            self._coach = AgentCoachTool()
        except Exception as exc:
            logger.warning("Planner: AgentCoachTool unavailable - %s", exc)

        try:
            from tools.live_tool_healer import LiveToolHealer
            if registry_ref is not None and not registry_ref.get("live_tool_healer"):
                try:
                    registry_ref.register(LiveToolHealer())
                except Exception:
                    pass
            self._healer = LiveToolHealer()
        except Exception as exc:
            logger.warning("Planner: LiveToolHealer unavailable - %s", exc)

        try:
            from tools.watchdog_bus import bus as watchdog_bus
            self._bus = watchdog_bus
            try:
                self._bus.start()
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Planner: watchdog_bus unavailable - %s", exc)

    def _ensure_minimal_tools_registered(self, registry_ref) -> None:
        minimal = [
            ("tools.files", "FilesTool"),
            ("tools.terminal_tool", "TerminalTool"),
            ("tools.system", "SystemTool"),
            ("tools.smart_search_tool", "SmartSearchTool"),
            ("tools.code_search", "CodeSearchTool"),
            ("tools.file_patch_tool", "FilePatchTool"),
            ("tools.project_navigator_tool", "ProjectNavigatorTool"),
            ("tools.code_context_pack_tool", "CodeContextPackTool"),
            ("tools.graph_context_pack_tool", "GraphContextPackTool"),
            ("tools.workspace_situational_awareness", "WorkspaceSituationalAwarenessTool"),
            ("tools.error_radar_tool", "ErrorRadarTool"),
            ("tools.tool_healthcheck", "ToolHealthcheckTool"),
            ("tools.memory_tool", "MemoryTool"),
            ("tools.vector_memory_tool", "VectorMemoryTool"),
            ("tools.event_stream_tool", "EventStreamTool"),
            ("tools.windows_insight_tool", "WindowsInsightTool"),
            ("tools.qa_tool", "QATool"),
            # Tooluri critice pentru a nu lucra orbeste
            ("tools.large_file_reader", "LargeFileReaderTool"),
            ("tools.desktop_capture", "DesktopCaptureTool"),
            ("tools.ocr_tool", "OCRTool"),
        ]
        import importlib
        for mod_path, cls_name in minimal:
            if registry_ref.get(cls_name.lower().replace("tool", "")) or registry_ref.get(mod_path.split(".")[-1]):
                continue
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                inst = cls()
                registry_ref.register(inst)
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute_task(
        self,
        task_desc: str,
        context_snapshot: Optional[Dict[str, Any]] = None,
        memory_state: Optional[Dict[str, Any]] = None,
    ) -> PlannerResult:
        task_id = f"tsk_{uuid.uuid4().hex[:10]}"
        started_at = datetime.utcnow().isoformat() + "Z"
        logger.info("PLANNER START task_id=%s task=%s", task_id, (task_desc or "")[:120])
        self._publish_bus("planner", "task_start", {"task_id": task_id, "task": task_desc[:200]})

        result: PlannerResult = {
            "success": False,
            "output": "",
            "steps": [],
            "errors": [],
            "task_id": task_id,
            "started_at": started_at,
            "finished_at": "",
        }

        if not self.enabled:
            result["output"] = "ANAPlanner este dezactivat prin config."
            result["errors"].append("planner_disabled")
            result["success"] = False
            result["finished_at"] = datetime.utcnow().isoformat() + "Z"
            return result

        if not task_desc or not task_desc.strip():
            result["output"] = "Task gol."
            result["errors"].append("empty_task")
            result["finished_at"] = datetime.utcnow().isoformat() + "Z"
            return result

        try:
            steps = self._generate_steps(task_desc, context_snapshot, memory_state)
            result["steps"] = steps
            logger.info("PLANNER plan task_id=%s steps=%d", task_id, len(steps))

            for step in steps:
                self._execute_step(step, task_id, context_snapshot, memory_state)
                if step.get("status") == "failed" and not self._is_step_recoverable(step):
                    result["errors"].append(f"step_failed:{step.get('step_id')}:{step.get('error')}")
                    if not self._should_continue_after_failure(step, result):
                        break

            result["success"] = all(s.get("status") == "success" for s in result["steps"]) or (
                len(result["steps"]) > 0 and result["steps"][-1].get("status") == "success"
            )
            result["output"] = self._synthesize_output(task_desc, result["steps"])

        except Exception as exc:
            logger.exception("PLANNER FATAL task_id=%s", task_id)
            result["errors"].append(f"planner_exception:{exc}")
            result["output"] = f"Planner a esuat: {exc}"
            result["success"] = False

        result["finished_at"] = datetime.utcnow().isoformat() + "Z"
        logger.info(
            "PLANNER END task_id=%s success=%s steps=%d errors=%d",
            task_id, result["success"], len(result["steps"]), len(result["errors"]),
        )
        self._publish_bus(
            "planner",
            "task_end",
            {"task_id": task_id, "success": result["success"], "errors": result["errors"]},
        )
        return result

    # ------------------------------------------------------------------
    # Step generation
    # ------------------------------------------------------------------
    def _generate_steps(
        self,
        task_desc: str,
        context_snapshot: Optional[Dict[str, Any]],
        memory_state: Optional[Dict[str, Any]],
    ) -> List[Step]:
        """Foloseste ToolRouter + coach pentru a sugera un stack de tools."""
        steps: List[Step] = []

        routing_tools: List[str] = []
        headline = ""
        if self._router:
            try:
                router_res = _tool_safe_result(self._router.safe_execute(query=task_desc, mode="compact"))
                if router_res.get("success"):
                    data = router_res.get("data") or {}
                    if isinstance(data, dict):
                        routing_tools = list(data.get("recommended_tools") or data.get("tool_stack") or [])
                        headline = str(data.get("headline") or data.get("router_headline") or "")
            except Exception as exc:
                logger.warning("Planner: router failed - %s", exc)

        if not routing_tools:
            routing_tools = self._heuristic_tools(task_desc)

        coach_notes = ""
        if self._coach:
            try:
                coach_res = _tool_safe_result(self._coach.safe_execute(action="recommend", task=task_desc))
                if coach_res.get("success"):
                    cdata = coach_res.get("data") or {}
                    if isinstance(cdata, dict):
                        coach_notes = str(cdata.get("headline") or cdata.get("guidance") or "")
            except Exception as exc:
                logger.warning("Planner: coach failed - %s", exc)

        desc_prefix = (
            (f"{headline}. " if headline else "")
            + (f"Note: {coach_notes}. " if coach_notes else "")
        ).strip()

        if not routing_tools:
            steps.append(self._make_step(
                description=f"{desc_prefix} Raspuns conversational la task fara tool-uri.",
                tool_name=None,
                arguments={"task": task_desc},
                checks=["Raspuns text furnizat"],
            ))
            return steps

        seen = set()
        for tool_name in routing_tools:
            if not tool_name or tool_name in seen:
                continue
            seen.add(tool_name)
            if len(steps) >= self.MAX_STEPS:
                break
            args = self._guess_args(tool_name, task_desc, context_snapshot)
            steps.append(self._make_step(
                description=f"{desc_prefix} Executa tool-ul '{tool_name}' pentru: {(task_desc or '')[:160]}",
                tool_name=tool_name,
                arguments=args,
                checks=[
                    f"Tool '{tool_name}' trebuie sa intoarca success.",
                    "Nu trebuie sa apara erori critice.",
                ],
            ))
        return steps

    def _heuristic_tools(self, task_desc: str) -> List[str]:
        t = (task_desc or "").lower()
        picks: List[str] = []
        if any(k in t for k in ("cauta", "search", "grep", "unde", "gaseste")):
            picks += ["smart_search", "code_search"]
        if any(k in t for k in ("citeste", "read", "lista", "list", "fisier", "file")):
            picks.append("file_operations")
        if any(k in t for k in ("ruleaza", "run", "executa", "terminal", "cmd", "powershell")):
            picks.append("terminal")
        if any(k in t for k in ("cod", "code", "analiza", "analyze", " proiect")):
            picks += ["code", "project_navigator", "code_context_pack"]
        if any(k in t for k in ("eroare", "error", "bug", "debug", "esuat")):
            picks += ["error_radar", "tool_healthcheck", "debugger"]
        if any(k in t for k in ("ecran", "screen", "captura", "screenshot", "ocr", "text poza", "window", "fereastra")):
            picks += ["desktop_capture", "ocr_tool", "window_manager"]
        if any(k in t for k in ("memorie", "memory", "cunoastere", "knowledge")):
            picks += ["ana_memory", "vector_memory"]
        if any(k in t for k in ("proces", "process", "pid", "sistem", "system")):
            picks += ["system", "windows_insight", "windows_deep_sight"]
        if not picks:
            picks = ["tool_router", "agent_coach", "smart_search"]
        return picks

    def _guess_args(self, tool_name: str, task_desc: str, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        tname = (tool_name or "").lower()
        args: Dict[str, Any] = {"task": task_desc or "", "query": task_desc or ""}
        extracted_path = self._extract_path_from_task(task_desc)
        if tname in {"terminal"}:
            args.setdefault("action", "run")
            cmd = task_desc or ""
            if extracted_path:
                cmd = f"{task_desc}\nPath curent detectat: {extracted_path}"
            args.setdefault("command", cmd)
        elif tname in {"file_operations", "files"}:
            op = "list"
            t_low = (task_desc or "").lower()
            if any(k in t_low for k in ("citeste", "read", "continut", "content")):
                op = "read"
            elif any(k in t_low for k in ("cauta", "grep", "search", "gaseste", "find")):
                op = "search"
            elif any(k in t_low for k in ("analiza", "analyze", "inform", "info")):
                op = "analyze"
            elif any(k in t_low for k in ("edit", "modifica", "inlocui", "scrie", "write")):
                op = "edit"
            args.setdefault("operation", op)
            if extracted_path:
                args.setdefault("path", extracted_path)
            elif op in {"read", "analyze", "info"}:
                args.setdefault("path", "ANA_MAX/main.py")
            else:
                args.setdefault("path", "ANA_MAX/core")
            if op in {"search", "find", "grep"}:
                pattern = self._extract_pattern_from_task(task_desc)
                if pattern:
                    args.setdefault("pattern", pattern)
        elif tname in {"code_search", "smart_search", "smart_search_tool"}:
            args.setdefault("operation", "search_codebase" if tname == "code_search" else "search")
            args.setdefault("query", task_desc or "")
            if extracted_path:
                args.setdefault("path", extracted_path)
            args.setdefault("pattern", self._extract_pattern_from_task(task_desc) or "class ")
        elif tname in {"code", "code_tool"}:
            args.setdefault("operation", "analyze")
            args.setdefault("target", task_desc or "")
        elif tname in {"tool_router", "tool_router_tool"}:
            args.setdefault("mode", "compact")
        elif tname in {"agent_coach"}:
            args.setdefault("action", "recommend")
            args.setdefault("task", task_desc or "")
        elif tname in {"ana_memory", "memory_tool"}:
            args.setdefault("action", "search_knowledge")
            args.setdefault("query", task_desc or "")
        elif tname in {"vector_memory"}:
            args.setdefault("action", "search")
            args.setdefault("query", task_desc or "")
        elif tname in {"desktop_capture"}:
            args.setdefault("operation", "capture")
        elif tname in {"system", "system_tool"}:
            args.setdefault("operation", "system_snapshot")
        elif tname in {"windows_insight"}:
            args.setdefault("operation", "system_snapshot")
        elif tname in {"workspace_situational_awareness"}:
            args.setdefault("include_uia", True)
            args.setdefault("include_errors", True)
        elif tname in {"code_context_pack"}:
            args.setdefault("task", task_desc or "")
            args.setdefault("limit", 8)
        elif tname in {"graph_context_pack"}:
            args.setdefault("action", "query")
            args.setdefault("query", task_desc or "")
            args.setdefault("limit", 6)
        elif tname in {"event_stream"}:
            args.setdefault("action", "timeline")
            args.setdefault("limit", 20)
        return args

    def _extract_path_from_task(self, task_desc: str) -> str:
        import re
        t = task_desc or ""
        # Cauta path-uri comune (Ana/care, workspace, project dirs mentionate explicit)
        m = re.search(r"((?:ANA_MAX|docs|tests|tools|core|bridge|config|scripts|memory|logs|react-demo)[\\/][A-Za-z0-9_\-\/\.\\]*)", t)
        if m:
            return m.group(1).replace("\\", "/").rstrip(".,;:!?")
        # Daca e mentionat doar un folder de nivel 1
        m2 = re.search(r"(ANA_MAX|docs|tests|tools|core|bridge|config|scripts|memory|logs|react-demo)\b", t)
        if m2:
            return m2.group(1)
        return ""

    def _extract_pattern_from_task(self, task_desc: str) -> str:
        import re
        t = task_desc or ""
        # Extrage string-uri intre ghilimele sau elemente dupa 'cauta ' / 'gaseste '
        m = re.search(r"['\"]([^'\"]{1,80})['\"]", t)
        if m:
            return m.group(1)
        m2 = re.search(r"(?:cauta|search|grep|gaseste|find)\s+(?:in|in interiorul|in folderul)?\s*([A-Za-z_][A-Za-z0-9_\.]{2,60})", t, re.IGNORECASE)
        if m2:
            return m2.group(1)
        return ""

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------
    def _make_step(
        self,
        description: str,
        tool_name: Optional[str],
        arguments: Dict[str, Any],
        checks: Optional[List[str]],
    ) -> Step:
        return Step(
            step_id=f"stp_{uuid.uuid4().hex[:8]}",
            description=description,
            tool_name=tool_name,
            arguments=dict(arguments or {}),
            checks=list(checks or []),
            status="pending",
            result=None,
            error=None,
            duration_ms=0.0,
        )

    def _execute_step(
        self,
        step: Step,
        task_id: str,
        context_snapshot: Optional[Dict[str, Any]],
        memory_state: Optional[Dict[str, Any]],
    ) -> None:
        step["status"] = "running"
        t0 = time.perf_counter()
        logger.info("PLANNER STEP START task=%s step=%s tool=%s", task_id, step["step_id"], step.get("tool_name"))
        self._publish_bus(
            "planner",
            "step_start",
            {"task_id": task_id, "step_id": step["step_id"], "tool": step.get("tool_name")},
        )

        last_error: Optional[str] = None
        for attempt in range(1, self.MAX_RETRY_PER_STEP + 2):
            try:
                if not step.get("tool_name"):
                    step["result"] = {"mode": "conversational", "task": step["arguments"].get("task")}
                    step["status"] = "success"
                    break

                tool_name = step["tool_name"]
                args = dict(step["arguments"] or {})

                if self._registry and self._registry.get(tool_name):
                    raw = self._registry.execute(tool_name, **args)
                    step["result"] = _tool_safe_result(raw)
                else:
                    step["result"] = {"success": False, "error": f"tool_not_found:{tool_name}", "message": "", "data": None}

                ok = bool((step["result"] or {}).get("success"))
                if not ok and self._healer:
                    try:
                        healed = _tool_safe_result(self._healer.safe_execute(
                            action="heal",
                            tool_name=tool_name,
                            last_error=str((step["result"] or {}).get("error") or ""),
                        ))
                        if healed.get("success") and healed.get("data"):
                            logger.info("PLANNER HEALER task=%s step=%s applied", task_id, step["step_id"])
                            raw2 = self._registry.execute(tool_name, **args) if self._registry else None
                            if raw2 is not None:
                                step["result"] = _tool_safe_result(raw2)
                    except Exception as exc:
                        logger.warning("Planner: healer failed - %s", exc)

                step["status"] = "success" if (step["result"] or {}).get("success") else "failed"
                if step["status"] == "failed":
                    last_error = str((step["result"] or {}).get("error") or "tool_failed")
                    if attempt <= self.MAX_RETRY_PER_STEP:
                        continue
                break

            except Exception as exc:
                last_error = f"exception:{exc}"
                logger.exception("PLANNER STEP EXCEPTION task=%s step=%s", task_id, step["step_id"])
                if attempt <= self.MAX_RETRY_PER_STEP:
                    time.sleep(0.2)
                    continue
                step["status"] = "failed"
                step["result"] = {"success": False, "error": last_error, "message": str(exc), "data": None}
                break

        if step["status"] == "failed":
            step["error"] = last_error or "unknown_failure"

        if self._memory and step["status"] == "failed":
            try:
                self._memory.record_event(
                    "tool_error",
                    {"task_id": task_id, "step_id": step["step_id"], "tool": step.get("tool_name"), "error": step.get("error")},
                )
            except Exception:
                pass

        step["duration_ms"] = round(1000.0 * (time.perf_counter() - t0), 2)
        logger.info(
            "PLANNER STEP END task=%s step=%s status=%s tool=%s duration_ms=%.2f",
            task_id, step["step_id"], step["status"], step.get("tool_name"), step["duration_ms"],
        )
        self._publish_bus(
            "planner",
            "step_end",
            {
                "task_id": task_id,
                "step_id": step["step_id"],
                "status": step["status"],
                "duration_ms": step["duration_ms"],
                "error": step.get("error"),
            },
        )

    def _is_step_recoverable(self, step: Step) -> bool:
        err = (step.get("error") or "").lower()
        unrecoverable = {"permission", "access denied", "not found", "tool_not_found", "auth", "invalid"}
        return not any(k in err for k in unrecoverable)

    def _should_continue_after_failure(self, step: Step, result: PlannerResult) -> bool:
        return len(result["errors"]) < 3 and len(result["steps"]) <= self.MAX_STEPS // 2

    def _synthesize_output(self, task_desc: str, steps: List[Step]) -> str:
        if not steps:
            return "Niciun pas executat."

        success_steps = [s for s in steps if s.get("status") == "success"]
        failed_steps = [s for s in steps if s.get("status") == "failed"]

        last_success = success_steps[-1] if success_steps else None
        if last_success:
            res = last_success.get("result")
            if isinstance(res, dict):
                msg = res.get("message") or ""
                data = res.get("data")
                if data is not None:
                    try:
                        s = json.dumps(data, ensure_ascii=False, default=str)
                        if len(s) < 2000:
                            return (msg + "\n" + s).strip()
                        return (msg + "\n" + s[:1800] + "\n...(truncated)").strip()
                    except Exception:
                        pass
                if msg:
                    return msg

        parts = [f"Planificator ANA: {len(success_steps)}/{len(steps)} pasi reusiti."]
        if failed_steps:
            parts.append("Erori:")
            for s in failed_steps:
                parts.append(f"- [{s.get('step_id')}] {s.get('tool_name')}: {s.get('error')}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _publish_bus(self, source: str, event_type: str, data: Dict[str, Any]) -> None:
        if self._bus is None:
            return
        try:
            self._bus.publish(source=source, event_type=event_type, data=data)
        except Exception:
            pass


_planner_singleton: Optional[ANAPlanner] = None


def get_planner(config: Optional[Dict[str, Any]] = None) -> ANAPlanner:
    global _planner_singleton
    if _planner_singleton is None:
        _planner_singleton = ANAPlanner(config=config)
    return _planner_singleton
