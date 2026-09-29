"""
ANA MAX - Session Log Miner Tool (OS27 Hyper++)
================================================
Extrage lectii utile din fisiere de sesiune, rapoarte, markdown, json sau jsonl si le poate salva in memoria conversationala.

OS27 Hyper++ Features:
- Telemetry tracking for session log mining operations (analyze, import_lessons)
- Health monitoring for session log mining operations reliability
- MemoryCortex integration for session log mining errors and state learning
- ContextEngine integration for session log mining state awareness
- SelfEvolvingTool integration for anomaly detection on session log mining failures
- Structured logging with error detection
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.conversation_learning_tool import ConversationLearningTool

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_session_log_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_session_log_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for session log mining operations."""
    if operation not in _session_log_telemetry:
        _session_log_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _session_log_telemetry[operation]["operation_count"] += 1
    _session_log_telemetry[operation]["total_time"] += execution_time
    _session_log_telemetry[operation]["last_execution_time"] = execution_time
    _session_log_telemetry[operation]["last_success"] = success
    
    if success:
        _session_log_telemetry[operation]["success_count"] += 1
    else:
        _session_log_telemetry[operation]["failure_count"] += 1


def get_session_log_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for session log mining operations."""
    if operation:
        return _session_log_telemetry.get(operation, {})
    return _session_log_telemetry.copy()


def get_session_log_health() -> str:
    """Get health status for session log mining tool based on telemetry."""
    if not _session_log_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _session_log_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _session_log_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class SessionLogMinerTool(Tool):
    def __init__(self) -> None:
        self.learning_tool = ConversationLearningTool()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="session_log_miner",
            description="Extrage lectii utile din fisiere de sesiune, rapoarte, markdown, json sau jsonl si le poate salva in memoria conversationala.",
            parameters=[
                ToolParameter(name="path", description="Calea catre fisierul sursa", type="string", required=True),
                ToolParameter(
                    name="action",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=["analyze", "import_lessons"],
                ),
                ToolParameter(
                    name="category",
                    description="Categoria implicita pentru lectiile extrase",
                    type="string",
                    required=False,
                    default="session_learning",
                ),
                ToolParameter(
                    name="source",
                    description="Eticheta sursei in jurnal",
                    type="string",
                    required=False,
                    default="session_log_miner",
                ),
                ToolParameter(
                    name="limit",
                    description="Numarul maxim de lectii extrase",
                    type="integer",
                    required=False,
                    default=10,
                ),
            ],
            category="memory",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        action = kwargs.get("action")
        path = kwargs.get("path")
        category = kwargs.get("category", "session_learning")
        source = kwargs.get("source", "session_log_miner")
        limit = int(kwargs.get("limit", 10))

        if action not in {"analyze", "import_lessons"}:
            execution_time = time.time() - start_time
            _record_session_log_telemetry("unknown", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

        try:
            file_path = Path(path)
            if not file_path.exists() or not file_path.is_file():
                execution_time = time.time() - start_time
                _record_session_log_telemetry(action, False, execution_time)
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisier inexistent: {path}")

            content = self._read_file(file_path)
            lessons = self._extract_lessons(content, file_path.name, category=category, limit=limit)

            if action == "analyze":
                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "path": str(file_path),
                        "lessons_found": len(lessons),
                        "lessons": lessons,
                    },
                    message=f"Extrase {len(lessons)} lectii candidate.",
                )
                execution_time = time.time() - start_time
                _record_session_log_telemetry(action, result.is_success, execution_time)
                
                # ContextEngine integration for session log mining state
                if context_engine and result.is_success:
                    try:
                        context_engine.update_context(
                            key="session_log_mining_state",
                            value={
                                "action": action,
                                "path": str(file_path),
                                "lessons_found": len(lessons),
                                "success": result.is_success,
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                return result

            imported = []
            for lesson in lessons:
                result = self.learning_tool.execute(
                    action="add",
                    title=lesson["title"],
                    category=lesson["category"],
                    problem=lesson["problem"],
                    lesson=lesson["lesson"],
                    fix=lesson["fix"],
                    validation=lesson["validation"],
                    source=source,
                    confidence=lesson["confidence"],
                    tags=",".join(lesson["tags"]),
                )
                if result.is_success:
                    imported.append(lesson)

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(file_path),
                    "lessons_found": len(lessons),
                    "lessons_imported": len(imported),
                    "lessons": imported,
                },
                message=f"Importate {len(imported)} lectii in conversation_learning.",
            )
            execution_time = time.time() - start_time
            _record_session_log_telemetry(action, result.is_success, execution_time)
            
            # ContextEngine integration for session log mining state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="session_log_mining_state",
                        value={
                            "action": action,
                            "path": str(file_path),
                            "lessons_found": len(lessons),
                            "lessons_imported": len(imported),
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_session_log_telemetry(action, False, execution_time)
            logger.error("Session log miner failed: %s", exc)
            
            # MemoryCortex integration for session log mining errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"session_log.{action}",
                        f"Session log mining failed for {path}: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()

        if suffix in {".md", ".txt", ".log"}:
            return path.read_text(encoding="utf-8", errors="replace")

        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            return json.dumps(data, ensure_ascii=False, indent=2)

        if suffix == ".jsonl":
            lines = []
            for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    lines.append(json.dumps(json.loads(raw), ensure_ascii=False))
                except json.JSONDecodeError:
                    lines.append(raw)
            return "\n".join(lines)

        return path.read_text(encoding="utf-8", errors="replace")

    def _extract_lessons(self, content: str, file_name: str, category: str, limit: int) -> List[Dict[str, Any]]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        candidates: List[Dict[str, Any]] = []

        trigger_words = [
            "error", "eroare", "fix", "fixed", "solutie", "solution",
            "problem", "problema", "warning", "rollback", "backup",
            "test", "pytest", "repair", "healing", "lesson", "pattern",
        ]

        for block in paragraphs:
            lowered = block.lower()
            if not any(word in lowered for word in trigger_words):
                continue

            lines = [line.strip("-* ").strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue

            title = lines[0][:90]
            problem = self._find_first_sentence(block, ["problem", "problema", "error", "eroare", "warning"])
            fix = self._find_first_sentence(block, ["fix", "fixed", "solutie", "solution", "rollback", "backup"])
            validation = self._find_first_sentence(block, ["test", "verified", "validat", "passed", "import ok"])
            lesson = self._build_lesson(problem, fix, validation, block)

            if not lesson:
                continue

            tags = [word for word in trigger_words if word in lowered][:6]
            candidates.append(
                {
                    "title": title,
                    "category": category,
                    "problem": problem,
                    "lesson": lesson,
                    "fix": fix,
                    "validation": validation,
                    "confidence": "medium",
                    "tags": list(dict.fromkeys(tags + ["mined", "session"])),
                }
            )

            if len(candidates) >= limit:
                break

        if not candidates and content.strip():
            preview = content.strip().splitlines()[0][:90]
            candidates.append(
                {
                    "title": f"Lesson from {file_name}: {preview}",
                    "category": category,
                    "problem": "",
                    "lesson": "Fisierul contine context util, dar necesita analiza manuala mai profunda.",
                    "fix": "",
                    "validation": "",
                    "confidence": "low",
                    "tags": ["mined", "review_needed"],
                }
            )

        return candidates[:limit]

    def _find_first_sentence(self, text: str, keywords: List[str]) -> str:
        for line in text.splitlines():
            line = line.strip("-* ").strip()
            lowered = line.lower()
            if any(keyword in lowered for keyword in keywords):
                return line[:300]
        return ""

    def _build_lesson(self, problem: str, fix: str, validation: str, block: str) -> str:
        if problem and fix:
            return f"Daca apare '{problem}', merita incercat fixul: {fix}"
        if fix:
            return f"Fix reutilizabil identificat: {fix}"
        if validation:
            return f"Observatie validata in sesiune: {validation}"
        snippet = " ".join(block.split())
        return snippet[:280] if snippet else ""
