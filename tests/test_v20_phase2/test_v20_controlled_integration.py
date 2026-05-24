# PATCH_START v20_phase2
"""Tests for controlled manual integration of ANA MAX v20 foundation tools."""

from __future__ import annotations

import builtins
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


V20_TOOL_NAMES = {
    "ana_health_check",
    "baseline_update_suggester",
    "docs_generator",
    "ana_patch_suggester",
    "runtime_guard",
}

V20_MODULE_NAMES = {
    "tools.v20.ana_health_check",
    "tools.v20.baseline_update_suggester",
    "tools.v20.docs_generator",
    "tools.v20.ana_patch_suggester",
    "tools.v20.runtime_guard",
}


class TestV20ControlledIntegration(unittest.TestCase):
    def setUp(self):
        from tools.base import registry

        registry.reset()

    def tearDown(self):
        from tools.base import registry

        registry.reset()

    def test_v20_tools_are_registered_and_listed(self):
        from main import _register_all_tools
        from tools.base import registry

        loaded = _register_all_tools()
        names = set(registry.list_tools())

        self.assertGreaterEqual(loaded, 80)
        self.assertTrue(V20_TOOL_NAMES.issubset(names))

    def test_v20_registration_does_not_auto_import_or_run_modules(self):
        from main import _register_all_tools

        for module_name in V20_MODULE_NAMES:
            sys.modules.pop(module_name, None)

        imported_v20_modules = []
        original_import = builtins.__import__

        def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in V20_MODULE_NAMES:
                imported_v20_modules.append(name)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=tracking_import):
            _register_all_tools()

        self.assertEqual(imported_v20_modules, [])

    def test_v20_tools_can_be_invoked_manually(self):
        from main import _register_all_tools
        from tools.base import registry

        _register_all_tools()
        calls = {
            "ana_health_check": {"include_contracts": False},
            "baseline_update_suggester": {"current": {"tool_count": 80}},
            "docs_generator": {"document": "SUMMARY.md"},
            "ana_patch_suggester": {
                "issue": {
                    "title": "manual smoke issue",
                    "file": "README.md",
                    "old": "old",
                    "new": "new",
                }
            },
            "runtime_guard": {"expected_root": str(PROJECT_ROOT)},
        }

        for tool_name, params in calls.items():
            with self.subTest(tool_name=tool_name):
                result = registry.execute(tool_name, **params)
                self.assertTrue(result.is_success, result.error)
                self.assertIsInstance(result.data, dict)
                self.assertTrue(result.data.get("success"))

    def test_v20_tool_definitions_are_manual_and_non_dangerous(self):
        from main import _register_all_tools
        from tools.base import registry

        _register_all_tools()

        for tool_name in V20_TOOL_NAMES:
            with self.subTest(tool_name=tool_name):
                tool = registry.get(tool_name)
                self.assertIsNotNone(tool)
                definition = tool.get_definition()
                self.assertEqual(definition.category, "diagnostics")
                self.assertFalse(definition.requires_confirmation)
                self.assertFalse(definition.dangerous)


if __name__ == "__main__":
    unittest.main()

# PATCH_END v20_phase2
