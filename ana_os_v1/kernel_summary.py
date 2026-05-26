"""Kernel summary and audit helpers for ANA MAX OS public release build."""

from __future__ import annotations

from typing import Any


class KernelSummary:
    """Aggregate subsystem summaries without mutating runtime state."""

    def __init__(self, **providers: Any) -> None:
        """Initialize provider map."""
        self.providers = dict(providers)

    def health(self) -> dict[str, Any]:
        """Return kernel health."""
        cluster = self.providers.get("cluster")
        if hasattr(cluster, "kernel_health_summary"):
            return cluster.kernel_health_summary()
        return {"healthy": True, "nodes": 0}

    def debug(self) -> dict[str, Any]:
        """Return debug summary."""
        return {"providers": sorted(self.providers), "breakpoints": len(getattr(self.providers.get("debug"), "breakpoints", []))}

    def metrics(self) -> dict[str, Any]:
        """Return metrics summary."""
        metrics = self.providers.get("metrics")
        return metrics.snapshot() if hasattr(metrics, "snapshot") else {}

    def recovery(self) -> dict[str, Any]:
        """Return recovery summary."""
        return {"available": self.providers.get("recovery") is not None}

    def consistency(self) -> dict[str, Any]:
        """Return consistency modes."""
        memory = self.providers.get("memory")
        fs_sync = self.providers.get("fs")
        return {"memory": getattr(memory, "mode", None), "fs": getattr(fs_sync, "mode", None)}

    def routing(self) -> dict[str, Any]:
        """Return routing summary."""
        cluster = self.providers.get("cluster")
        return cluster.kernel_routing_summary() if hasattr(cluster, "kernel_routing_summary") else {}

    def models(self) -> dict[str, Any]:
        """Return model summary."""
        registry = self.providers.get("models")
        return {"count": len(registry.list_models()) if hasattr(registry, "list_models") else 0}

    def agents(self) -> dict[str, Any]:
        """Return agent summary."""
        agents = self.providers.get("agents")
        return {"count": len(agents.list_agents()) if hasattr(agents, "list_agents") else 0}

    def pipelines(self) -> dict[str, Any]:
        """Return pipeline summary."""
        return {"available": self.providers.get("pipelines") is not None}

    def vectors(self) -> dict[str, Any]:
        """Return vector summary."""
        vectors = self.providers.get("vectors")
        return {"count": len(getattr(vectors, "vectors", {}))}

    def federation(self) -> dict[str, Any]:
        """Return federation summary."""
        federation = self.providers.get("federation")
        return {"clusters": len(getattr(federation, "clusters", {})), "domain": getattr(federation, "domain", None)}

    def full(self) -> dict[str, Any]:
        """Return all summaries."""
        return {
            "health": self.health(),
            "debug": self.debug(),
            "metrics": self.metrics(),
            "recovery": self.recovery(),
            "consistency": self.consistency(),
            "routing": self.routing(),
            "models": self.models(),
            "agents": self.agents(),
            "pipelines": self.pipelines(),
            "vectors": self.vectors(),
            "federation": self.federation(),
        }


__all__ = ["KernelSummary"]

