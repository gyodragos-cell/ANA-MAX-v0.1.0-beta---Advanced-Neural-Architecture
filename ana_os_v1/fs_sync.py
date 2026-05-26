"""Filesystem sync layer for ANA MAX OS dev mode."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ana_os_v1.transport import Transport


FS_UPDATE = "fs.update"
FS_DELETE = "fs.delete"
FS_PULL_REQUEST = "fs.pull_request"
FS_PULL_RESPONSE = "fs.pull_response"


class FSSync:
    """Local filesystem sync with optional best-effort transport broadcast."""

    def __init__(
        self,
        root_path: str,
        transport: Transport | None = None,
        node_id: str = "local",
        mode: str = "eventual",
        cleanup_on_leave: bool = False,
    ) -> None:
        """Initialize sync root and optional transport."""
        self.root_path = Path(root_path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.transport = transport
        self.node_id = node_id
        self.mode = mode
        self.cleanup_on_leave = cleanup_on_leave
        self._remote_mtimes: dict[str, str] = {}

    def write_file(self, path: str, content: str | bytes) -> dict[str, Any]:
        """Write a file under root_path and broadcast an fs.update if configured."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(str(content), encoding="utf-8")
        mtime = self._get_mtime(target)
        self._broadcast_update(path, content, mtime)
        return {"success": True, "path": path, "mtime": mtime}

    def delete_file(self, path: str) -> dict[str, Any]:
        """Delete a file under root_path and broadcast an fs.delete if configured."""
        target = self._resolve_path(path)
        existed = target.exists()
        if existed:
            target.unlink()
        mtime = self._now()
        self._remote_mtimes[path] = mtime
        self._broadcast_delete(path, mtime)
        return {"success": True, "path": path, "deleted": existed, "mtime": mtime}

    def handle_fs_message(self, envelope: dict[str, Any]) -> None:
        """Handle one externally received distributed FS envelope."""
        msg_type = envelope.get("type")
        payload = envelope.get("payload") or {}
        source = envelope.get("source_node")

        if msg_type == FS_UPDATE:
            self._handle_remote_update(str(source or ""), dict(payload))
        elif msg_type == FS_DELETE:
            self._handle_remote_delete(str(source or ""), dict(payload))
        elif msg_type == FS_PULL_REQUEST:
            self._handle_pull_request(str(source or ""), dict(payload))
        elif msg_type == FS_PULL_RESPONSE:
            self._handle_pull_response(str(source or ""), dict(payload))

    def request_full_fs_sync(self, target_node: str) -> None:
        """Ask target_node for the full known filesystem tree."""
        self._send_fs_message(FS_PULL_REQUEST, {"node_id": self.node_id, "paths": None}, target_node=target_node)

    def _send_fs_message(self, msg_type: str, payload: dict[str, Any], target_node: str = "*") -> None:
        """Send an FS protocol envelope if transport is configured."""
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
        try:
            self.transport.send(envelope)
        except Exception:
            return

    def _broadcast_update(self, path: str, content: str | bytes, mtime: str) -> None:
        """Broadcast a local file update."""
        self._send_fs_message(
            FS_UPDATE,
            {
                "path": path,
                "content": self._encode_content(content),
                "mtime": mtime,
                "node_id": self.node_id,
            },
        )

    def _broadcast_delete(self, path: str, mtime: str) -> None:
        """Broadcast a local file delete."""
        self._send_fs_message(FS_DELETE, {"path": path, "mtime": mtime, "node_id": self.node_id})

    def _handle_remote_update(self, source_node: str, payload: dict[str, Any]) -> None:
        """Apply a remote update if it wins by mtime."""
        path = payload.get("path")
        content_str = payload.get("content")
        mtime = str(payload.get("mtime") or self._now())
        if not path:
            return
        local_mtime = self._get_mtime_safe(str(path))
        if not local_mtime or self._is_newer(mtime, local_mtime):
            self._apply_remote_write(str(path), self._decode_content(content_str), mtime)

    def _handle_remote_delete(self, source_node: str, payload: dict[str, Any]) -> None:
        """Apply a remote delete if it wins by mtime."""
        path = payload.get("path")
        mtime = str(payload.get("mtime") or self._now())
        if not path:
            return
        local_mtime = self._get_mtime_safe(str(path))
        if not local_mtime or self._is_newer(mtime, local_mtime):
            self._apply_remote_delete(str(path), mtime)

    def _handle_pull_request(self, source_node: str, payload: dict[str, Any]) -> None:
        """Respond to a full or partial filesystem sync request."""
        if not self.transport:
            return
        paths = payload.get("paths")
        if paths is None:
            paths = self._list_all_paths()
        entries = []
        for item in paths:
            info = self._get_file_entry(str(item))
            if info:
                entries.append(info)
        self._send_fs_message(FS_PULL_RESPONSE, {"entries": entries}, target_node=source_node)

    def _handle_pull_response(self, source_node: str, payload: dict[str, Any]) -> None:
        """Merge entries from a pull response using LWW."""
        entries = payload.get("entries") or []
        for entry in entries:
            path = entry.get("path")
            mtime = str(entry.get("mtime") or self._now())
            if not path:
                continue
            local_mtime = self._get_mtime_safe(str(path))
            if local_mtime and not self._is_newer(mtime, local_mtime):
                continue
            if entry.get("deleted", False):
                self._apply_remote_delete(str(path), mtime)
            else:
                self._apply_remote_write(str(path), self._decode_content(entry.get("content")), mtime)

    def _get_mtime_safe(self, path: str) -> str | None:
        """Return a file mtime or remote tombstone mtime if known."""
        target = self._resolve_path(path)
        if target.exists():
            return self._get_mtime(target)
        return self._remote_mtimes.get(path)

    def _is_newer(self, remote_mtime: Any, local_mtime: Any) -> bool:
        """Compare numeric or ISO-ish mtimes as strings."""
        return str(remote_mtime) > str(local_mtime)

    def _apply_remote_write(self, path: str, content: str, mtime: str) -> None:
        """Write remote content locally without re-broadcasting."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._remote_mtimes[path] = mtime

    def _apply_remote_delete(self, path: str, mtime: str) -> None:
        """Delete remote content locally without re-broadcasting."""
        target = self._resolve_path(path)
        if target.exists():
            target.unlink()
        self._remote_mtimes[path] = mtime

    def _list_all_paths(self) -> list[str]:
        """List all regular file paths relative to root_path."""
        return [
            str(path.relative_to(self.root_path)).replace("\\", "/")
            for path in self.root_path.rglob("*")
            if path.is_file()
        ]

    def _get_file_entry(self, path: str) -> dict[str, Any] | None:
        """Return a pull_response entry for one file path."""
        target = self._resolve_path(path)
        if not target.exists() or not target.is_file():
            return None
        content = target.read_text(encoding="utf-8")
        return {"path": path, "content": self._encode_content(content), "mtime": self._get_mtime(target), "deleted": False}

    def cleanup_node(self, node_id: str) -> dict[str, Any]:
        """Optional cleanup hook for node leave."""
        return {"success": True, "node_id": node_id, "cleanup_enabled": self.cleanup_on_leave}

    def snapshot(self) -> dict[str, Any]:
        """Return a compact filesystem snapshot."""
        return {
            "mode": self.mode,
            "files": {path: self._get_file_entry(path) for path in self._list_all_paths()},
            "root_path": str(self.root_path),
        }

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path safely under root_path."""
        target = (self.root_path / path).resolve()
        if self.root_path != target and self.root_path not in target.parents:
            raise ValueError("path escapes sync root")
        return target

    def _get_mtime(self, path: Path) -> str:
        """Return a stable ISO-8601 mtime for a path."""
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _encode_content(content: str | bytes) -> str:
        """Encode content for the current text-only transport phase."""
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return str(content)

    @staticmethod
    def _decode_content(content_str: Any) -> str:
        """Decode content from the current text-only transport phase."""
        return "" if content_str is None else str(content_str)

    @staticmethod
    def _now() -> str:
        """Return an ISO-8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")


__all__ = ["FS_DELETE", "FS_PULL_REQUEST", "FS_PULL_RESPONSE", "FS_UPDATE", "FSSync"]

