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
            PROJECT_ROOT / "index.html",
            PROJECT_ROOT / "videos.html",
            PROJECT_ROOT / ".env.example",
            PROJECT_ROOT / "docs" / "README.md",
            PROJECT_ROOT / "docs" / "AI_COLLABORATION_AND_TOOLS.md",
            PROJECT_ROOT / "docs" / "PROJECT_MAP_AI_GUIDE.md",
            PROJECT_ROOT / "docs" / "AGENT_IDE_SUPER_TOOLS_PLAN.md",
            PROJECT_ROOT / "docs" / "USER_EXTENSION_INSTALL_AND_ETHICS.md",
            PROJECT_ROOT / "docs" / "ANA_WORKGRAPH_ARCHITECTURE.md",
            PROJECT_ROOT / "docs" / "ANA_MAX_WOW_DEMO.md",
            PROJECT_ROOT / "docs" / "LOCAL_QA_LAB_VISION.md",
            PROJECT_ROOT / "vscode_extension" / "README.md",
            PROJECT_ROOT / "vscode_extension" / "package.json",
            PROJECT_ROOT / "vscode_extension" / "src" / "extension.js",
            PROJECT_ROOT / "assets" / "VIDEO_MAP.md",
            PROJECT_ROOT / "assets" / "videos" / "README.md",
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

    def test_vscode_extension_sends_mcp_auth(self):
        package_json = (PROJECT_ROOT / "vscode_extension" / "package.json").read_text(encoding="utf-8")
        extension_js = (PROJECT_ROOT / "vscode_extension" / "src" / "extension.js").read_text(encoding="utf-8")

        self.assertIn("anaMax.mcpApiKey", package_json)
        self.assertIn("Authorization", extension_js)
        self.assertIn("Bearer ${mcpConfig.apiKey}", extension_js)
        self.assertIn("MCP_API_KEY", extension_js)

    def test_vscode_agent_mode_is_documented(self):
        main_py = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
        tool_base = (PROJECT_ROOT / "tools" / "base.py").read_text(encoding="utf-8")
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        setup = (PROJECT_ROOT / "SETUP_AND_RUN.md").read_text(encoding="utf-8")
        project_map = (PROJECT_ROOT / "docs" / "PROJECT_MAP_AI_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn("VSCODE_AGENT", main_py)
        self.assertIn("VSCODE_AGENT", tool_base)
        self.assertIn("vscode_agent", main_py)
        self.assertIn("output_profile", main_py)
        self.assertIn("VSCODE_AGENT", readme)
        self.assertIn("VSCODE_AGENT", setup)
        self.assertIn("VSCODE_AGENT", project_map)

    def test_website_does_not_embed_large_local_videos(self):
        for name in ("index.html", "videos.html"):
            content = (PROJECT_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("<video", content)
            self.assertNotIn(".mp4", content)
