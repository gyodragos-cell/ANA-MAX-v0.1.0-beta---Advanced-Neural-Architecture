"""Developer tools protocols for ANA MAX AI Kernel v1."""

from __future__ import annotations

from typing import Any


class DevToolsManager:
    """Simulate logs, FS, and memory viewer protocols."""

    def __init__(self, event_bus: Any = None, fs_sync: Any = None, distributed_memory: Any = None) -> None:
        """Initialize devtools providers."""
        self.event_bus = event_bus
        self.fs_sync = fs_sync
        self.distributed_memory = distributed_memory
        self.log_subscriptions: list[dict[str, Any]] = []

    def subscribe_logs(self, topic_filter: str = "*") -> dict[str, Any]:
        """Register a log subscription."""
        subscription = {"type": "ui.logs.subscribe", "filter": topic_filter}
        self.log_subscriptions.append(subscription)
        return subscription

    def emit_log(self, message: str, topic: str = "log.entry") -> None:
        """Emit a UI log event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish("ui.logs.event", {"topic": topic, "message": message})

    def fs_list(self) -> list[str]:
        """List files through fs_sync."""
        return self.fs_sync._list_all_paths() if self.fs_sync else []

    def fs_read(self, path: str) -> str | None:
        """Read a file through fs_sync."""
        if not self.fs_sync:
            return None
        entry = self.fs_sync._get_file_entry(path)
        return entry.get("content") if entry else None

    def fs_write(self, path: str, content: str) -> None:
        """Write a file through fs_sync."""
        if self.fs_sync:
            self.fs_sync.write_file(path, content)

    def memory_list(self) -> list[str]:
        """List memory keys."""
        return list(self.distributed_memory.store.keys()) if self.distributed_memory else []

    def memory_get(self, key: str) -> Any:
        """Get a memory value."""
        return self.distributed_memory.read(key).get("value") if self.distributed_memory else None

    def memory_set(self, key: str, value: Any) -> None:
        """Set a memory value."""
        if self.distributed_memory:
            self.distributed_memory.write(key, value)


__all__ = ["DevToolsManager"]

