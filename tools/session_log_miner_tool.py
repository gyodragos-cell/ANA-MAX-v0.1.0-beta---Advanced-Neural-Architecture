"""
ANA MAX - Session Log Miner Tool
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.conversation_learning_tool import ConversationLearningTool

logger = logging.getLogger(__name__)


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
        action = kwargs.get("action")
        path = kwargs.get("path")
        category = kwargs.get("category", "session_learning")
        source = kwargs.get("source", "session_log_miner")
        limit = int(kwargs.get("limit", 10))

        if action not in {"analyze", "import_lessons"}:
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

        try:
            file_path = Path(path)
            if not file_path.exists() or not file_path.is_file():
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisier inexistent: {path}")

            content = self._read_file(file_path)
            lessons = self._extract_lessons(content, file_path.name, category=category, limit=limit)

            if action == "analyze":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "path": str(file_path),
                        "lessons_found": len(lessons),
                        "lessons": lessons,
                    },
                    message=f"Extrase {len(lessons)} lectii candidate.",
                )

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

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(file_path),
                    "lessons_found": len(lessons),
                    "lessons_imported": len(imported),
                    "lessons": imported,
                },
                message=f"Importate {len(imported)} lectii in conversation_learning.",
            )
        except Exception as exc:
            logger.error("Session log miner failed: %s", exc)
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
