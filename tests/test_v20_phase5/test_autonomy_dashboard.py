# PATCH_START v20_phase5
"""Tests for the read-only v20 autonomy dashboard."""

from __future__ import annotations

import builtins
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SAMPLE_OUTPUTS = {
    "ana_health_check": {"success": True, "status": "OK"},
    "baseline_update_suggester": {"success": True, "status": "OK"},
    "docs_generator": {"success": True, "document": "SUMMARY.md"},
    "ana_patch_suggester": {"success": True, "suggestions": []},
    "runtime_guard": {"success": True, "status": "OK"},
}


class TestAutonomyDashboard(unittest.TestCase):
    def setUp(self):
        from tools.base import registry

        registry.reset()

    def tearDown(self):
        from tools.base import registry

        registry.reset()

    def test_dashboard_renderer_loads_and_displays_sections(self):
        from dashboard.autonomy_dashboard import render_dashboard

        html = render_dashboard(SAMPLE_OUTPUTS)

        self.assertIn("ANA MAX v20 Autonomy Dashboard", html)
        self.assertIn("ANA Health Check", html)
        self.assertIn("Baseline Update Suggester", html)
        self.assertIn("Docs Generator", html)
        self.assertIn("ANA Patch Suggester", html)
        self.assertIn("Runtime Guard", html)

    def test_dashboard_run_accepts_precomputed_outputs_without_side_effects(self):
        from dashboard import autonomy_dashboard

        with patch.object(autonomy_dashboard, "_default_outputs") as default_outputs:
            result = autonomy_dashboard.run({"outputs": SAMPLE_OUTPUTS})

        default_outputs.assert_not_called()
        self.assertTrue(result["success"])
        self.assertFalse(result["written"])
        self.assertIn("<html", result["html"])

    def test_dashboard_registration_does_not_auto_import_renderer(self):
        from main import _register_all_tools

        sys.modules.pop("dashboard.autonomy_dashboard", None)
        imported = []
        original_import = builtins.__import__

        def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "dashboard.autonomy_dashboard":
                imported.append(name)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=tracking_import):
            _register_all_tools()

        self.assertEqual(imported, [])

    def test_dashboard_tool_invokes_manually(self):
        from main import _register_all_tools
        from tools.base import registry

        _register_all_tools()
        result = registry.execute("autonomy_dashboard", outputs=SAMPLE_OUTPUTS)

        self.assertTrue(result.is_success, result.error)
        self.assertEqual(result.data["format"], "html")
        self.assertFalse(result.data["written"])
        self.assertIn("runtime_guard", result.data["sections"])


if __name__ == "__main__":
    unittest.main()

# PATCH_END v20_phase5
