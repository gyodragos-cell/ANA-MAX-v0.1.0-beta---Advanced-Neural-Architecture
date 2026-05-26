"""AI OS service manager for long-running services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


HealthCheck = Callable[[], bool]


@dataclass
class ServiceRecord:
    """Service lifecycle state."""

    name: str
    running: bool = False
    health_check: HealthCheck | None = None
    restart_count: int = 0
    node_id: str | None = None
    dependencies: list[str] | None = None
    priority: int = 100
    annotations: dict[str, Any] | None = None


class ServiceManager:
    """Register, start, stop, and health-check services."""

    def __init__(self, distributed_memory: Any = None, event_bus: Any = None, cluster_manager: Any = None, node_id: str = "local") -> None:
        """Initialize service registry."""
        self.services: dict[str, ServiceRecord] = {}
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.cluster_manager = cluster_manager
        self.node_id = node_id

    def register(self, name: str, health_check: HealthCheck | None = None) -> ServiceRecord:
        """Register a service."""
        record = ServiceRecord(name, False, health_check)
        self.services[name] = record
        return record

    def start(self, name: str) -> None:
        """Start a service."""
        self.services[name].running = True

    def stop(self, name: str) -> None:
        """Stop a service."""
        self.services[name].running = False

    def restart(self, name: str) -> dict[str, bool | int | str]:
        """Restart a service and increment its restart counter."""
        service = self.services[name]
        service.running = True
        service.restart_count += 1
        return {"name": name, "running": service.running, "restart_count": service.restart_count}

    def health(self, name: str) -> dict[str, bool | str]:
        """Return service health."""
        service = self.services[name]
        ok = service.running and (service.health_check() if service.health_check else True)
        return {"name": name, "healthy": bool(ok), "running": service.running, "restart_count": service.restart_count}

    def start_service(self, name: str, node_id: str | None = None) -> dict[str, Any]:
        """Start a distributed service and replicate registry state."""
        if name not in self.services:
            self.register(name)
        service = self.services[name]
        service.running = True
        service.node_id = node_id or self.node_id
        self._replicate_service(name)
        self._publish("service.start", {"name": name, "node_id": service.node_id})
        return self._service_payload(service)

    def stop_service(self, name: str) -> dict[str, Any]:
        """Stop a distributed service and replicate registry state."""
        if name not in self.services:
            self.register(name)
        service = self.services[name]
        service.running = False
        self._replicate_service(name)
        self._publish("service.stop", {"name": name, "node_id": service.node_id})
        return self._service_payload(service)

    def restart_service(self, name: str) -> dict[str, Any]:
        """Restart a distributed service and emit service.crash for recovery visibility."""
        if name not in self.services:
            self.register(name)
        result = self.restart(name)
        service = self.services[name]
        service.node_id = service.node_id or self.node_id
        self._replicate_service(name)
        self._publish("service.crash", {"name": name, "node_id": service.node_id, "restart_count": service.restart_count})
        return {**result, "node_id": service.node_id}

    def failover_services(self, dead_node: str) -> dict[str, Any]:
        """Reassign services from a dead node to the best available node."""
        reassigned = {}
        if self.cluster_manager and hasattr(self.cluster_manager, "mark_unhealthy"):
            self.cluster_manager.mark_unhealthy(dead_node, reason="service_failover")
        for name, service in self.services.items():
            if service.node_id != dead_node:
                continue
            replacement = self.cluster_manager.get_best_node() if self.cluster_manager else self.node_id
            service.node_id = replacement
            reassigned[name] = replacement
            self._replicate_service(name)
        return {"dead_node": dead_node, "reassigned": reassigned}

    def sync_registry(self) -> dict[str, Any]:
        """Replicate all known services."""
        for name in self.services:
            self._replicate_service(name)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe service registry snapshot."""
        return {name: self._service_payload(service) for name, service in self.services.items()}

    def _replicate_service(self, name: str) -> None:
        """Store one service record in distributed memory when configured."""
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"service:{name}", self._service_payload(self.services[name]), node_id=self.node_id)

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a service event when an event bus is configured."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)

    @staticmethod
    def _service_payload(service: ServiceRecord) -> dict[str, Any]:
        """Return a JSON-safe service payload."""
        return {
            "name": service.name,
            "running": service.running,
            "restart_count": service.restart_count,
            "node_id": service.node_id,
            "dependencies": list(service.dependencies or []),
            "priority": service.priority,
            "annotations": dict(service.annotations or {}),
        }

    def configure_service(
        self,
        name: str,
        dependencies: list[str] | None = None,
        priority: int = 100,
        annotations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Configure service v2 metadata."""
        if name not in self.services:
            self.register(name)
        service = self.services[name]
        service.dependencies = list(dependencies or [])
        service.priority = priority
        service.annotations = dict(annotations or {})
        self._replicate_service(name)
        return self._service_payload(service)

    def scale_service(self, name: str, replicas: int) -> dict[str, Any]:
        """Record a simulated scaling policy."""
        service = self.services.setdefault(name, ServiceRecord(name))
        service.annotations = {**dict(service.annotations or {}), "replicas": replicas}
        self._replicate_service(name)
        return self._service_payload(service)

    def service_summary(self) -> dict[str, Any]:
        """Return service runtime summary."""
        running = sum(1 for service in self.services.values() if service.running)
        return {"count": len(self.services), "running": running, "services": self.snapshot()}


__all__ = ["ServiceManager", "ServiceRecord"]

