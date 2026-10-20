from __future__ import annotations

import json
from pathlib import Path

from os29.runtime_snapshot import snapshot_loopback
from os29.store import Store


class FakeResponse:
    status = 200

    def __init__(self, content: dict):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return json.dumps(self.content).encode("utf-8")


def test_snapshot_uses_only_fixed_loopback_urls_and_updates_capabilities(tmp_path: Path, monkeypatch):
    import os29.runtime_snapshot as module

    requested = []

    def fake_urlopen(request, timeout):
        requested.append(request.full_url)
        if ":11434/" in request.full_url:
            return FakeResponse({"models": []})
        return FakeResponse({"status": "online", "tools_count": 127, "mcp_ready": True})

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module, "_listener_map", lambda: {})
    store = Store(tmp_path / "snapshot.db")
    output = snapshot_loopback(store, timeout=0.1)
    assert output["status"] == "complete"
    assert len(requested) == 7
    assert all(url.startswith("http://127.0.0.1:") for url in requested)
    assert store.stats()["capability_nodes"] == 14
    assert store.stats()["capability_edges"] == 7
    edges = store.list_capability_edges()
    assert all(edge["relation"] == "probes_port" for edge in edges)
    assert any(x["snapshot"]["name"] == "ana_max_mcp" for x in output["services"])