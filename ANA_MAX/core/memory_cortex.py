"""
ANA MAX - Memory Cortex avansat (ANAMemoryCortex)
===================================================
Cortex de memorie cu trei tipuri: episodic, semantic, task-based.

Foloseste: VectorMemoryTool, MemoryTool
Salveaza in: memory/episodic/, memory/semantic/, memory/tasks/
Expune: record_event, query_memory, get_state_for_task
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger("memory_cortex")

ANA_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ANA_ROOT / "memory"
EPISODIC_DIR = MEMORY_DIR / "episodic"
SEMANTIC_DIR = MEMORY_DIR / "semantic"
TASKS_DIR = MEMORY_DIR / "tasks"

for _d in (EPISODIC_DIR, SEMANTIC_DIR, TASKS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class ANAMemoryCortex:
    """Cortex de memorie cu 3 straturi: episodic, semantic, task-based."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        self._vector_tool = None
        self._memory_tool = None
        self._bus = None
        self._episodic_db = EPISODIC_DIR / "events.jsonl"
        self._task_db = TASKS_DIR / "task_states.json"
        self._semantic_db = SEMANTIC_DIR / "concepts.jsonl"
        self._init_components()

    def _init_components(self) -> None:
        try:
            from tools.vector_memory_tool import VectorMemoryTool
            self._vector_tool = VectorMemoryTool()
        except Exception as exc:
            logger.warning("MemoryCortex: VectorMemoryTool unavailable - %s", exc)

        try:
            from tools.memory_tool import MemoryTool
            self._memory_tool = MemoryTool()
        except Exception as exc:
            logger.warning("MemoryCortex: MemoryTool unavailable - %s", exc)

        try:
            from tools.watchdog_bus import bus as watchdog_bus
            self._bus = watchdog_bus
            try:
                self._bus.start()
            except Exception:
                pass
        except Exception as exc:
            logger.warning("MemoryCortex: watchdog_bus unavailable - %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def record_event(self, type: str, data: Dict[str, Any]) -> bool:
        """Inregistreaza un eveniment episodic (task, tool, eroare, etc)."""
        if not self.enabled:
            return False
        event = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": type or "generic",
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "epoch_ms": int(time.time() * 1000),
        }
        try:
            with self._episodic_db.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logger.warning("MemoryCortex: episodic write failed - %s", exc)
            return False

        try:
            if self._vector_tool:
                text = f"[{event['type']}] {json.dumps(event['data'], ensure_ascii=False, default=str)}"
                self._vector_tool.safe_execute(
                    action="store",
                    content=text,
                    memory_type="episodic",
                    tags=json.dumps([event["type"]]),
                )
        except Exception as exc:
            logger.debug("MemoryCortex: vector store skipped - %s", exc)

        try:
            if self._memory_tool and event["type"] == "tool_error":
                err = str((data or {}).get("error") or "")
                self._memory_tool.safe_execute(
                    action="save_error_solution",
                    error_pattern=err[:400],
                    solution=f"Eroare inregistrata la {event['timestamp']}. Context: {json.dumps(data, ensure_ascii=False, default=str)[:1200]}",
                )
        except Exception as exc:
            logger.debug("MemoryCortex: memory tool save skipped - %s", exc)

        self._publish_bus("memory_cortex", "event_recorded", {"type": event["type"], "id": event["id"]})
        logger.info("MEMORY_CORTEX record type=%s id=%s", event["type"], event["id"])
        return True

    def query_memory(
        self,
        query: str,
        type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Cauta in memorie: vector + episodic + semantic + knowledge."""
        if not self.enabled or not query:
            return []

        results: List[Dict[str, Any]] = []

        try:
            if self._vector_tool:
                kwargs = {"action": "search", "query": query, "top_k": top_k}
                if type:
                    kwargs["memory_type"] = type
                res = self._safe_result(self._vector_tool.safe_execute(**kwargs))
                if res.get("success") and isinstance(res.get("data"), dict):
                    hits = (res["data"].get("results") or res["data"].get("items") or [])
                    for h in hits[:top_k]:
                        results.append({"source": "vector", "data": h})
        except Exception as exc:
            logger.debug("MemoryCortex: vector query skipped - %s", exc)

        try:
            if self._memory_tool:
                res = self._safe_result(
                    self._memory_tool.safe_execute(action="search_knowledge", query=query, limit=top_k)
                )
                if res.get("success") and isinstance(res.get("data"), dict):
                    hits = res["data"].get("results") or []
                    for h in hits[:top_k]:
                        results.append({"source": "knowledge", "data": h})
        except Exception as exc:
            logger.debug("MemoryCortex: knowledge query skipped - %s", exc)

        try:
            epi_results = self._query_episodic_local(query, type=type, limit=top_k)
            for r in epi_results:
                results.append({"source": "episodic_local", "data": r})
        except Exception as exc:
            logger.debug("MemoryCortex: local episodic query skipped - %s", exc)

        return results[:top_k]

    def get_state_for_task(self, task_id: str) -> Dict[str, Any]:
        """Returneaza starea unui task (istoric de pasi, erori, status)."""
        if not self.enabled:
            return {"task_id": task_id, "state": "cortex_disabled"}
        try:
            if self._task_db.exists():
                raw = json.loads(self._task_db.read_text(encoding="utf-8") or "{}")
            else:
                raw = {}
            if not isinstance(raw, dict):
                raw = {}
            state = raw.get(task_id) or {
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "history": [],
                "errors": [],
            }
            return state
        except Exception as exc:
            logger.warning("MemoryCortex: get_state failed - %s", exc)
            return {"task_id": task_id, "state": "load_failed", "error": str(exc)}

    def set_task_state(self, task_id: str, state_update: Dict[str, Any]) -> bool:
        """Actualizeaza starea unui task."""
        if not self.enabled or not task_id:
            return False
        try:
            if self._task_db.exists():
                raw = json.loads(self._task_db.read_text(encoding="utf-8") or "{}")
            else:
                raw = {}
            if not isinstance(raw, dict):
                raw = {}
            current = raw.get(task_id) or {
                "task_id": task_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            current.update(state_update or {})
            current["updated_at"] = datetime.utcnow().isoformat() + "Z"
            raw[task_id] = current
            self._task_db.write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            self._publish_bus("memory_cortex", "task_state_updated", {"task_id": task_id})
            return True
        except Exception as exc:
            logger.warning("MemoryCortex: set_task_state failed - %s", exc)
            return False

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returneaza erorile recente din memorie (pentru planner: evita repetarea)."""
        return self._query_episodic_local("error", type="tool_error", limit=limit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _safe_result(self, result: Any) -> Dict[str, Any]:
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

    def _query_episodic_local(
        self, query: str, type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self._episodic_db.exists():
            return []
            
        # Daca e un query valid, folosim BM25 RAG pe JSONL
        if query and query.strip():
            try:
                from core.rag_cpu_engine import get_rag_engine
                rag = get_rag_engine()
                results = rag.search_jsonl(
                    filepath=str(self._episodic_db),
                    query=query,
                    top_k=limit,
                    filter_type=type
                )
                
                if results:
                    # Returnam rezultatele RAG daca a gasit ceva
                    for r in results:
                        if "_score" in r:
                            del r["_score"]
                    return results
            except Exception as exc:
                logger.error(f"MemoryCortex: RAG search failed, fallback to linear. Error: {exc}")
                
        # Daca n-avem query sau RAG a picat/nu a gasit, folosim legacy linear search (fallback / pure filter)
        q = (query or "").lower()
        results: List[Dict[str, Any]] = []
        try:
            lines = self._episodic_db.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        for line in reversed(lines[-2000:]):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if type and obj.get("type") != type:
                continue
            if q:
                blob = json.dumps(obj, ensure_ascii=False, default=str).lower()
                if q not in blob:
                    continue
            results.append(obj)
            if len(results) >= limit:
                break
        return results

    def _publish_bus(self, source: str, event_type: str, data: Dict[str, Any]) -> None:
        if self._bus is None:
            return
        try:
            self._bus.publish(source=source, event_type=event_type, data=data)
        except Exception:
            pass


_cortex_singleton: Optional[ANAMemoryCortex] = None


def get_memory_cortex(config: Optional[Dict[str, Any]] = None) -> ANAMemoryCortex:
    global _cortex_singleton
    if _cortex_singleton is None:
        _cortex_singleton = ANAMemoryCortex(config=config)
    return _cortex_singleton
