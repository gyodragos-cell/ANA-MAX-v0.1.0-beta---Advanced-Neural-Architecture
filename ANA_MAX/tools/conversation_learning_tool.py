"""
ANA MAX - Conversation Learning Tool
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ConversationLearningTool(Tool):
    def __init__(self) -> None:
        self.memory_file = Path("memory/conversation_learning.jsonl")
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="conversation_learning",
            description="Salveaza si cauta lectii invatate de ANA din conversatii, teste si self-healing.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=["add", "recent", "search"],
                ),
                ToolParameter(name="title", description="Titlul lectiei", type="string", required=False),
                ToolParameter(name="category", description="Categoria lectiei", type="string", required=False),
                ToolParameter(name="problem", description="Problema observata", type="string", required=False),
                ToolParameter(name="lesson", description="Lectia invatata", type="string", required=False),
                ToolParameter(name="fix", description="Fix-ul sau regula aplicata", type="string", required=False),
                ToolParameter(name="validation", description="Cum a fost validata lectia", type="string", required=False),
                ToolParameter(name="source", description="Sursa lectiei", type="string", required=False, default="manual"),
                ToolParameter(name="confidence", description="Nivel de incredere", type="string", required=False, default="medium"),
                ToolParameter(name="tags", description="Tag-uri separate prin virgula", type="string", required=False),
                ToolParameter(name="query", description="Text de cautare pentru search", type="string", required=False),
                ToolParameter(name="limit", description="Numarul maxim de rezultate", type="integer", required=False, default=10),
            ],
            category="memory",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")

        if action == "add":
            result = self._add_lesson(**kwargs)
        elif action == "recent":
            result = self._recent(**kwargs)
        elif action == "search":
            result = self._search(**kwargs)
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

        if result.get("success"):
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result.get("message", ""))
        return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Unknown error"))

    def _read_entries(self) -> List[Dict[str, Any]]:
        if not self.memory_file.exists():
            return []

        entries: List[Dict[str, Any]] = []
        for line in self.memory_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Invalid JSONL entry skipped in %s", self.memory_file)
        return entries

    def _add_lesson(self, **kwargs: Any) -> Dict[str, Any]:
        title = (kwargs.get("title") or "").strip()
        category = (kwargs.get("category") or "").strip()
        lesson = (kwargs.get("lesson") or "").strip()

        if not title or not category or not lesson:
            return {
                "success": False,
                "error": "Parametrii 'title', 'category' si 'lesson' sunt obligatorii pentru action='add'.",
            }

        tags_raw = kwargs.get("tags", "")
        tags = [tag.strip() for tag in str(tags_raw).split(",") if tag.strip()]

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": kwargs.get("source", "manual"),
            "category": category,
            "title": title,
            "problem": kwargs.get("problem", ""),
            "lesson": lesson,
            "fix": kwargs.get("fix", ""),
            "validation": kwargs.get("validation", ""),
            "confidence": kwargs.get("confidence", "medium"),
            "tags": tags,
        }

        with self.memory_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return {
            "success": True,
            "message": "Lectie salvata cu succes.",
            "entry": entry,
        }

    def _recent(self, **kwargs: Any) -> Dict[str, Any]:
        limit = int(kwargs.get("limit", 10))
        entries = self._read_entries()
        results = entries[-limit:] if limit > 0 else entries
        return {
            "success": True,
            "count": len(results),
            "results": results,
            "message": f"Gasite {len(results)} lectii recente.",
        }

    def _search(self, **kwargs: Any) -> Dict[str, Any]:
        query = (kwargs.get("query") or "").strip().lower()
        if not query:
            return {"success": False, "error": "Parametrul 'query' este obligatoriu pentru action='search'."}

        limit = int(kwargs.get("limit", 10))
        entries = self._read_entries()
        matches: List[Dict[str, Any]] = []

        for entry in reversed(entries):
            haystack = " ".join(
                [
                    str(entry.get("title", "")),
                    str(entry.get("category", "")),
                    str(entry.get("problem", "")),
                    str(entry.get("lesson", "")),
                    str(entry.get("fix", "")),
                    " ".join(entry.get("tags", [])),
                ]
            ).lower()
            if query in haystack:
                matches.append(entry)
            if len(matches) >= limit:
                break

        return {
            "success": True,
            "query": query,
            "count": len(matches),
            "results": matches,
            "message": f"Gasite {len(matches)} lectii pentru query-ul dat.",
        }
