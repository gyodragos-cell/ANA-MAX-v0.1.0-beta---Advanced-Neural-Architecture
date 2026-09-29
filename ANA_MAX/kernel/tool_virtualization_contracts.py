"""OS-21 tool virtualization contracts.

This module turns registered agent capabilities into sandboxed tool contracts.
It is metadata-only and never executes tools, network requests, or transports.
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

from ANA_MAX.kernel.agent_capability_registry import AgentCapabilityRegistry


CONTRACT_SCHEMA = "ana.os21.tool_virtualization_contracts.v1"
SIMULATION_SCHEMA = "ana.os21.tool_simulation.v1"
FALLBACK_SCHEMA = "ana.os21.tool_fallback_plan.v1"
ENGINE_NAME = "tool_virtualization_contracts_v1"
ENGINE_VERSION = "1.0"


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _payload_keys(payload: Any) -> list[str]:
    if isinstance(payload, Mapping):
        return sorted(str(key) for key in payload)
    if payload is None:
        return []
    return ["value"]


class ToolVirtualizationContracts:
    """Build and query sandboxed metadata contracts for registered tools."""

    def __init__(self, registry_builder: AgentCapabilityRegistry | None = None) -> None:
        self.registry_builder = registry_builder or AgentCapabilityRegistry()
        self._last_contracts: dict[str, Any] | None = None

    def _registry(self, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if registry is not None:
            return dict(registry)
        return self.registry_builder.build_registry()

    def _operation_records(self, tool_name: str, registry: Mapping[str, Any]) -> list[dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for agent in registry.get("agents") or []:
            if not isinstance(agent, Mapping):
                continue
            agent_id = str(agent.get("agent_id", ""))
            for capability in agent.get("capabilities") or []:
                if not isinstance(capability, Mapping):
                    continue
                if str(capability.get("tool", "")) != tool_name:
                    continue
                for operation in capability.get("operations") or []:
                    operation_name = str(operation)
                    operation_id = f"{tool_name}.{operation_name}"
                    record = records.setdefault(
                        operation_id,
                        {
                            "operation_id": operation_id,
                            "tool": tool_name,
                            "operation": operation_name,
                            "groups": [],
                            "agent_ids": [],
                            "risk": str(capability.get("risk", "low")),
                            "requires_confirmation": bool(capability.get("requires_confirmation", False)),
                            "execution_allowed": False,
                            "simulation_available": True,
                            "metadata_only": True,
                        },
                    )
                    group = str(capability.get("group", "unknown"))
                    if group not in record["groups"]:
                        record["groups"].append(group)
                    if agent_id and agent_id not in record["agent_ids"]:
                        record["agent_ids"].append(agent_id)
                    if capability.get("requires_confirmation"):
                        record["requires_confirmation"] = True
                    if str(capability.get("risk", "low")) == "medium":
                        record["risk"] = "medium"

        for record in records.values():
            record["groups"] = sorted(record["groups"])
            record["agent_ids"] = sorted(record["agent_ids"])
        return [records[key] for key in sorted(records)]

    def build_contracts(self, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
        registry_payload = self._registry(registry)
        tool_names = sorted(str(tool) for tool in registry_payload.get("tool_index", {}) if str(tool))
        tools: list[dict[str, Any]] = []
        operation_contracts: list[dict[str, Any]] = []

        for tool_name in tool_names:
            operations = self._operation_records(tool_name, registry_payload)
            operation_contracts.extend(operations)
            tools.append(
                {
                    "tool": tool_name,
                    "metadata_only": True,
                    "local_only": True,
                    "sandbox": {
                        "execution_allowed": False,
                        "simulation_allowed": True,
                        "filesystem_write_allowed": False,
                        "network_allowed": False,
                        "requires_confirmation": any(item["requires_confirmation"] for item in operations),
                    },
                    "operation_count": len(operations),
                    "operations": operations,
                    "agent_ids": sorted(registry_payload.get("tool_index", {}).get(tool_name, [])),
                }
            )

        contracts = {
            "schema": CONTRACT_SCHEMA,
            "engine_name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "no_execution": True,
            "baseline_compatible": True,
            "registry_ref": {
                "schema": registry_payload.get("schema", ""),
                "registry_name": registry_payload.get("registry_name", ""),
                "agent_count": registry_payload.get("summary", {}).get("agent_count", 0),
            },
            "sandbox_policy": {
                "default_execution_allowed": False,
                "default_simulation_allowed": True,
                "network_allowed": False,
                "filesystem_write_allowed": False,
                "requires_explicit_execution_layer": True,
            },
            "tools": tools,
            "operation_contracts": operation_contracts,
            "tool_index": {tool["tool"]: tool for tool in tools},
            "operation_index": {item["operation_id"]: item for item in operation_contracts},
            "fallback_policy": {
                "default_steps": [
                    "return_contract_metadata",
                    "return_simulation_result",
                    "request_explicit_execution_layer",
                ],
                "execution_allowed": False,
            },
            "summary": {
                "schema": CONTRACT_SCHEMA,
                "engine_name": ENGINE_NAME,
                "tool_count": len(tools),
                "operation_contract_count": len(operation_contracts),
                "metadata_only": True,
                "execution_allowed": False,
            },
        }
        self._last_contracts = contracts
        return contracts

    def _contracts(self) -> dict[str, Any]:
        return self._last_contracts or self.build_contracts()

    def find_contract(self, tool: str) -> dict[str, Any]:
        contracts = self._contracts()
        normalized = str(tool or "").strip()
        result = contracts.get("tool_index", {}).get(normalized)
        results = [result] if result else []
        return {
            "schema": CONTRACT_SCHEMA,
            "metadata_only": True,
            "local_only": True,
            "query": {
                "type": "find_contract",
                "tool": normalized,
            },
            "count": len(results),
            "results": results,
        }

    def simulate_operation(self, *, tool: str, operation: str, payload: Any = None) -> dict[str, Any]:
        contracts = self._contracts()
        normalized_tool = str(tool or "").strip()
        normalized_operation = str(operation or "").strip()
        operation_id = f"{normalized_tool}.{normalized_operation}" if normalized_tool and normalized_operation else ""
        contract = _as_mapping(contracts.get("operation_index", {}).get(operation_id))
        allowed = bool(contract)
        status = "simulated_contract_match" if allowed else "blocked_unknown_operation"
        return {
            "schema": SIMULATION_SCHEMA,
            "engine_name": ENGINE_NAME,
            "metadata_only": True,
            "local_only": True,
            "executed": False,
            "allowed_by_contract": allowed,
            "tool": normalized_tool,
            "operation": normalized_operation,
            "simulation": {
                "status": status,
                "tool": normalized_tool,
                "operation": normalized_operation,
                "payload_keys": _payload_keys(payload),
                "requires_confirmation": bool(contract.get("requires_confirmation", False)),
                "execution_allowed": False,
            },
            "contract": contract,
        }

    def build_fallback_plan(self, tool: str) -> dict[str, Any]:
        contracts = self._contracts()
        normalized = str(tool or "").strip()
        contract = contracts.get("tool_index", {}).get(normalized, {})
        return {
            "schema": FALLBACK_SCHEMA,
            "engine_name": ENGINE_NAME,
            "metadata_only": True,
            "local_only": True,
            "tool": normalized,
            "contract_found": bool(contract),
            "execution_allowed": False,
            "fallback_steps": list(contracts.get("fallback_policy", {}).get("default_steps") or []),
            "contract_summary": {
                "operation_count": contract.get("operation_count", 0) if isinstance(contract, Mapping) else 0,
                "agent_ids": list(contract.get("agent_ids", [])) if isinstance(contract, Mapping) else [],
            },
        }

    def summarize_contracts(self) -> dict[str, Any]:
        contracts = self._contracts()
        return dict(contracts.get("summary") or {})


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "contracts"))
    engine = ToolVirtualizationContracts()
    contracts = engine.build_contracts()

    if action == "summary":
        return {"success": True, "result": engine.summarize_contracts()}
    if action == "contract":
        return {"success": True, "result": engine.find_contract(str(args.get("tool", "")))}
    if action == "simulate":
        return {
            "success": True,
            "result": engine.simulate_operation(
                tool=str(args.get("tool", "")),
                operation=str(args.get("operation", "")),
                payload=args.get("payload"),
            ),
        }
    if action == "fallback":
        return {"success": True, "result": engine.build_fallback_plan(str(args.get("tool", "")))}
    if action in {"contracts", "cycle"}:
        return {"success": True, "result": contracts}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build OS-21 tool virtualization contracts.")
    parser.add_argument("--summary", action="store_true", help="Print compact summary")
    parser.add_argument("--tool", default="", help="Tool name for contract, simulation, or fallback")
    parser.add_argument("--operation", default="", help="Operation name for simulation")
    parser.add_argument("--simulate", action="store_true", help="Simulate a tool operation")
    parser.add_argument("--fallback", action="store_true", help="Build fallback metadata for a tool")
    parser.add_argument("--cycle", action="store_true", help="Print the full contracts payload")
    args = parser.parse_args(argv)

    action = "contracts"
    extra: dict[str, Any] = {}
    if args.summary:
        action = "summary"
    elif args.simulate:
        action = "simulate"
        extra["tool"] = args.tool
        extra["operation"] = args.operation
    elif args.fallback:
        action = "fallback"
        extra["tool"] = args.tool
    elif args.tool:
        action = "contract"
        extra["tool"] = args.tool
    elif args.cycle:
        action = "cycle"

    output = run({"action": action, **extra})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
