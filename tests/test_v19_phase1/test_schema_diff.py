# PATCH_START v19_phase2
"""Tests for the read-only schema_diff diagnostic tool."""

from unittest import TestCase

from tools import schema_diff


class TestSchemaDiff(TestCase):
    def test_matching_schema_has_no_findings(self):
        result = schema_diff.run(
            {
                "expected_schema": {
                    "properties": {
                        "success": {"type": "boolean", "required": True},
                        "context": {"type": "object"},
                    }
                },
                "actual_response": {"success": True, "context": {}},
            }
        )

        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["extra"], [])
        self.assertEqual(result["type_mismatch"], [])

    def test_reports_missing_extra_and_type_mismatch(self):
        result = schema_diff.run(
            {
                "expected_schema": {
                    "properties": {
                        "success": {"type": "boolean", "required": True},
                        "context": {"type": "object", "required": True},
                    }
                },
                "actual_response": {"success": "yes", "extra": 1},
            }
        )

        self.assertTrue(result["success"])
        self.assertIn("context", result["missing"])
        self.assertIn("extra", result["extra"])
        self.assertEqual(result["type_mismatch"][0]["field"], "success")

    def test_invalid_inputs_return_safe_errors(self):
        result = schema_diff.run({"expected_schema": [], "actual_response": {}})
        self.assertFalse(result["success"])
        self.assertIn("error", result)

        result = schema_diff.run({"expected_schema": {}, "actual_response": []})
        self.assertFalse(result["success"])
        self.assertIn("error", result)


# PATCH_END v19_phase2
