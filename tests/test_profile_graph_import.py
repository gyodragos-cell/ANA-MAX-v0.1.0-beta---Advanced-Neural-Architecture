from __future__ import annotations

from os29.store import Store
from scripts.import_os28_profile_catalogs import import_catalogs


def test_profile_catalog_import_creates_idempotent_profile_tool_service_graph(tmp_path):
    store = Store(tmp_path / "catalog-import.db")
    gateway = store.upsert_capability(
        kind="service", name="operator_gateway", status="running", evidence={"port": 8772}
    )
    ana = store.upsert_capability(
        kind="tool", name="code_search", status="configured", evidence={"source": "main catalog"}
    )

    snapshot = {
        "schema_version": "os29.os28_profile_catalogs.v1",
        "captured_at": "2026-10-19T00:00:00Z",
        "catalogs": [{
            "profile": "operator-dev",
            "service_name": "operator_gateway",
            "endpoint": "http://127.0.0.1:8772/mcp",
            "tool_count": 2,
            "unique_tool_count": 2,
            "tools": [
                {
                    "name": "code_search",
                    "description": "Search source files.",
                    "category": "code",
                    "input_parameters": ["operation", "path", "pattern"],
                    "input_parameter_count": 3,
                    "allowed_operation_enum": ["grep", "search_symbol"],
                    "input_schema_sha256": "schema-hash-1",
                },
                {
                    "name": "custom_gateway_tool",
                    "description": "Profile-specific test tool.",
                    "category": "gateway",
                    "input_parameters": ["action"],
                    "input_parameter_count": 1,
                    "allowed_operation_enum": [],
                    "input_schema_sha256": "schema-hash-2",
                },
            ],
        }],
    }

    first = import_catalogs(store, snapshot)
    before = store.stats()
    second = import_catalogs(store, snapshot)
    after = store.stats()

    assert first["tool_instances_upserted"] == 2
    assert second["tool_instances_upserted"] == 2
    assert after["capability_nodes"] == before["capability_nodes"]
    assert after["capability_edges"] == before["capability_edges"]

    nodes = store.list_capabilities(limit=100)
    instance = next(n for n in nodes if n["kind"] == "tool_instance" and n["name"] == "operator-dev::code_search")
    custom = next(n for n in nodes if n["kind"] == "catalog_tool" and n["name"] == "custom_gateway_tool")
    edges = store.list_capability_edges(limit=100)
    instance_edges = [e for e in edges if e["source_node_id"] == instance["node_id"]]
    assert {e["relation"] for e in instance_edges} == {"exposed_by", "visible_in", "implements"}
    assert custom["status"] == "configured"
    assert any(e["target_node_id"] == gateway["node_id"] and e["relation"] == "exposed_by" for e in instance_edges)
    assert any(e["target_node_id"] == ana["node_id"] and e["relation"] == "implements" for e in instance_edges)