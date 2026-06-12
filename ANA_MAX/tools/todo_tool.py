"""
ANA MAX - TodoWrite Tool
========================
Persistent task list helper inspired by OpenCode's todowrite utility.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


@dataclass
class TodoItem:
    content: str
    status: str = "pending"
    note: str = ""
    updated_at: float = 0.0


_TODO_SESSIONS: Dict[str, List[TodoItem]] = {}


class TodoWriteTool(Tool):
    """Maintain a lightweight persistent todo list per session."""

    VALID_STATUSES = {"pending", "in_progress", "completed"}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="todowrite",
            description=(
                "Gestioneaza o lista persistenta de task-uri pentru sesiunea curenta. "
                "Util pentru modele locale care trebuie sa urmareasca progresul pas cu pas."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia dorita",
                    type="string",
                    required=True,
                    choices=["replace", "append", "update", "list", "clear"],
                ),
                ToolParameter(
                    name="session_id",
                    description="ID sesiune pentru lista de task-uri",
                    type="string",
                    required=False,
                    default="default",
                ),
                ToolParameter(
                    name="items_json",
                    description="JSON array pentru replace, ex: ['pas 1', {'content':'pas 2','status':'pending'}]",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="content",
                    description="Continut pentru append sau update",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="index",
                    description="Index item pentru update",
                    type="integer",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="status",
                    description="Status item: pending | in_progress | completed",
                    type="string",
                    required=False,
                    default="pending",
                    choices=["pending", "in_progress", "completed"],
                ),
                ToolParameter(
                    name="note",
                    description="Nota optionala pentru item",
                    type="string",
                    required=False,
                    default="",
                ),
            ],
            category="productivity",
            requires_confirmation=False,
        )

    def execute(self, operation: str, session_id: str = "default", **kwargs) -> ToolResult:
        session_id = session_id or "default"
        items = _TODO_SESSIONS.setdefault(session_id, [])

        if operation == "replace":
            items_json = kwargs.get("items_json", "") or ""
            if not items_json:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'items_json' este necesar")
            try:
                payload = json.loads(items_json)
                if not isinstance(payload, list):
                    raise ValueError("items_json trebuie sa fie lista JSON")
                _TODO_SESSIONS[session_id] = [self._normalize_item(item) for item in payload]
                return self._success(session_id, "Lista todo a fost inlocuita")
            except Exception as exc:
                return ToolResult(status=ToolStatus.ERROR, error=f"items_json invalid: {exc}")

        if operation == "append":
            content = (kwargs.get("content", "") or "").strip()
            if not content:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'content' este necesar")
            status = kwargs.get("status", "pending") or "pending"
            note = kwargs.get("note", "") or ""
            items.append(self._build_item(content=content, status=status, note=note))
            return self._success(session_id, "Item adaugat in todo list")

        if operation == "update":
            index = int(kwargs.get("index", 0) or 0)
            if index < 0 or index >= len(items):
                return ToolResult(status=ToolStatus.ERROR, error=f"Index invalid: {index}")
            item = items[index]
            content = kwargs.get("content")
            status = kwargs.get("status")
            note = kwargs.get("note")
            if content:
                item.content = content.strip()
            if status:
                normalized_status = self._normalize_status(status)
                if not normalized_status:
                    return ToolResult(status=ToolStatus.ERROR, error=f"Status invalid: {status}")
                item.status = normalized_status
            if note is not None:
                item.note = note
            item.updated_at = time.time()
            return self._success(session_id, f"Item {index} actualizat")

        if operation == "list":
            return self._success(session_id, f"{len(items)} item-uri in todo list")

        if operation == "clear":
            _TODO_SESSIONS[session_id] = []
            return self._success(session_id, "Todo list golita")

        return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

    def _success(self, session_id: str, message: str) -> ToolResult:
        items = _TODO_SESSIONS.get(session_id, [])
        data = {
            "session_id": session_id,
            "count": len(items),
            "items": [asdict(item) for item in items],
        }
        return ToolResult(status=ToolStatus.SUCCESS, data=data, message=message)

    def _normalize_item(self, item) -> TodoItem:
        if isinstance(item, str):
            return self._build_item(content=item, status="pending", note="")
        if isinstance(item, dict):
            return self._build_item(
                content=str(item.get("content", "")).strip(),
                status=str(item.get("status", "pending")),
                note=str(item.get("note", "")),
            )
        raise ValueError(f"Item todo invalid: {item!r}")

    def _build_item(self, content: str, status: str, note: str) -> TodoItem:
        normalized_status = self._normalize_status(status)
        if not content:
            raise ValueError("Item todo fara continut")
        if not normalized_status:
            raise ValueError(f"Status invalid: {status}")
        return TodoItem(content=content, status=normalized_status, note=note, updated_at=time.time())

    def _normalize_status(self, status: str) -> str:
        normalized = (status or "").strip().lower()
        return normalized if normalized in self.VALID_STATUSES else ""
