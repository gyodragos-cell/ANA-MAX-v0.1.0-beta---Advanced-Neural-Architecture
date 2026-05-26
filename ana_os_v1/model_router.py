"""Model router for ANA MAX AI Kernel v1."""

from __future__ import annotations

from typing import Any


class ModelRouter:
    """Route fake model inference to healthy placed nodes."""

    def __init__(self, model_registry: Any, placement_manager: Any, cluster_manager: Any, vector_memory: Any = None) -> None:
        """Initialize router dependencies."""
        self.model_registry = model_registry
        self.placement_manager = placement_manager
        self.cluster_manager = cluster_manager
        self.vector_memory = vector_memory
        self.sticky_sessions: dict[str, str] = {}
        self._rr: dict[tuple[str, str], int] = {}

    def route(self, model: str, version: str | None = None, capability: str | None = None) -> str | None:
        """Return the best node for a model inference request."""
        record = self.model_registry.get_model(model, version)
        if record is None:
            return None
        selected_version = str(record.get("version"))
        placement = None
        if hasattr(self.placement_manager, "get_placement"):
            placement = self.placement_manager.get_placement(model, selected_version)
        candidates = self._active_nodes()
        if placement:
            nodes = placement.get("nodes")
            if nodes != "all":
                allowed = set(nodes or [])
                candidates = [node for node in candidates if node.node_id in allowed]
        if capability:
            capable = [node for node in candidates if capability in getattr(node, "capabilities", []) or getattr(node, "metadata", {}).get("capability") == capability]
            candidates = capable or candidates
        if not candidates:
            return self.cluster_manager.get_best_node(capability=capability)
        key = (model, selected_version)
        index = self._rr.get(key, 0) % len(candidates)
        self._rr[key] = index + 1
        return candidates[index].node_id

    def route_inference(self, model_name: str, version: str | None = None, capability: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Select a node for model inference."""
        model = self.model_registry.get_model(model_name, version)
        if model is None:
            return {"success": False, "error": "model not found"}
        selected_version = model["version"]
        if session_id and session_id in self.sticky_sessions:
            node_id = self.sticky_sessions[session_id]
            node = self.cluster_manager.nodes.get(node_id)
            if node and getattr(node, "healthy", False):
                return {"success": True, "node_id": node_id, "model": model_name, "version": selected_version, "sticky": True}
        node_id = self.route(model_name, selected_version, capability)
        if session_id and node_id:
            self.sticky_sessions[session_id] = node_id
        return {"success": node_id is not None, "node_id": node_id, "model": model_name, "version": selected_version}

    def _active_nodes(self) -> list[Any]:
        """Return healthy ACTIVE nodes sorted by node_id."""
        nodes = []
        for node in getattr(self.cluster_manager, "nodes", {}).values():
            state = getattr(node, "state", None)
            state_value = getattr(state, "value", state)
            if getattr(node, "healthy", False) and state_value == "active":
                nodes.append(node)
        return sorted(nodes, key=lambda item: item.node_id)


__all__ = ["ModelRouter"]

