"""Distributed task execution manager for ANA MAX OS dev mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4


@dataclass
class TaskRecord:
    """One distributed task record."""

    task_id: str
    payload: dict[str, Any]
    status: str = "submitted"
    node_id: str | None = None
    attempts: int = 0
    result: Any = None


class TaskManager:
    """Route and execute simulated distributed tasks."""

    def __init__(self, cluster_manager: Any = None, distributed_memory: Any = None, event_bus: Any = None) -> None:
        """Initialize task state."""
        self.cluster_manager = cluster_manager
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.tasks: dict[str, TaskRecord] = {}

    def submit(self, task: dict[str, Any]) -> TaskRecord:
        """Submit and route a task."""
        node_id = self.cluster_manager.get_best_node(task.get("capability")) if self.cluster_manager else None
        record = TaskRecord(str(uuid4()), dict(task), "submitted", node_id)
        self.tasks[record.task_id] = record
        self._replicate(record)
        self._publish("task.submitted", {"task_id": record.task_id, "node_id": node_id})
        return record

    def execute(self, task_id: str, handler: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        """Execute a submitted task with a fake handler."""
        record = self.tasks[task_id]
        if record.status == "cancelled":
            return {"success": False, "status": "cancelled", "task_id": task_id}
        record.status = "started"
        record.attempts += 1
        self._publish("task.started", {"task_id": task_id, "node_id": record.node_id})
        try:
            record.result = handler(record.payload) if handler else {"ok": True}
            record.status = "completed"
            self._publish("task.completed", {"task_id": task_id})
            success = True
        except Exception as error:
            record.result = str(error)
            record.status = "failed"
            self._publish("task.failed", {"task_id": task_id, "error": str(error)})
            success = False
        self._replicate(record)
        return {"success": success, "task_id": task_id, "status": record.status, "result": record.result}

    def retry(self, task_id: str, handler: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        """Retry a failed task."""
        self.tasks[task_id].status = "submitted"
        return self.execute(task_id, handler=handler)

    def cancel(self, task_id: str) -> dict[str, Any]:
        """Cancel a task."""
        record = self.tasks[task_id]
        record.status = "cancelled"
        self._replicate(record)
        return {"success": True, "task_id": task_id, "status": record.status}

    def snapshot(self) -> dict[str, Any]:
        """Return task state."""
        return {task_id: record.__dict__.copy() for task_id, record in self.tasks.items()}

    def _replicate(self, record: TaskRecord) -> None:
        """Replicate task state to distributed memory."""
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"task:{record.task_id}", record.__dict__.copy())

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a task event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)


__all__ = ["TaskManager", "TaskRecord"]

