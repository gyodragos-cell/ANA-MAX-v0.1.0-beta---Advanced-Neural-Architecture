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
from pathlib import Path
from unittest import TestCase, main

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
        
        premium_tools = ["desktop_capture", "windows_deep_sight"]
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
        
        expected_tools = ["file_operations", "system_control", "code_operations", "web_operations"]
        for tool in expected_tools:
            self.assertIn(tool, tools, f"Tool-ul {tool} ar trebui sa existe")
    
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
        self.assertIsInstance(result.data, dict)
        self.assertIn("files", result.data)


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
        content = pyproject_path.read_text()
        
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
        content = licensing_path.read_text()
        
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
        content = script_path.read_text()
        
        self.assertIn("LicenseManager", content)
        self.assertIn("activate", content)
    
    def test_generate_license_content(self):
        """Testeaza continutul generate_license.py."""
        script_path = PROJECT_ROOT / "generate_license.py"
        content = script_path.read_text()
        
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
        # Inregistrarea nu ar trebui sa dureze mai mult de 10 secunde
        self.assertLess(elapsed, 10.0, f"Inregistrarea a durat {elapsed:.2f} secunde")
    
    def test_tool_execution_time(self):
        """Testeaza timpul de executie al unui tool."""
        from tools.base import registry
        
        start = time.time()
        result = registry.execute("file_operations", operation="list", path=".")
        elapsed = time.time() - start
        
        self.assertTrue(result.is_success)
        # Executia nu ar trebui sa dureze mai mult de 2 secunde
        self.assertLess(elapsed, 2.0, f"Executia a durat {elapsed:.2f} secunde")


if __name__ == "__main__":
    main()