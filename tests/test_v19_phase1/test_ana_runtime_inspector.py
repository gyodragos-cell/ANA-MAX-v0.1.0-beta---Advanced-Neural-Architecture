# PATCH_START v19_phase2
"""Tests for the read-only ANA runtime inspector."""

from pathlib import Path
from unittest import TestCase

from tools import ana_runtime_inspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestAnaRuntimeInspector(TestCase):
    def test_snapshot_returns_runtime_contract(self):
        result = ana_runtime_inspector.run({"action": "snapshot"})

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("runtime", result)

        runtime = result["runtime"]
        self.assertIn("cwd", runtime)
        self.assertIn("bridge_pid", runtime)
        self.assertIn("ports", runtime)
        self.assertIn("loaded_modules", runtime)
        self.assertIn("file_hashes", runtime)
        self.assertIsInstance(runtime["ports"], dict)
        self.assertIsInstance(runtime["loaded_modules"], list)
        self.assertIsInstance(runtime["file_hashes"], dict)

    def test_compare_envs_same_path_has_no_diff(self):
        result = ana_runtime_inspector.run(
            {
                "action": "compare_envs",
                "dev_path": str(PROJECT_ROOT),
                "release_path": str(PROJECT_ROOT),
                "max_files": 50,
            }
        )

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertEqual(result["diff"]["modified"], [])
        self.assertEqual(result["diff"]["missing"], [])
        self.assertEqual(result["diff"]["extra"], [])

    def test_unknown_action_is_safe_error(self):
        result = ana_runtime_inspector.run({"action": "does_not_exist"})

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertFalse(result["success"])
        self.assertIn("error", result)


# PATCH_END v19_phase2
