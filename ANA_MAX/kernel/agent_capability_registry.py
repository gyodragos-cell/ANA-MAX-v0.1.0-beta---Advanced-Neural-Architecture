"""OS-21 agent capability registry.

This module is metadata-only. It registers agent roles, capability contracts,
tool references, and sandbox policy without executing any agent or tool work.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents.browser_recon_agent import BrowserReconAgent
from ANA_MAX.agents.web_recon_agent import WebReconAgent
from ANA_MAX.agents.web_scraper_agent import WebScraperAgent


REGISTRY_SCHEMA = "ana.os21.agent_capability_registry.v1"
REGISTRY_NAME = "agent_capability_registry_v1"
REGISTRY_VERSION = "1.0"


def _normalize_agent_id(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith("agent:"):
        return normalized.split(":", 1)[1]
    return normalized


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _capability_id(tool: str, group: str) -> str:
    return f"{tool}.{group}"


def _capability_record(
    *,
    capability_id: str,
    tool: str,
    group: str,
    operations: list[str],
    risk: str,
    execution_allowed: bool = False,
    requires_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "tool": tool,
        "group": group,
        "operations": sorted(set(operations)),
        "risk": risk,
        "execution_allowed": bool(execution_allowed),
        "requires_confirmation": bool(requires_confirmation),
        "metadata_only": True,
    }


class AgentCapabilityRegistry:
    """Build and query agent capability registration metadata."""

    def __init__(self) -> None:
        self._last_registry: dict[str, Any] | None = None

    def _default_plans(self) -> list[dict[str, Any]]:
        return [
            BrowserReconAgent().build_plan(target="https://example.com", mode="passive"),
            WebScraperAgent().build_plan(targets=["https://example.com"], mode="passive"),
            WebReconAgent().build_plan(target="https://example.com", mode="passive"),
        ]

    def _capabilities_from_contracts(self, contracts: Mapping[str, Any]) -> list[dict[str, Any]]:
        capabilities: list[dict[str, Any]] = []
        for tool_name in sorted(contracts):
            contract = contracts.get(tool_name)
            if not isinstance(contract, Mapping):
                continue
            for key in sorted(contract):
                if key in {"execution_allowed", "metadata_only", "local_only"}:
                    continue
                operations = _normalize_list(contract.get(key))
                if not operations:
                    continue
                group = str(key).replace("_operations", "").replace("operations", "ops").strip("_")
                if group == "read_only":
                    risk = "low"
                    requires_confirmation = False
                elif "confirm" in group or "network" in group:
                    risk = "medium"
                    requires_confirmation = True
                else:
                    risk = "low"
                    requires_confirmation = False
                capabilities.append(
                    _capability_record(
                        capability_id=_capability_id(tool_name, group),
                        tool=tool_name,
                        group=group,
                        operations=operations,
                        risk=risk,
                        execution_allowed=False,
                        requires_confirmation=requires_confirmation,
                    )
                )
        return capabilities

    def _flatten_contracts(self, contracts: Mapping[str, Any]) -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key in sorted(contracts):
            value = contracts.get(key)
            if not isinstance(value, Mapping):
                continue
            if all(isinstance(nested, Mapping) for nested in value.values()):
                for nested_key in sorted(value):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, Mapping):
                        flattened[str(nested_key)] = dict(nested_value)
            else:
                flattened[str(key)] = dict(value)
        return flattened

    def _tools_from_plan(self, plan: Mapping[str, Any], capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tools: dict[str, dict[str, Any]] = {}
        for item in plan.get("required_tools") or []:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            tools[name] = {
                "tool": name,
                "purpose": str(item.get("purpose", "")),
                "load_policy": str(item.get("load_policy", "metadata_only")),
                "execution_allowed": bool(item.get("execution_allowed", False)),
            }
        for capability in capabilities:
            tool = str(capability.get("tool", ""))
            if tool and tool not in tools:
                tools[tool] = {
                    "tool": tool,
                    "purpose": "capability_contract",
                    "load_policy": "metadata_only",
                    "execution_allowed": False,
                }
        return [tools[key] for key in sorted(tools)]

    def _agent_record_from_plan(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        agent_id = _normalize_agent_id(str(plan.get("agent_name", "")))
        role = str(plan.get("agent_role", agent_id)).strip() or agent_id
        raw_contracts = plan.get("capability_contracts") or {}
        contracts = self._flatten_contracts(raw_contracts if isinstance(raw_contracts, Mapping) else {})
        capabilities = self._capabilities_from_contracts(contracts)
        tools = self._tools_from_plan(plan, capabilities)
        requires_confirmation = bool(plan.get("risk_profile", {}).get("requires_confirmation", False))
        requires_confirmation = requires_confirmation or any(item.get("requires_confirmation") for item in capabilities)
        graph_hints = plan.get("reasoning_graph_hints") or {}

        return {
            "agent_id": agent_id,
            "node_id": f"agent:{agent_id}",
            "role": role,
            "schema": str(plan.get("schema", "")),
            "metadata_only": bool(plan.get("metadata_only", plan.get("local_only", True))),
            "local_only": bool(plan.get("local_only", True)),
            "no_execution": bool(plan.get("no_execution", True)),
            "requires_confirmation": requires_confirmation,
            "capabilities": sorted(capabilities, key=lambda item: item["capability_id"]),
            "tools": tools,
            "sandbox_policy": {
                "execution_allowed": False,
                "metadata_only": True,
                "local_only": True,
                "requires_confirmation": requires_confirmation,
            },
            "reasoning_graph_hints": {
                "nodes": sorted(set(_normalize_list(graph_hints.get("nodes")))),
                "edges": [dict(edge) for edge in graph_hints.get("edges") or [] if isinstance(edge, Mapping)],
            },
        }

    def build_registry(self, plans: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        source_plans = list(plans) if plans is not None else self._default_plans()
        agent_records = [self._agent_record_from_plan(plan) for plan in source_plans if isinstance(plan, Mapping)]
        agent_records = [agent for agent in agent_records if agent.get("agent_id")]
        agent_records = sorted(agent_records, key=lambda item: item["agent_id"])
        agent_index = {agent["agent_id"]: agent for agent in agent_records}

        capability_index: dict[str, list[str]] = {}
        tool_index: dict[str, list[str]] = {}
        for agent in agent_records:
            agent_id = agent["agent_id"]
            for capability in agent.get("capabilities") or []:
                capability_id = str(capability.get("capability_id", ""))
                if capability_id:
                    capability_index.setdefault(capability_id, []).append(agent_id)
            for tool in agent.get("tools") or []:
                tool_name = str(tool.get("tool", ""))
                if tool_name:
                    tool_index.setdefault(tool_name, []).append(agent_id)

        capability_index = {key: sorted(set(value)) for key, value in sorted(capability_index.items())}
        tool_index = {key: sorted(set(value)) for key, value in sorted(tool_index.items())}
        registry = {
            "schema": REGISTRY_SCHEMA,
            "registry_name": REGISTRY_NAME,
            "version": REGISTRY_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "baseline_compatible": True,
            "sandbox_policy": {
                "execution_allowed": False,
                "metadata_only": True,
                "local_only": True,
                "default_mode": "planning_only",
            },
            "agents": agent_records,
            "agent_index": agent_index,
            "capability_index": capability_index,
            "tool_index": tool_index,
            "reasoning_graph_hints": {
                "nodes": [agent["node_id"] for agent in agent_records],
                "edges": [
                    {
                        "source": agent["node_id"],
                        "target": f"tool:{tool['tool']}",
                        "relation": "declares_capability",
                    }
                    for agent in agent_records
                    for tool in agent.get("tools") or []
                ],
            },
            "summary": {
                "schema": REGISTRY_SCHEMA,
                "registry_name": REGISTRY_NAME,
                "agent_count": len(agent_records),
                "capability_count": sum(len(agent.get("capabilities") or []) for agent in agent_records),
                "tool_count": len(tool_index),
                "requires_confirmation_count": len([agent for agent in agent_records if agent.get("requires_confirmation")]),
                "metadata_only": True,
            },
        }
        self._last_registry = registry
        return registry

    def _registry(self) -> dict[str, Any]:
        return self._last_registry or self.build_registry()

    def find_agents_by_capability(self, capability_id: str) -> dict[str, Any]:
        registry = self._registry()
        normalized = str(capability_id or "").strip()
        agent_ids = registry.get("capability_index", {}).get(normalized, [])
        results = [registry["agent_index"][agent_id] for agent_id in agent_ids if agent_id in registry.get("agent_index", {})]
        return {
            "schema": REGISTRY_SCHEMA,
            "metadata_only": True,
            "local_only": True,
            "query": {
                "type": "find_agents_by_capability",
                "capability_id": normalized,
            },
            "count": len(results),
            "results": sorted(results, key=lambda item: item["agent_id"]),
        }

    def find_tools_for_agent(self, agent_id: str) -> dict[str, Any]:
        registry = self._registry()
        normalized = _normalize_agent_id(agent_id)
        agent = registry.get("agent_index", {}).get(normalized, {})
        results = sorted([dict(item) for item in agent.get("tools") or []], key=lambda item: item["tool"])
        return {
            "schema": REGISTRY_SCHEMA,
            "metadata_only": True,
            "local_only": True,
            "query": {
                "type": "find_tools_for_agent",
                "agent_id": normalized,
            },
            "count": len(results),
            "results": results,
        }

    def validate_registry(self, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(registry or self._registry())
        issues: list[str] = []
        if payload.get("schema") != REGISTRY_SCHEMA:
            issues.append("schema_mismatch")
        if not payload.get("metadata_only"):
            issues.append("metadata_only_false")
        if payload.get("sandbox_policy", {}).get("execution_allowed") is not False:
            issues.append("execution_allowed_not_false")
        if not payload.get("agents"):
            issues.append("missing_agents")
        for agent in payload.get("agents") or []:
            if not isinstance(agent, Mapping):
                issues.append("agent_not_mapping")
                continue
            if not agent.get("agent_id"):
                issues.append("missing_agent_id")
            if agent.get("sandbox_policy", {}).get("execution_allowed") is not False:
                issues.append(f"agent_execution_allowed:{agent.get('agent_id', '')}")
        return {
            "schema": REGISTRY_SCHEMA,
            "registry_name": REGISTRY_NAME,
            "success": not issues,
            "issues": issues,
            "agent_count": len(payload.get("agents") or []),
            "capability_count": payload.get("summary", {}).get("capability_count", 0),
        }

    def summarize_registry(self) -> dict[str, Any]:
        registry = self._registry()
        summary = dict(registry.get("summary") or {})
        summary["metadata_only"] = True
        summary["local_only"] = True
        return summary


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "registry"))
    registry = AgentCapabilityRegistry()
    payload = registry.build_registry()

    if action == "summary":
        return {"success": True, "result": registry.summarize_registry()}
    if action == "validate":
        result = registry.validate_registry(payload)
        return {"success": result["success"], "result": result}
    if action == "capability":
        return {"success": True, "result": registry.find_agents_by_capability(str(args.get("capability_id", "")))}
    if action == "tools":
        return {"success": True, "result": registry.find_tools_for_agent(str(args.get("agent_id", "")))}
    if action in {"registry", "cycle"}:
        return {"success": True, "result": payload}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build OS-21 agent capability registry metadata.")
    parser.add_argument("--summary", action="store_true", help="Print compact registry summary")
    parser.add_argument("--validate", action="store_true", help="Validate registry metadata")
    parser.add_argument("--capability", default="", help="Find agents by capability ID")
    parser.add_argument("--agent", default="", help="Find tool refs for an agent ID")
    parser.add_argument("--cycle", action="store_true", help="Print the full registry")
    args = parser.parse_args(argv)

    action = "registry"
    extra: dict[str, Any] = {}
    if args.summary:
        action = "summary"
    elif args.validate:
        action = "validate"
    elif args.capability:
        action = "capability"
        extra["capability_id"] = args.capability
    elif args.agent:
        action = "tools"
        extra["agent_id"] = args.agent
    elif args.cycle:
        action = "cycle"

    output = run({"action": action, **extra})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
