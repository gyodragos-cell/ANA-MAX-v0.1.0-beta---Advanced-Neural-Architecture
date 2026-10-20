from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit


class ScopePolicy:
    """Explicit, fail-closed scope for local debugging and security research."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "os29.scope.v1":
            raise ValueError("unsupported scope schema")
        self.data = data
        self.approved_hosts = {str(x).strip().lower().rstrip(".") for x in data.get("approved_hosts", [])}
        self.approved_ports = {int(x) for x in data.get("approved_ports", [])}
        self.approved_networks = [
            ipaddress.ip_network(str(x), strict=False) for x in data.get("approved_networks", [])
        ]
        self.approved_device_ids = {
            str(x).strip() for x in data.get("approved_device_ids", []) if str(x).strip()
        }
        self.approved_process_names = {
            str(x).strip().lower() for x in data.get("approved_process_names", []) if str(x).strip()
        }

    def check_device(self, device_id: str) -> dict[str, object]:
        requested = str(device_id or "").strip()
        if not requested:
            return {"allowed": False, "reason": "missing_device_id"}
        if requested not in self.approved_device_ids:
            return {"allowed": False, "reason": "device_not_explicitly_approved"}
        return {"allowed": True, "reason": "explicit_device_match", "device_id": requested}

    def check_target(self, target: str) -> dict[str, object]:
        try:
            parsed = urlsplit(str(target))
            if parsed.scheme.lower() not in {"http", "https"}:
                return {"allowed": False, "reason": "scheme_not_allowed"}
            if not parsed.hostname:
                return {"allowed": False, "reason": "missing_hostname"}
            if parsed.username is not None or parsed.password is not None:
                return {"allowed": False, "reason": "embedded_credentials_forbidden"}
            host = parsed.hostname.lower().rstrip(".")
            try:
                port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            except ValueError:
                return {"allowed": False, "reason": "invalid_port"}
            host_allowed = host in self.approved_hosts
            if not host_allowed:
                try:
                    address = ipaddress.ip_address(host)
                    host_allowed = any(address in network for network in self.approved_networks)
                except ValueError:
                    host_allowed = False
            if not host_allowed:
                return {"allowed": False, "reason": "host_not_in_scope", "host": host, "port": port}
            if self.approved_ports and port not in self.approved_ports:
                return {"allowed": False, "reason": "port_not_in_scope", "host": host, "port": port}
            return {
                "allowed": True,
                "reason": "explicit_local_scope_match",
                "host": host,
                "port": port,
                "scheme": parsed.scheme.lower(),
            }
        except (TypeError, ValueError):
            return {"allowed": False, "reason": "invalid_target"}

    def check_process(self, process_name: str) -> dict[str, object]:
        name = Path(str(process_name)).name.lower()
        if not name:
            return {"allowed": False, "reason": "missing_process_name"}
        if name not in self.approved_process_names:
            return {"allowed": False, "reason": "process_not_explicitly_approved", "process": name}
        return {"allowed": True, "reason": "explicit_process_match", "process": name}