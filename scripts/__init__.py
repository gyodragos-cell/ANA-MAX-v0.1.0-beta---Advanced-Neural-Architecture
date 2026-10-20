"""Operational OS28 catalog snapshot/import scripts for OS29."""

--- C:\Users\billy\Desktop\OS29_LAB\scripts\import_os28_profile_catalogs.py contents: ---
[Reading 184 lines from start (total: 184 lines, 0 remaining)]

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from os29.store import Store


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(os.environ.get("OS29_DB_PATH", str(ROOT / "data" / "os29.db")))
DEFAULT_SNAPSHOT = ROOT / "artifacts" / "os28_profile_catalogs_snapshot.json"
OWNER = "OS28 profile catalog snapshot"
INSTANCE_OWNER = OWNER


def import_catalogs(store: Store, snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema_version") != "os29.os28_profile_catalogs.v1":
        raise ValueError("unsupported profile catalog schema")
    catalogs = snapshot.get("catalogs")
    if not isinstance(catalogs, list) or not catalogs:
        raise ValueError("profile catalog list is empty")

    nodes = store.list_capabilities(limit=2000)
    service_by_name = {
        node["name"]: node for node in nodes if node["kind"] == "service"
    }
    canonical_by_name = {
        node["name"]: node for node in nodes if node["kind"] == "catalog_tool"
    }
    canonical_by_name.update({
        node["name"]: node for node in nodes if node["kind"] == "tool"
    })
    prior_instances = {
        node["name"]: node for node in nodes
        if node["kind"] == "tool_instance" and node.get("owner") == INSTANCE_OWNER
    }

    current_instance_names: set[str] = set()
    profile_count = 0
    instance_count = 0
    canonical_fallback_count = 0
    for catalog in catalogs:
        profile_name = str(catalog.get("profile", "")).strip()
        service_name = str(catalog.get("service_name", "")).strip()
        tool_items = catalog.get("tools")
        if not profile_name or not service_name or not isinstance(tool_items, list):
            raise ValueError("catalog profile/service/tools fields are invalid")
        service = service_by_name.get(service_name)
        if service is None:
            raise ValueError(f"run runtime snapshot first; service node is missing: {service_name}")
        tool_names = [item.get("name") for item in tool_items if isinstance(item, dict)]
        if len(tool_names) != len(tool_items) or len(tool_names) != len(set(tool_names)):
            raise ValueError(f"catalog has invalid or duplicate tools: {profile_name}")

        profile = store.upsert_capability(
            kind="profile",
            name=profile_name,
            status="configured",
            evidence={
                "source": "authenticated live MCP tools/list",
                "endpoint": catalog.get("endpoint"),
                "captured_at": snapshot.get("captured_at"),
                "advertised_tool_count": len(tool_items),
            },
            owner=OWNER,
        )
        profile_count += 1
        store.upsert_capability_edge(
            source_node_id=profile["node_id"],
            target_node_id=service["node_id"],
            relation="served_by",
            evidence={
                "endpoint": catalog.get("endpoint"),
                "catalog_captured_at": snapshot.get("captured_at"),
            },
        )

        for item in tool_items:
            tool_name = str(item["name"])
            instance_name = f"{profile_name}::{tool_name}"
            current_instance_names.add(instance_name)
            evidence = {
                "source": "live MCP tools/list",
                "profile": profile_name,
                "endpoint": catalog.get("endpoint"),
                "catalog_captured_at": snapshot.get("captured_at"),
                "tool_name": tool_name,
                "description": item.get("description", ""),
                "category": item.get("category", "unknown"),
                "input_parameters": item.get("input_parameters", []),
                "input_parameter_count": item.get("input_parameter_count", 0),
                "allowed_operation_enum": item.get("allowed_operation_enum", []),
                "input_schema_sha256": item.get("input_schema_sha256"),
            }
            instance = store.upsert_capability(
                kind="tool_instance",
                name=instance_name,
                status="configured",
                evidence=evidence,
                owner=INSTANCE_OWNER,
            )
            instance_count += 1
            store.upsert_capability_edge(
                source_node_id=instance["node_id"],
                target_node_id=service["node_id"],
                relation="exposed_by",
                evidence={"profile": profile_name, "endpoint": catalog.get("endpoint")},
            )
            store.upsert_capability_edge(
                source_node_id=instance["node_id"],
                target_node_id=profile["node_id"],
                relation="visible_in",
                evidence={"profile": profile_name, "catalog_captured_at": snapshot.get("captured_at")},
            )

            canonical = canonical_by_name.get(tool_name)
            if canonical is None:
                canonical = store.upsert_capability(
                    kind="catalog_tool",
                    name=tool_name,
                    status="configured",
                    evidence={
                        "source": "profile MCP catalog",
                        "first_seen_in_profile": profile_name,
                        "description": item.get("description", ""),
                        "input_schema_sha256": item.get("input_schema_sha256"),
                    },
                    owner=OWNER,
                )
                canonical_by_name[tool_name] = canonical
                canonical_fallback_count += 1
            store.upsert_capability_edge(
                source_node_id=instance["node_id"],
                target_node_id=canonical["node_id"],
                relation="implements",
                evidence={
                    "profile": profile_name,
                    "input_schema_sha256": item.get("input_schema_sha256"),
                },
            )

    stale = 0
    for instance_name, old in prior_instances.items():
        if instance_name not in current_instance_names:
            store.upsert_capability(
                kind="tool_instance",
                name=instance_name,
                status="unknown",
                evidence={
                    "source": "OS28 profile catalog comparison",
                    "last_seen": old.get("observed_at"),
                    "missing_from_snapshot_at": snapshot.get("captured_at"),
                    "note": "Not deleted; marked unknown after a single absent snapshot.",
                },
                owner=INSTANCE_OWNER,
            )
            stale += 1

    return {
        "result": "OS28_PROFILE_GRAPH_IMPORT_PASS",
        "profile_count": profile_count,
        "tool_instances_upserted": instance_count,
        "canonical_profile_only_tools_created": canonical_fallback_count,
        "stale_instances_marked_unknown": stale,
        "store": store.stats(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import sanitized per-profile OS28 tool catalogs into OS29's capability graph.")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = import_catalogs(Store(args.db), snapshot)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())