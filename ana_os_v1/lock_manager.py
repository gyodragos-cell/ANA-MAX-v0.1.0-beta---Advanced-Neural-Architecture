"""Ephemeral distributed lock manager for ANA MAX OS dev mode."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class LockRecord:
    """One ephemeral lock."""

    key: str
    owner: str
    expires_at: str


class LockManager:
    """Simple LWW lock table backed by optional distributed memory."""

    def __init__(self, distributed_memory: Any = None, event_bus: Any = None, node_id: str = "local") -> None:
        """Initialize lock table."""
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.node_id = node_id
        self.locks: dict[str, LockRecord] = {}

    def acquire(self, key: str, owner: str, ttl: float = 30.0) -> bool:
        """Acquire a lock if missing or expired."""
        self.check_expired()
        existing = self.locks.get(key)
        if existing and existing.owner != owner:
            return False
        record = LockRecord(key, owner, self._future(ttl))
        self.locks[key] = record
        self._replicate(key)
        self._publish("lock.acquired", {"key": key, "owner": owner})
        return True

    def release(self, key: str, owner: str) -> bool:
        """Release a lock owned by owner."""
        existing = self.locks.get(key)
        if not existing or existing.owner != owner:
            return False
        self.locks.pop(key, None)
        self._replicate(key)
        self._publish("lock.released", {"key": key, "owner": owner})
        return True

    def is_locked(self, key: str) -> bool:
        """Return whether a lock is currently active."""
        self.check_expired()
        return key in self.locks

    def check_expired(self) -> None:
        """Release expired locks."""
        now = self._now()
        for key, record in list(self.locks.items()):
            if record.expires_at <= now:
                self.locks.pop(key, None)
                self._replicate(key)
                self._publish("lock.released", {"key": key, "owner": record.owner, "reason": "ttl_expired"})

    def release_by_owner(self, owner: str) -> list[str]:
        """Release all locks held by owner."""
        released = []
        for key, record in list(self.locks.items()):
            if record.owner == owner and self.release(key, owner):
                released.append(key)
        return released

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe lock snapshot."""
        return {key: record.__dict__.copy() for key, record in self.locks.items()}

    def _replicate(self, key: str) -> None:
        """Replicate lock state to distributed memory."""
        if not self.distributed_memory or not hasattr(self.distributed_memory, "write"):
            return
        value = self.locks[key].__dict__.copy() if key in self.locks else None
        self.distributed_memory.write(f"lock:{key}", value, node_id=self.node_id)

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a lock event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)

    @staticmethod
    def _now() -> str:
        """Return an ISO timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @classmethod
    def _future(cls, seconds: float) -> str:
        """Return an ISO timestamp in the future."""
        return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="microseconds")


__all__ = ["LockManager", "LockRecord"]

