"""Recovery manager for ANA MAX OS dev mode."""

from __future__ import annotations

from typing import Any


class RecoveryManager:
    """Restore memory, FS, services, and locks from snapshots."""

    def __init__(self, memory: Any = None, fs_sync: Any = None, service_manager: Any = None, lock_manager: Any = None) -> None:
        """Initialize recovery targets."""
        self.memory = memory
        self.fs_sync = fs_sync
        self.service_manager = service_manager
        self.lock_manager = lock_manager

    def restore(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Restore available targets from a snapshot."""
        restored = []
        if self.memory is not None and "memory" in snapshot:
            self.memory.store.update(snapshot["memory"].get("store", {}))
            restored.append("memory")
        if self.service_manager is not None and "services" in snapshot:
            for name, data in snapshot["services"].items():
                self.service_manager.start_service(name, node_id=data.get("node_id"))
            restored.append("services")
        if self.lock_manager is not None and "locks" in snapshot:
            for key, data in snapshot["locks"].items():
                self.lock_manager.acquire(key, data.get("owner", "unknown"), ttl=30)
            restored.append("locks")
        return {"success": True, "restored": restored}


__all__ = ["RecoveryManager"]

