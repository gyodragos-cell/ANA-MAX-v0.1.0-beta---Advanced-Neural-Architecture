from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .store import Store


SERVICES = [
    ("ana_max_mcp", 8766, "/health"),
    ("gpt_only_guard", 8771, "/health"),
    ("operator_gateway", 8772, "/health"),
    ("legacy_backend", 8765, "/health"),
    ("universal_gateway", 8768, "/health"),
    ("dashboard", 8780, "/health"),
    ("ollama", 11434, "/api/tags"),
]


def _listener_map() -> dict[int, list[dict[str, Any]]]:
    """Enumerate listening TCP sockets without command lines or environment values."""
    try:
        import psutil
    except ImportError:
        return {}
    result: dict[int, list[dict[str, Any]]] = {}
    try:
        connections = psutil.net_connections(kind="tcp")
    except (OSError, psutil.Error):
        return {}
    for connection in connections:
        if connection.status != psutil.CONN_LISTEN or not connection.laddr:
            continue
        port = int(connection.laddr.port)
        pid = connection.pid
        name = "unknown"
        if pid:
            try:
                name = psutil.Process(pid).name()
            except (OSError, psutil.Error):
                name = "unavailable"
        result.setdefault(port, []).append({
            "pid": int(pid) if pid else None,
            "process_name": name,
            "bind_address": str(connection.laddr.ip),
        })
    return result


def snapshot_loopback(store: Store, timeout: float = 1.2) -> dict[str, Any]:
    """Read-only health probes and local listener metadata; never starts/stops a process."""
    listeners = _listener_map()
    observed = []
    exposure_risks = []
    for name, port, route in SERVICES:
        url = f"http://127.0.0.1:{port}{route}"
        row: dict[str, Any] = {"kind": "service", "name": name, "port": port, "probe": route}
        try:
            req = Request(url, headers={"Accept": "application/json"}, method="GET")
            with urlopen(req, timeout=timeout) as response:
                row["status"] = "running" if 200 <= response.status < 300 else "degraded"
                row["http_status"] = response.status
                payload = json.loads(response.read(65_536).decode("utf-8", "replace"))
                if isinstance(payload, dict) and name != "ollama":
                    row["health_evidence"] = {
                        key: payload[key] for key in ("status", "agent", "version", "tools_count", "mcp_ready", "profile", "policy_version", "gateway", "backend_up")
                        if key in payload
                    }
                elif isinstance(payload, dict):
                    row["health_evidence"] = {"model_count": len(payload.get("models", []))}
                else:
                    row["health_evidence"] = {}
        except HTTPError as exc:
            row.update({"status": "responding_denied_or_error", "http_status": exc.code})
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            row.update({"status": "offline_or_timeout", "error_type": type(exc).__name__})

        port_listeners = listeners.get(port, [])
        row["listener_count"] = len(port_listeners)
        row["listener_processes"] = port_listeners
        wildcard_bindings = [item for item in port_listeners if item["bind_address"] in {"0.0.0.0", "::", "0:0:0:0:0:0:0:0"}]
        if wildcard_bindings:
            exposure_risks.append({
                "port": port,
                "service": name,
                "reason": "wildcard_listener",
                "pids": [item["pid"] for item in wildcard_bindings if item["pid"]],
            })

        raw_status = row["status"]
        if raw_status == "responding_denied_or_error":
            service_status = "degraded"
        elif raw_status == "offline_or_timeout":
            service_status = "degraded" if port_listeners else "offline"
        else:
            service_status = raw_status

        service_node = store.upsert_capability(
            kind="service", name=name, status=service_status,
            evidence={
                "source": "loopback_http_probe",
                "url": url,
                **{k: v for k, v in row.items() if k not in {"kind", "name", "status", "url"}},
                "observed_status": raw_status,
            },
            owner="OS29 read-only runtime snapshot",
        )
        port_status = "degraded" if wildcard_bindings else ("running" if port_listeners or row.get("http_status") else "offline")
        port_node = store.upsert_capability(
            kind="port", name=f"127.0.0.1:{port}", status=port_status,
            evidence={
                "source": "loopback_probe_and_listener_table",
                "port": port,
                "listener_count": len(port_listeners),
                "listeners": port_listeners,
                "wildcard_binding": bool(wildcard_bindings),
            },
            owner="OS29 read-only runtime snapshot",
        )
        store.upsert_capability_edge(
            source_node_id=service_node["node_id"],
            target_node_id=port_node["node_id"],
            relation="probes_port",
            evidence={"http_route": route, "health_status": raw_status, "http_status": row.get("http_status")},
        )
        for listener in port_listeners:
            if not listener["pid"]:
                continue
            process_node = store.upsert_capability(
                kind="process",
                name=f'{listener["process_name"]}#{listener["pid"]}',
                status="running",
                evidence={"pid": listener["pid"], "process_name": listener["process_name"], "bind_address": listener["bind_address"]},
                owner="OS29 read-only listener snapshot",
            )
            store.upsert_capability_edge(
                source_node_id=process_node["node_id"],
                target_node_id=port_node["node_id"],
                relation="listens_on",
                evidence={"pid": listener["pid"], "bind_address": listener["bind_address"]},
            )
        observed.append({
            "snapshot": row,
            "service_node_id": service_node["node_id"],
            "port_node_id": port_node["node_id"],
        })
    return {
        "status": "complete",
        "probe_scope": "HTTP probes to 127.0.0.1 only; listener inventory is local read-only",
        "services": observed,
        "exposure_risks": exposure_risks,
        "store": store.stats(),
    }