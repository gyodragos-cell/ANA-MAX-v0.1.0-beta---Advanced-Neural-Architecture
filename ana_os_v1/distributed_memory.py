"""Distributed memory engine for ANA MAX AI OS dev mode."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ana_os_v1.transport import Transport


MEMORY_WRITE = "memory.write"
MEMORY_REPLICATE = "memory.replicate"
MEMORY_PULL_REQUEST = "memory.pull_request"
MEMORY_PULL_RESPONSE = "memory.pull_response"
MEMORY_CONFLICT = "memory.conflict"


@dataclass(frozen=True)
class MemoryValue:
    """Versioned distributed memory value."""

    value: Any
    version: int = 1


class DistributedMemory:
    """Node-aware distributed memory API with simple conflict resolution."""

    def __init__(
        self,
        strategy: str = "latest",
        transport: Transport | None = None,
        node_id: str = "local",
        mode: str = "eventual",
        global_mode: str = "eventual",
    ) -> None:
        """Initialize memory store."""
        self.strategy = strategy
        self.transport = transport
        self.node_id = node_id
        self.mode = mode
        self.global_mode = global_mode
        self.store: dict[str, MemoryValue] = {}
        self.node_store: dict[str, dict[str, MemoryValue]] = {}

    def write(self, key: str, value: Any, version: int = 1, node_id: str = "global") -> dict[str, Any]:
        """Write a value with version."""
        node_values = self.node_store.setdefault(node_id, {})
        existing = node_values.get(key) or self.store.get(key)
        existing_version = existing.version if isinstance(existing, MemoryValue) else 0
        if existing and existing_version > version and self.strategy == "latest":
            return {"success": False, "error": "older version rejected", "current_version": existing_version}
        item = MemoryValue(value, version)
        node_values[key] = item
        self.store[key] = item
        self._send_memory_message(
            MEMORY_WRITE,
            {
                "key": key,
                "value": value,
                "version": item.version,
                "node_id": self.node_id,
                "timestamp": self._now(),
            },
        )
        return {"success": True, "key": key, "version": version, "node_id": node_id}

    def read(self, key: str, node_id: str | None = None) -> dict[str, Any]:
        """Read a distributed value."""
        item = self.node_store.get(node_id or "", {}).get(key) if node_id else None
        item = item or self.store.get(key)
        value = item.value if isinstance(item, MemoryValue) else item
        version = item.version if isinstance(item, MemoryValue) else None
        return {
            "success": item is not None,
            "key": key,
            "value": value,
            "version": version,
            "node_id": node_id or "global",
        }

    def replicate(self, source_node: str, target_node: str, key: str) -> dict[str, Any]:
        """Replicate one key between simulated nodes."""
        source = self.node_store.get(source_node, {}).get(key)
        if source is None:
            return {"success": False, "error": "source key missing", "key": key}
        self.node_store.setdefault(target_node, {})[key] = source
        self._send_memory_message(
            MEMORY_REPLICATE,
            {
                "key": key,
                "value": source.value if isinstance(source, MemoryValue) else source,
                "version": source.version if isinstance(source, MemoryValue) else None,
                "source_node": source_node,
            },
            target_node=target_node,
        )
        return {
            "success": True,
            "key": key,
            "source_node": source_node,
            "target_node": target_node,
            "version": source.version if isinstance(source, MemoryValue) else None,
        }

    def resolve_conflict(self, key: str, left: MemoryValue, right: MemoryValue) -> MemoryValue:
        """Resolve a conflict using the configured strategy."""
        winner = right if right.version >= left.version else left
        self.store[key] = winner
        return winner

    def request_full_sync(self, target_node: str) -> None:
        """Ask target_node for all known keys."""
        self._send_memory_message(
            MEMORY_PULL_REQUEST,
            {"node_id": self.node_id, "keys": None},
            target_node=target_node,
        )

    def handle_memory_message(self, envelope: dict[str, Any]) -> None:
        """Handle one externally received distributed memory envelope."""
        msg_type = envelope.get("type")
        payload = envelope.get("payload") or {}
        source = envelope.get("source_node")

        if msg_type == MEMORY_WRITE:
            self._handle_remote_write(str(source or ""), dict(payload))
        elif msg_type == MEMORY_REPLICATE:
            self._handle_remote_write(str(source or ""), dict(payload))
        elif msg_type == MEMORY_PULL_REQUEST:
            self._handle_pull_request(str(source or ""), dict(payload))
        elif msg_type == MEMORY_PULL_RESPONSE:
            self._handle_pull_response(str(source or ""), dict(payload))

    def _send_memory_message(self, msg_type: str, payload: dict[str, Any], target_node: str = "*") -> None:
        """Send a memory protocol envelope if transport is configured."""
        if not self.transport or self.mode == "strong_local":
            return
        envelope = {
            "version": 1,
            "type": msg_type,
            "source_node": self.node_id,
            "target_node": target_node,
            "timestamp": self._now(),
            "payload": payload,
        }
        self.transport.send(envelope)

    def _handle_remote_write(self, source_node: str, payload: dict[str, Any]) -> None:
        """Store a remote memory update and invoke conflict resolution when needed."""
        key = payload.get("key")
        value = payload.get("value")
        if not key:
            return

        if key in self.store:
            self.store[key] = self._resolve_remote_conflict(self.store[key], value)
        else:
            self.store[key] = value

        self.node_store.setdefault(source_node, {})[key] = self.store[key]

    def _handle_pull_request(self, source_node: str, payload: dict[str, Any]) -> None:
        """Respond to a full or partial sync request with known entries."""
        if not self.transport:
            return
        keys = payload.get("keys") or list(self.store.keys())
        entries = []
        for key in keys:
            if key not in self.store:
                continue
            item = self.store[key]
            entries.append(
                {
                    "key": key,
                    "value": item.value if isinstance(item, MemoryValue) else item,
                    "version": item.version if isinstance(item, MemoryValue) else None,
                }
            )
        self._send_memory_message(MEMORY_PULL_RESPONSE, {"entries": entries}, target_node=source_node)

    def _handle_pull_response(self, source_node: str, payload: dict[str, Any]) -> None:
        """Merge entries from a pull response without overwriting existing keys."""
        entries = payload.get("entries") or []
        for entry in entries:
            key = entry.get("key")
            if not key:
                continue
            if key not in self.store:
                value = entry.get("value")
                self.store[key] = value
                self.node_store.setdefault(source_node, {})[key] = value

    def remove_node(self, node_id: str) -> bool:
        """Remove per-node memory state."""
        return self.node_store.pop(node_id, None) is not None

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe memory snapshot."""
        return {
            "store": {key: self._unwrap(value) for key, value in self.store.items()},
            "node_store": {
                node: {key: self._unwrap(value) for key, value in values.items()}
                for node, values in self.node_store.items()
            },
            "mode": self.mode,
        }

    def _resolve_remote_conflict(self, local_value: Any, remote_value: Any) -> Any:
        """Resolve a remote conflict while preserving the legacy signature."""
        try:
            return self.resolve_conflict(local_value, remote_value)  # type: ignore[misc]
        except TypeError:
            if isinstance(local_value, MemoryValue) and isinstance(remote_value, MemoryValue):
                return self.resolve_conflict("remote", local_value, remote_value)
            return remote_value

    @staticmethod
    def _unwrap(value: Any) -> Any:
        """Return the plain value for MemoryValue or raw entries."""
        return value.value if isinstance(value, MemoryValue) else value

    @staticmethod
    def _now() -> str:
        """Return an ISO-8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "DistributedMemory",
    "MEMORY_CONFLICT",
    "MEMORY_PULL_REQUEST",
    "MEMORY_PULL_RESPONSE",
    "MEMORY_REPLICATE",
    "MEMORY_WRITE",
    "MemoryValue",
]

