#!/usr/bin/env python3
"""Release hygiene tests for public-facing docs."""

from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestPublicDocsHygiene(TestCase):
    def test_shell_facing_docs_are_ascii_clean(self):
        files = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "SETUP_AND_RUN.md",
            PROJECT_ROOT / "AGENTS.md",
            PROJECT_ROOT / "CHANGELOG.md",
            PROJECT_ROOT / ".env.example",
            PROJECT_ROOT / "docs" / "PROJECT_MAP_AI_GUIDE.md",
        ]
        forbidden = [
            "\u00e2",
            "\u20ac",
            "\u0153",
            "mcp_server.py",
            "ana_dev",
            ".qoder",
            ".kiro",
            "Jules",
            "Qoder",
            "Kiro",
        ]

        for path in files:
            content = path.read_text(encoding="utf-8")
            try:
                content.encode("ascii")
            except UnicodeEncodeError as exc:
                self.fail(f"{path.relative_to(PROJECT_ROOT)} contains non-ASCII text: {exc}")

            for token in forbidden:
                self.assertNotIn(token, content, f"{path.relative_to(PROJECT_ROOT)} contains {token!r}")

    def test_env_example_documents_required_public_auth(self):
        content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("MCP_API_KEY=", content)
