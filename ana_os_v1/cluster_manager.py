"""Cluster manager for ANA MAX v27 dev runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ana_os_v1.transport import Transport


CLUSTER_JOIN = "cluster.join"
CLUSTER_LEAVE = "cluster.leave"
CLUSTER_HEARTBEAT = "cluster.heartbeat"


class NodeState(str, Enum):
    """Cluster node membership state."""

    JOINING = "joining"
    ACTIVE = "active"
    SUSPECT = "suspect"
    DEAD = "dead"


@dataclass
class ClusterNode:
    """Cluster node state."""

    node_id: str
    healthy: bool = True
    load: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)
    last_heartbeat: str | None = None
    address: str = "127.0.0.1"
    port: int = 0
    capabilities: list[str] = field(default_factory=list)
    state: NodeState = NodeState.ACTIVE
    missed_heartbeats: int = 0


class ClusterManager:
    """Manage fake node discovery, health, load, and failover."""

    def __init__(
        self,
        node_id: str = "local",
        transport: Transport | None = None,
        event_bus: Any = None,
        cluster_id: str = "local-cluster",
        domain: str = "local",
    ) -> None:
        """Initialize cluster state."""
        self.node_id = node_id
        self.cluster_id = cluster_id
        self.domain = domain
        self.transport = transport
        self.event_bus = event_bus
        self.nodes: dict[str, ClusterNode] = {}
        self._rr_index = 0
        self._capability_rr: dict[str, int] = {}
        self.consistency_mode = "eventual"
        self.kernel_version = "ANA MAX AI Kernel v1"
        self.node_labels: dict[str, list[str]] = {}
        self.node_annotations: dict[str, dict[str, Any]] = {}

    def join(self, node_id: str | None = None, metadata: dict[str, str] | None = None) -> ClusterNode:
        """Join a node locally or announce this node over transport."""
        target_id = node_id or self.node_id
        node = self.nodes.get(target_id)
        if node is None:
            node = ClusterNode(node_id=target_id, metadata=dict(metadata or {}), last_heartbeat=self._now())
        else:
            node.metadata.update(dict(metadata or {}))
            node.last_heartbeat = self._now()
        node.state = NodeState.ACTIVE
        node.healthy = True
        node.missed_heartbeats = 0
        self.nodes[target_id] = node
        if node_id is None:
            self._send_cluster_message(
                CLUSTER_JOIN,
                {
                    "node_id": self.node_id,
                    "address": node.address,
                    "port": node.port,
                    "capabilities": list(node.capabilities),
                },
                target_node="*",
            )
        return node

    def leave(self, node_id: str | None = None, reason: str = "") -> bool:
        """Remove a node locally or announce this node leaving over transport."""
        if node_id is None:
            self._send_cluster_message(CLUSTER_LEAVE, {"node_id": self.node_id, "reason": reason}, target_node="*")
            return self.evict(self.node_id, reason=reason)
        return self.nodes.pop(node_id, None) is not None

    def mark_health(self, node_id: str, healthy: bool) -> None:
        """Set node health."""
        self.nodes[node_id].healthy = healthy

    def heartbeat(self, node_id: str, load: float | None = None) -> dict[str, str | bool | float]:
        """Record a simulated heartbeat for one node."""
        node = self.nodes.get(node_id)
        if node is None:
            node = ClusterNode(node_id=node_id, last_heartbeat=self._now())
            self.nodes[node_id] = node
        node.last_heartbeat = self._now()
        if load is not None:
            node.load = max(0.0, float(load))
        node.healthy = True
        node.state = NodeState.ACTIVE
        node.missed_heartbeats = 0
        self._publish_event("node.recovered", {"node_id": node_id, "reason": "heartbeat"})
        return {"success": True, "node_id": node_id, "load": node.load, "healthy": node.healthy}

    def send_heartbeat(self) -> None:
        """Send a heartbeat message for this node over the transport."""
        self._send_cluster_message(CLUSTER_HEARTBEAT, {"node_id": self.node_id}, target_node="*")

    def check_heartbeats(self, max_missed: int = 3) -> None:
        """Update remote node state based on missed heartbeats."""
        for node_id, node in self.nodes.items():
            if node_id == self.node_id or node.state == NodeState.DEAD:
                continue
            node.missed_heartbeats += 1
            if node.missed_heartbeats >= max_missed:
                if node.state == NodeState.ACTIVE:
                    self.mark_unhealthy(node_id, reason="missed_heartbeats")
                elif node.state == NodeState.SUSPECT:
                    self.evict(node_id, reason="missed_heartbeats")

    def check_node_health(self, max_missed: int = 3) -> dict[str, Any]:
        """Run one local health-monitor tick and return a snapshot."""
        self.check_heartbeats(max_missed=max_missed)
        return self.snapshot()

    def mark_unhealthy(self, node_id: str, reason: str = "") -> bool:
        """Mark a node unhealthy and move it to SUSPECT state."""
        changed = self.mark_suspect(node_id, reason=reason)
        if changed:
            self._publish_event("node.unhealthy", {"node_id": node_id, "reason": reason})
        return changed

    def mark_recovered(self, node_id: str, reason: str = "") -> bool:
        """Mark a node recovered and move it to ACTIVE state."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        node.state = NodeState.ACTIVE
        node.healthy = True
        node.missed_heartbeats = 0
        node.last_heartbeat = self._now()
        self._publish_event("node.recovered", {"node_id": node_id, "reason": reason})
        return True

    def mark_suspect(self, node_id: str, reason: str = "") -> bool:
        """Mark a node as suspect without resetting missed heartbeat count."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        node.state = NodeState.SUSPECT
        node.healthy = False
        self._publish_event("node.suspect", {"node_id": node_id, "reason": reason})
        return True

    def evict(self, node_id: str, reason: str = "") -> bool:
        """Mark a node as dead while preserving membership history."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        node.state = NodeState.DEAD
        node.healthy = False
        self._publish_event("node.dead", {"node_id": node_id, "reason": reason})
        return True

    def handle_cluster_message(self, envelope: dict[str, Any]) -> None:
        """Handle one externally received cluster transport envelope."""
        msg_type = envelope.get("type")
        payload = envelope.get("payload") or {}
        source_node = envelope.get("source_node")
        if msg_type == CLUSTER_JOIN:
            self._handle_join(str(source_node or payload.get("node_id") or ""), dict(payload))
        elif msg_type == CLUSTER_LEAVE:
            self._handle_leave(str(source_node or payload.get("node_id") or ""), dict(payload))
        elif msg_type == CLUSTER_HEARTBEAT:
            self._handle_heartbeat(str(source_node or payload.get("node_id") or ""), dict(payload))

    def choose_node(self) -> str | None:
        """Choose a healthy node using round-robin with load as a tiebreaker."""
        healthy = [node for node in self.nodes.values() if node.healthy]
        if not healthy:
            return None
        healthy.sort(key=lambda node: (node.load, node.node_id))
        node = healthy[self._rr_index % len(healthy)]
        self._rr_index += 1
        return node.node_id

    def get_best_node(self, capability: str | None = None) -> str | None:
        """Return the best node for routing, skipping SUSPECT and DEAD nodes."""
        candidates = self._routing_candidates(capability, NodeState.ACTIVE)
        if not candidates:
            candidates = self._routing_candidates(capability, NodeState.JOINING)
        if not candidates:
            return None
        key = capability or "__all__"
        index = self._capability_rr.get(key, 0) % len(candidates)
        self._capability_rr[key] = index + 1
        selected = candidates[index]
        self._publish_event("routing.changed", {"selected_node": selected.node_id, "capability": capability})
        return selected.node_id

    def failover(self, failed_node: str) -> str | None:
        """Mark a node unhealthy and choose a replacement."""
        if failed_node in self.nodes:
            self.mark_unhealthy(failed_node, reason="failover")
        return self.get_best_node()

    def snapshot(self) -> dict[str, dict[str, str | bool | float | None]]:
        """Return a JSON-safe cluster snapshot."""
        return {
            node_id: {
                "node_id": node.node_id,
                "healthy": node.healthy,
                "load": node.load,
                "last_heartbeat": node.last_heartbeat,
                "state": node.state.value,
                "missed_heartbeats": node.missed_heartbeats,
            }
            for node_id, node in self.nodes.items()
        }

    def kernel_health_summary(self) -> dict[str, Any]:
        """Return a compact kernel health summary."""
        states = {state.value: 0 for state in NodeState}
        for node in self.nodes.values():
            states[node.state.value] += 1
        return {"kernel_version": self.kernel_version, "nodes": len(self.nodes), "states": states, "healthy": states["dead"] == 0}

    def kernel_routing_summary(self) -> dict[str, Any]:
        """Return routing-related cluster state."""
        return {"rr_index": self._rr_index, "capability_rr": dict(self._capability_rr), "mode": self.consistency_mode}

    def set_node_labels(self, node_id: str, labels: list[str]) -> None:
        """Set arbitrary labels for a node."""
        self.node_labels[node_id] = list(labels)

    def set_node_annotations(self, node_id: str, annotations: dict[str, Any]) -> None:
        """Set arbitrary annotations for a node."""
        self.node_annotations[node_id] = dict(annotations)

    def _send_cluster_message(self, msg_type: str, payload: dict[str, Any], target_node: str | None = None) -> None:
        """Send a cluster protocol envelope if transport is configured."""
        if not self.transport:
            return
        envelope = {
            "version": 1,
            "type": msg_type,
            "source_node": self.node_id,
            "target_node": target_node or "*",
            "timestamp": self._now(),
            "payload": payload,
        }
        self.transport.send(envelope)

    def _handle_join(self, node_id: str, payload: dict[str, Any]) -> None:
        """Register or activate a node from a join envelope."""
        if not node_id:
            return
        node = self.nodes.get(node_id)
        if node is None:
            node = ClusterNode(
                node_id=node_id,
                address=str(payload.get("address", "127.0.0.1")),
                port=int(payload.get("port", 0)),
                capabilities=list(payload.get("capabilities", [])),
                last_heartbeat=self._now(),
            )
            self.nodes[node_id] = node
        node.state = NodeState.ACTIVE
        node.healthy = True
        node.missed_heartbeats = 0

    def _handle_leave(self, node_id: str, payload: dict[str, Any]) -> None:
        """Mark a node as dead from a leave envelope."""
        if not node_id:
            return
        self.evict(node_id, reason=str(payload.get("reason", "")))

    def _handle_heartbeat(self, node_id: str, payload: dict[str, Any]) -> None:
        """Apply an incoming heartbeat using existing heartbeat logic."""
        if not node_id:
            return
        self.heartbeat(node_id)

    def _publish_event(self, category: str, payload: dict[str, Any]) -> None:
        """Publish an event when an event bus is configured."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(category, payload)

    def _routing_candidates(self, capability: str | None, state: NodeState) -> list[ClusterNode]:
        """Return sorted nodes matching routing requirements."""
        nodes = [node for node in self.nodes.values() if node.state == state and node.healthy]
        if capability:
            nodes = [
                node
                for node in nodes
                if capability in node.capabilities or node.metadata.get("capability") == capability
            ]
        return sorted(nodes, key=lambda node: (node.load, node.node_id))

    @staticmethod
    def _now() -> str:
        """Return an ISO-8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "CLUSTER_HEARTBEAT",
    "CLUSTER_JOIN",
    "CLUSTER_LEAVE",
    "ClusterManager",
    "ClusterNode",
    "NodeState",
]

