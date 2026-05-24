#!/usr/bin/env python3
"""
ANA MAX - Smoke Tests
======================
Teste rapide pentru a verifica ca sistemul de baza functioneaza corect.
Aceste teste sunt concepute sa ruleze rapid si sa acopere functionalitatile critice.

Utilizare:
    python -m pytest tests/test_smoke.py -v
    python -m pytest tests/test_smoke.py -v --tb=short
"""

import sys
import time
import tempfile
import asyncio
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

# Asigura-te ca proiectul este in path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestImports(TestCase):
    """Teste de import pentru modulele principale."""
    
    def test_import_core_modules(self):
        """Testeaza importul modulelor core."""
        from core import config
        from core import agent
        from core import mcp_server
        self.assertTrue(True)
    
    def test_import_tools_base(self):
        """Testeaza importul tools.base."""
        from tools.base import registry
        self.assertIsNotNone(registry)
    
    def test_import_license_manager(self):
        """Testeaza importul license_manager."""
        from core import license_manager
        self.assertIsNotNone(license_manager)
    
    def test_import_main(self):
        """Testeaza importul main."""
        import main
        self.assertTrue(hasattr(main, 'main'))
        self.assertTrue(hasattr(main, '_register_all_tools'))


class TestLicenseManagerBasic(TestCase):
    """Teste de baza pentru LicenseManager."""
    
    def test_license_manager_instantiation(self):
        """Testeaza crearea unei instante LicenseManager."""
        from core.license_manager import LicenseManager
        manager = LicenseManager()
        self.assertIsNotNone(manager)
    
    def test_license_manager_singleton(self):
        """Testeaza singleton-ul global."""
        from core.license_manager import get_license_manager
        manager1 = get_license_manager()
        manager2 = get_license_manager()
        self.assertIs(manager1, manager2)
    
    def test_free_tools_allowed(self):
        """Testeaza ca tool-urile gratuite sunt permise."""
        from core.license_manager import LicenseManager
        manager = LicenseManager()
        
        free_tools = ["code", "files", "web", "system", "git"]
        for tool in free_tools:
            self.assertTrue(manager.is_tool_allowed(tool), 
                          f"Tool-ul {tool} ar trebui sa fie gratuit")
    
    def test_premium_tools_blocked_without_license(self):
        """Testeaza ca tool-urile premium sunt blocate fara licenta."""
        from core.license_manager import LicenseManager
        manager = LicenseManager()
        
        premium_tools = ["live_desktop_viewer", "windows_deep_sight"]
        for tool in premium_tools:
            self.assertFalse(manager.is_tool_allowed(tool), 
                           f"Tool-ul {tool} ar trebui sa fie premium")
    
    def test_check_premium_access_free_tool(self):
        """Testeaza check_premium_access pentru tool gratuit."""
        from core.license_manager import check_premium_access
        allowed, message = check_premium_access("code")
        self.assertTrue(allowed)
        self.assertEqual(message, "Access granted")


class TestToolRegistryBasic(TestCase):
    """Teste de baza pentru tool registry."""
    
    def test_registry_not_empty(self):
        """Testeaza ca registry nu este gol."""
        from tools.base import registry
        tools = registry.list_tools()
        self.assertTrue(len(tools) > 0, "Registry ar trebui sa aiba tool-uri")
    
    def test_registry_has_expected_tools(self):
        """Testeaza ca registry are tool-urile de baza."""
        from tools.base import registry
        tools = registry.list_tools()
        
        expected_tools = [
            "file_operations",
            "system_control",
            "code_tools",
            "web_search",
            "desktop_capture",
            "workspace_situational_awareness",
            "file_patch",
            "project_navigator",
            "error_radar",
            "uia_click",
            "uia_type",
            "vision_region_capture",
            "vision_find_element",
        ]
        for tool in expected_tools:
            self.assertIn(tool, tools, f"Tool-ul {tool} ar trebui sa existe")

    def test_public_tool_count_baseline(self):
        """Public release should keep its documented tool count aligned."""
        from main import _register_all_tools
        from tools.base import registry

        registry.reset()
        _register_all_tools()
        self.assertEqual(len(registry.list_tools()), 71)
    
    def test_registry_get_tool(self):
        """Testeaza obtinerea unui tool din registry."""
        from tools.base import registry
        tool = registry.get("file_operations")
        self.assertIsNotNone(tool)
        self.assertTrue(hasattr(tool, 'get_definition'))
    
    def test_registry_execute_file_list(self):
        """Testeaza executia file_operations list."""
        from tools.base import registry
        result = registry.execute("file_operations", operation="list", path=".")
        self.assertTrue(result.is_success)
        self.assertIsNotNone(result.data)
        self.assertIsInstance(result.data, (dict, str))
        self.assertTrue(result.data)

    def test_registry_blocks_premium_tool_without_license(self):
        """Premium tools must be blocked at registry execution, not only in LicenseManager."""
        import core.license_manager as lm
        from core.license_manager import LicenseManager
        from tools.base import registry

        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()

        with tempfile.TemporaryDirectory() as tmp:
            lm._license_manager = LicenseManager(str(Path(tmp) / ".license"))
            result = registry.execute("live_desktop_viewer", operation="status")
            self.assertFalse(result.is_success)
            self.assertIn("premium", (result.error or result.message).lower())
        lm._license_manager = None

    def test_ai_core_adapters_have_backing_modules(self):
        """Listed AI Core adapters should not be phantom tools."""
        from tools.base import registry

        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()

        for tool_name, params in [
            ("window_manager", {"action": "list"}),
            ("edge_tts_voice", {"action": "status"}),
        ]:
            result = registry.execute(tool_name, **params)
            self.assertTrue(result.is_success, result.error)

    def test_browser_control_supports_external_chrome_launch(self):
        """Browser tool should support a persistent external Chrome launch."""
        from tools.browser_control import BrowserControlTool

        definition = BrowserControlTool().get_definition()
        operation = next(
            param for param in definition.parameters if param.name == "operation"
        )
        browser_path = next(
            param for param in definition.parameters if param.name == "browser_path"
        )

        self.assertIn("open_external", operation.choices)
        self.assertFalse(browser_path.required)

    def test_browser_runtime_prefers_chrome_before_brave(self):
        """Chrome should be preferred for Windows browser workflows."""
        from core.browser_runtime import BrowserAutomationRuntime

        candidates = [str(path) for path in BrowserAutomationRuntime._candidate_browser_paths()]
        chrome_index = next(i for i, path in enumerate(candidates) if "Chrome" in path)
        brave_index = next(i for i, path in enumerate(candidates) if "Brave" in path)

        self.assertLess(chrome_index, brave_index)

    def test_browser_open_external_reports_invalid_explicit_path(self):
        """Explicit invalid browser paths should fail instead of falling back silently."""
        from tools.browser_control import BrowserControlTool
        from tools.base import ToolStatus

        result = BrowserControlTool().execute(
            operation="open_external",
            url="https://example.com/",
            browser_path=r"C:\missing\chrome.exe",
        )

        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("does not exist", result.error)
        self.assertFalse(result.data["opened"])

    def test_browser_open_external_reports_system_fallback_failure(self):
        """A failed system fallback should be an error result."""
        from tools.browser_control import BrowserControlTool
        from tools.base import ToolStatus

        with patch("tools.browser_control.Path.exists", return_value=False), patch(
            "tools.browser_control.webbrowser.open", return_value=False
        ):
            result = BrowserControlTool().execute(
                operation="open_external",
                url="https://example.com/",
            )

        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertFalse(result.data["opened"])

    def test_browser_open_external_allows_system_fallback_success(self):
        """System browser fallback can still succeed when Chrome is unavailable."""
        from tools.browser_control import BrowserControlTool
        from tools.base import ToolStatus

        with patch("tools.browser_control.Path.exists", return_value=False), patch(
            "tools.browser_control.webbrowser.open", return_value=True
        ):
            result = BrowserControlTool().execute(
                operation="open_external",
                url="https://example.com/",
            )

        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertTrue(result.data["opened"])
        self.assertEqual(result.data["mode"], "system_default")

    def test_core_mcp_server_exposes_real_tool_schema(self):
        """Legacy MCP bridge should expose the same callable tool schema."""
        import core.mcp_server as mcp
        from main import _register_all_tools

        _register_all_tools()
        mcp._mcp_server = None
        server = mcp.get_mcp_server()
        browser = server.tools["browser_control"]
        operation = browser["inputSchema"]["properties"]["operation"]

        self.assertIn("open_external", operation["enum"])
        self.assertIn("browser_path", browser["inputSchema"]["properties"])

    def test_core_mcp_server_uses_registry_license_gate(self):
        """MCP tool calls must go through ToolRegistry license checks."""
        import core.license_manager as lm
        import core.mcp_server as mcp
        from core.license_manager import LicenseManager
        from main import _register_all_tools

        _register_all_tools()
        mcp._mcp_server = None
        with tempfile.TemporaryDirectory() as tmp:
            lm._license_manager = LicenseManager(str(Path(tmp) / ".license"))
            server = mcp.get_mcp_server()
            response = asyncio.run(
                server.handle_request(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "live_desktop_viewer",
                            "arguments": {"operation": "status"},
                        },
                    }
                )
            )
        lm._license_manager = None

        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "blocked")

    def test_workspace_situational_awareness_snapshot(self):
        """WorkGraph snapshot should be compact, read-only, and useful."""
        from tools.base import registry

        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()

        result = registry.execute("workspace_situational_awareness", path=".", max_files=10)
        self.assertTrue(result.is_success, result.error)
        self.assertEqual(result.data["schema"], "ana.workgraph.workspace_state.v1")
        self.assertEqual(result.data["mode"], "observe_only")
        self.assertIn("workspace", result.data)
        self.assertIn("recommended_next_step", result.data)
        self.assertLess(len(str(result.data)), 8192)

    def test_workspace_situational_awareness_handles_agent_inputs(self):
        """WorkGraph snapshot should tolerate file paths and loose AI parameters."""
        from tools.base import registry

        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()

        result = registry.execute(
            "workspace_situational_awareness",
            path="main.py",
            max_files="not-a-number",
        )
        self.assertTrue(result.is_success, result.error)
        self.assertTrue(result.data["workspace"]["available"])
        self.assertNotIn("repo_path", result.data["workspace"])

    def test_tool_healthcheck_safe_scope_stays_offline(self):
        """Safe healthcheck must avoid semantic search model/network loading."""
        from tools.base import ToolResult, ToolStatus
        from tools.tool_healthcheck import ToolHealthcheckTool

        calls = []

        def fake_execute(name, **params):
            calls.append((name, params))
            return ToolResult(status=ToolStatus.SUCCESS, data={}, message="ok")

        with patch("tools.tool_healthcheck.registry.execute", side_effect=fake_execute):
            result = ToolHealthcheckTool().execute(operation="summary")

        self.assertTrue(result.is_success)
        self.assertNotIn("codebase_understanding", [name for name, _ in calls])
        self.assertIn("workspace_situational_awareness", [name for name, _ in calls])
        self.assertIn("project_navigator", [name for name, _ in calls])
        self.assertIn("error_radar", [name for name, _ in calls])

    def test_new_public_tools_are_compact_and_safe(self):
        """New public utility tools should import and perform non-mutating checks."""
        from tools.base import registry

        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()

        nav = registry.execute("project_navigator", operation="find", path="tools", pattern="base.py", limit=3)
        self.assertTrue(nav.is_success, nav.error)

        radar = registry.execute("error_radar", scope="quick", limit=3)
        self.assertTrue(radar.is_success, radar.error)
        self.assertEqual(radar.data["schema"], "ana.error_radar.v1")

        confirm = registry.execute("uia_click", window_title="x", element_title="y")
        self.assertEqual(confirm.status.value, "requires_confirmation")


class TestConfig(TestCase):
    """Teste pentru config."""
    
    def test_config_load(self):
        """Testeaza incarcarea config-ului."""
        from core.config import config
        # Config-ul ar trebui sa fie deja incarcat de main.py
        self.assertIsNotNone(config)
    
    def test_config_get_mcp_settings(self):
        """Testeaza obtinerea setarilor MCP."""
        from core.config import config
        host = config.get("mcp.host", "127.0.0.1")
        port = config.get("mcp.port", 8765)
        
        self.assertIsInstance(host, str)
        self.assertIsInstance(port, int)


class TestMainFunctions(TestCase):
    """Teste pentru functiile din main."""
    
    def test_build_parser(self):
        """Testeaza crearea parser-ului."""
        from main import _build_parser
        parser = _build_parser()
        self.assertIsNotNone(parser)
        
        # Testeaza argumentele
        args = parser.parse_args(["--port", "9999", "--debug"])
        self.assertEqual(args.port, 9999)
        self.assertTrue(args.debug)
    
    def test_print_banner(self):
        """Testeaza afisarea banner-ului."""
        from main import _print_banner
        # Nu ar trebui sa arunce exceptie
        _print_banner()
    
    def test_list_tools(self):
        """Testeaza listarea tool-urilor."""
        from main import _list_tools
        # Nu ar trebui sa arunce exceptie
        _list_tools()
    
    def test_run_tests(self):
        """Testeaza rularea testelor rapide."""
        from main import _run_tests
        # Nu ar trebui sa arunce exceptie
        result = _run_tests()
        self.assertIsInstance(result, bool)


class TestPyprojectToml(TestCase):
    """Teste pentru pyproject.toml."""
    
    def test_pyproject_exists(self):
        """Testeaza existenta pyproject.toml."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), "pyproject.toml ar trebui sa existe")
    
    def test_pyproject_content(self):
        """Testeaza continutul pyproject.toml."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")
        
        self.assertIn("[project]", content)
        self.assertIn("name = \"ana-max\"", content)
        self.assertIn("version = \"0.1.0-beta\"", content)
        self.assertIn("[project.scripts]", content)
        self.assertIn("ana-max = \"main:main\"", content)


class TestDocumentation(TestCase):
    """Teste pentru documentatie."""
    
    def test_licensing_doc_exists(self):
        """Testeaza existenta docs/LICENSING.md."""
        licensing_path = PROJECT_ROOT / "docs" / "LICENSING.md"
        self.assertTrue(licensing_path.exists(), "docs/LICENSING.md ar trebui sa existe")
    
    def test_licensing_content(self):
        """Testeaza continutul LICENSING.md."""
        licensing_path = PROJECT_ROOT / "docs" / "LICENSING.md"
        content = licensing_path.read_text(encoding="utf-8")
        
        self.assertIn("ANA MAX", content)
        self.assertIn("License", content)
        self.assertIn("Pro", content)
        self.assertIn("Free", content)


class TestScripts(TestCase):
    """Teste pentru script-urile utilitare."""
    
    def test_activate_license_exists(self):
        """Testeaza existenta activate_license.py."""
        script_path = PROJECT_ROOT / "activate_license.py"
        self.assertTrue(script_path.exists(), "activate_license.py ar trebui sa existe")
    
    def test_generate_license_exists(self):
        """Testeaza existenta generate_license.py."""
        script_path = PROJECT_ROOT / "generate_license.py"
        self.assertTrue(script_path.exists(), "generate_license.py ar trebui sa existe")
    
    def test_activate_license_content(self):
        """Testeaza continutul activate_license.py."""
        script_path = PROJECT_ROOT / "activate_license.py"
        content = script_path.read_text(encoding="utf-8")
        
        self.assertIn("LicenseManager", content)
        self.assertIn("activate", content)
    
    def test_generate_license_content(self):
        """Testeaza continutul generate_license.py."""
        script_path = PROJECT_ROOT / "generate_license.py"
        content = script_path.read_text(encoding="utf-8")
        
        self.assertIn("LicenseManager", content)
        self.assertIn("generate_license_key", content)


class TestPerformance(TestCase):
    """Teste de performanta de baza."""
    
    def test_import_time(self):
        """Testeaza timpul de import."""
        start = time.time()
        import main
        elapsed = time.time() - start
        # Importul nu ar trebui sa dureze mai mult de 5 secunde
        self.assertLess(elapsed, 5.0, f"Importul a durat {elapsed:.2f} secunde")
    
    def test_tool_registration_time(self):
        """Testeaza timpul de inregistrare a tool-urilor."""
        from main import _register_all_tools
        start = time.time()
        count = _register_all_tools()
        elapsed = time.time() - start
        
        self.assertGreater(count, 0, "Ar trebui sa se inregistreze tool-uri")
        # Incarcarea include tool-uri optionale grele pe Windows; pragul ramane de smoke test.
        self.assertLess(elapsed, 45.0, f"Inregistrarea a durat {elapsed:.2f} secunde")
    
    def test_tool_execution_time(self):
        """Testeaza timpul de executie al unui tool."""
        from tools.base import registry
        if not registry.list_tools():
            from main import _register_all_tools
            _register_all_tools()
        
        start = time.time()
        result = registry.execute("file_operations", operation="list", path=".")
        elapsed = time.time() - start
        
        self.assertTrue(result.is_success)
        # Executia nu ar trebui sa dureze mai mult de 2 secunde
        self.assertLess(elapsed, 2.0, f"Executia a durat {elapsed:.2f} secunde")


if __name__ == "__main__":
    main()
