# PATCH_START v19_phase2
"""Tests for the read-only tool contract validator."""

from unittest import TestCase
from unittest.mock import patch

from tools import tool_contract_validator


class TestToolContractValidator(TestCase):
    def test_validate_tool_schema_diff_passes(self):
        result = tool_contract_validator.run(
            {"action": "validate_tool", "tool_name": "schema_diff"}
        )

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["tool"], "schema_diff")
        self.assertEqual(result["result"]["status"], "PASS")

    def test_validate_tool_unknown_import_fails_safely(self):
        result = tool_contract_validator.run(
            {"action": "validate_tool", "tool_name": "missing_v19_tool"}
        )

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertFalse(result["success"])
        self.assertEqual(result["result"]["status"], "FAIL")
        self.assertIn("import failed", result["result"]["reason"])

    def test_validate_all_isolated_to_safe_allowlist(self):
        with patch.object(
            tool_contract_validator,
            "_candidate_tools",
            return_value=["schema_diff", "ana_runtime_inspector"],
        ):
            result = tool_contract_validator.run({"action": "validate_all"})

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertEqual(result["counts"]["FAIL"], 0)
        self.assertEqual(len(result["results"]), 2)

    def test_unknown_action_is_safe_error(self):
        result = tool_contract_validator.run({"action": "does_not_exist"})

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertFalse(result["success"])
        self.assertIn("error", result)


# PATCH_END v19_phase2
