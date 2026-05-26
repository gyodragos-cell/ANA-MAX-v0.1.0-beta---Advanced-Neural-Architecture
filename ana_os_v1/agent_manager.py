"""In-memory multi-agent manager for ANA MAX v24.

Agents are lightweight task records, not OS processes. This keeps multi-agent
mode safe and testable until real worker isolation is designed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AgentRecord:
    """One managed ANA MAX sub-agent record."""

    agent_id: str
    role: str
    task: str
    status: str = "idle"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe agent record."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "task": self.task,
            "status": self.status,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


class AgentManager:
    """Spawn, route, and clean up lightweight ANA MAX agents."""

    def __init__(self, distributed_memory: Any = None, event_bus: Any = None, cluster_manager: Any = None, fs_sync: Any = None, task_manager: Any = None) -> None:
        """Initialize an empty in-memory agent registry."""
        self.agents: dict[str, AgentRecord] = {}
        self.distributed_memory = distributed_memory
        self.event_bus = event_bus
        self.cluster_manager = cluster_manager
        self.fs_sync = fs_sync
        self.task_manager = task_manager
        self.registry: dict[str, dict[str, Any]] = {}

    def spawn_agent(self, role: str, task: str, metadata: Mapping[str, Any] | None = None) -> AgentRecord:
        """Create a tool, scenario, fallback, or analysis agent."""
        if role not in {"tool", "scenario", "fallback", "analysis", "planner", "executor", "critic", "repair", "observer"}:
            raise ValueError(f"unsupported agent role: {role}")
        record = AgentRecord(agent_id=str(uuid4()), role=role, task=task, metadata=dict(metadata or {}))
        self.agents[record.agent_id] = record
        return record

    def route_agent(self, task_type: str, task: str) -> AgentRecord:
        """Choose an agent role from a task type and spawn it."""
        role_map = {
            "tool": "tool",
            "scenario": "scenario",
            "fallback": "fallback",
            "analysis": "analysis",
        }
        return self.spawn_agent(role_map.get(task_type, "analysis"), task, {"task_type": task_type})

    def send_message(self, sender_id: str, receiver_id: str, message: str) -> dict[str, Any]:
        """Send an in-memory message between agents."""
        if sender_id not in self.agents or receiver_id not in self.agents:
            raise KeyError("sender or receiver agent does not exist")
        inbox = dict(self.agents[receiver_id].metadata).get("inbox", [])
        inbox.append({"from": sender_id, "message": message})
        metadata = dict(self.agents[receiver_id].metadata)
        metadata["inbox"] = inbox
        self.agents[receiver_id].metadata = metadata
        return inbox[-1]

    def resolve_conflict(self, agent_ids: list[str]) -> str:
        """Resolve conflicts by preferring critic, then planner, then first agent."""
        for role in ("critic", "planner"):
            for agent_id in agent_ids:
                if self.agents.get(agent_id) and self.agents[agent_id].role == role:
                    return agent_id
        return agent_ids[0]

    def cleanup_agent(self, agent_id: str) -> bool:
        """Remove an agent from the in-memory registry."""
        return self.agents.pop(agent_id, None) is not None

    def snapshot(self) -> dict[str, Any]:
        """Return all active agents."""
        return {"agents": {agent_id: record.to_dict() for agent_id, record in self.agents.items()}}

    def register_agent(self, name: str, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Register a named agent configuration."""
        self.registry[name] = {"name": name, "config": dict(config or {}), "state": "idle", "node_id": None, "inbox": []}
        self._replicate(name)
        return dict(self.registry[name])

    def unregister_agent(self, name: str) -> bool:
        """Unregister a named agent."""
        return self.registry.pop(name, None) is not None

    def list_agents(self) -> list[dict[str, Any]]:
        """Return registered agents."""
        return [dict(item) for item in self.registry.values()]

    def start_agent(self, name: str) -> dict[str, Any]:
        """Start a registered agent."""
        agent = self.registry.setdefault(name, {"name": name, "config": {}, "inbox": []})
        agent["state"] = "running"
        agent["node_id"] = self.cluster_manager.get_best_node() if self.cluster_manager else None
        self._replicate(name)
        self._publish("agent.started", {"name": name, "node_id": agent["node_id"]})
        return dict(agent)

    def stop_agent(self, name: str) -> dict[str, Any]:
        """Stop a registered agent."""
        self.registry[name]["state"] = "stopped"
        self._replicate(name)
        self._publish("agent.stopped", {"name": name})
        return dict(self.registry[name])

    def restart_agent(self, name: str) -> dict[str, Any]:
        """Restart a registered agent."""
        self._publish("agent.crashed", {"name": name})
        return self.start_agent(name)

    def route_message(self, agent_id: str, content: Any, sender: str = "system", correlation_id: str | None = None) -> dict[str, Any]:
        """Route a message to a registered agent inbox."""
        agent = self.registry[agent_id]
        message = {"agent_id": agent_id, "from": sender, "to": agent_id, "content": content, "correlation_id": correlation_id}
        agent.setdefault("inbox", []).append(message)
        self._replicate(agent_id)
        self._publish("agent.message.sent", message)
        self._publish("agent.message.received", message)
        return message

    def agent_write_memory(self, agent_id: str, key: str, value: Any) -> None:
        """Let an agent write short-term memory."""
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"agent:{agent_id}:{key}", value)

    def agent_write_file(self, agent_id: str, path: str, content: str) -> None:
        """Let an agent write through fs_sync."""
        if self.fs_sync and hasattr(self.fs_sync, "write_file"):
            self.fs_sync.write_file(path, content)

    def submit_agent_task(self, agent_id: str, task: Mapping[str, Any]) -> Any:
        """Let an agent submit a task."""
        if self.task_manager and hasattr(self.task_manager, "submit"):
            return self.task_manager.submit({"agent_id": agent_id, **dict(task)})
        return None

    def _replicate(self, name: str) -> None:
        """Replicate agent state when memory is configured."""
        if self.distributed_memory and hasattr(self.distributed_memory, "write"):
            self.distributed_memory.write(f"agent:{name}", dict(self.registry[name]))

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an agent event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)


__all__ = ["AgentManager", "AgentRecord"]

