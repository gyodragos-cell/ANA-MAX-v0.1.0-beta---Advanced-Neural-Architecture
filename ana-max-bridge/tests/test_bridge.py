import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("bridge_server", ROOT / "bridge_server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class TestBridgeServer(unittest.TestCase):
    def setUp(self):
        self.bridge = load_bridge_module()
        self.config = {
            "local_dev": True,
            "bridge": {"auto_start": True, "max_logs": 25},
            "ana_max": {"base_url": "http://127.0.0.1:8765", "timeout_seconds": 1},
            "watchdog": {"blocked_tools": [], "max_payload_bytes": 200000},
        }
        self.seen_headers = []

    def fake_request(self, method, url, **kwargs):
        self.seen_headers.append(kwargs.get("headers", {}))
        if url.endswith("/tools"):
            return FakeResponse(
                {
                    "tools": [
                        {
                            "name": "workspace_situational_awareness",
                            "description": "Workspace snapshot",
                            "category": "core",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    ],
                    "count": 1,
                }
            )
        if url.endswith("/health"):
            return FakeResponse({"status": "online", "tools_count": 1})
        if url.endswith("/execute"):
            return FakeResponse({"success": True, "data": {"ok": True}, "message": "done"})
        return FakeResponse({"error": "not found"}, 404)

    def test_health_and_tool_list(self):
        with patch.object(self.bridge.requests, "request", side_effect=self.fake_request):
            app = self.bridge.create_app(self.config)
            client = app.test_client()

            health = client.get("/health")
            tools = client.get("/tools/list")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(tools.status_code, 200)
        self.assertEqual(tools.get_json()["count"], 1)

    def test_execute_forwards_to_ana(self):
        with patch.object(self.bridge.requests, "request", side_effect=self.fake_request):
            app = self.bridge.create_app(self.config)
            client = app.test_client()
            response = client.post(
                "/tools/call",
                json={"tool": "workspace_situational_awareness", "params": {"path": "."}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

    def test_local_dev_does_not_send_auth_header(self):
        with patch.object(self.bridge.requests, "request", side_effect=self.fake_request):
            app = self.bridge.create_app(self.config)
            client = app.test_client()
            client.get("/tools/list")

        self.assertTrue(self.seen_headers)
        self.assertTrue(all("Authorization" not in headers for headers in self.seen_headers))

    def test_local_dev_rejects_non_localhost_requests(self):
        with patch.object(self.bridge.requests, "request", side_effect=self.fake_request):
            app = self.bridge.create_app(self.config)
            client = app.test_client()
            response = client.get("/health", environ_base={"REMOTE_ADDR": "192.168.1.10"})

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
