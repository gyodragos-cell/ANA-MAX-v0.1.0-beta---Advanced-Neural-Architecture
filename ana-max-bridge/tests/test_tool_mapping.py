import unittest

from tool_mapper import ToolMapper
from watchdog import BridgeWatchdog


class TestToolMapping(unittest.TestCase):
    def test_maps_ana_tool_to_bridge_definition(self):
        mapper = ToolMapper()
        result = mapper.map_tool(
            {
                "name": "file_operations",
                "description": "File operations",
                "category": "core",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        )

        self.assertEqual(result["name"], "file_operations")
        self.assertEqual(result["endpoint"], "/tools/call")
        self.assertEqual(result["input_schema"]["type"], "object")

    def test_watchdog_blocks_destructive_pattern(self):
        watchdog = BridgeWatchdog({})
        verdict = watchdog.validate_call("terminal", {"command": "git reset --hard"})

        self.assertFalse(verdict.allowed)
        self.assertIn("blocked pattern", verdict.reason)

    def test_watchdog_suppresses_auth_warnings_in_local_dev(self):
        watchdog = BridgeWatchdog({"local_dev": True})

        self.assertFalse(watchdog.should_report_auth_warning())
        self.assertTrue(watchdog.snapshot()["suppress_auth_warnings"])


if __name__ == "__main__":
    unittest.main()
