#!/usr/bin/env python3
"""
Teste pentru tool registry si tool-uri de baza.
"""

import sys
from pathlib import Path
from unittest import TestCase, main

# Asigura-te ca proiectul este in path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestToolRegistry(TestCase):
    """Teste pentru registry-ul de tool-uri."""
    
    def test_registry_import(self):
        """Testeaza importul registry."""
        from tools.base import registry
        self.assertIsNotNone(registry)
    
    def test_registry_list_tools(self):
        """Testeaza listarea tool-urilor."""
        from tools.base import registry
        tools = registry.list_tools()
        self.assertIsInstance(tools, list)
        self.assertTrue(len(tools) > 0)
    
    def test_registry_get_tool(self):
        """Testeaza obtinerea unui tool."""
        from tools.base import registry
        
        # Incearca sa obtina un tool cunoscut
        tools = registry.list_tools()
        if tools:
            tool = registry.get(tools[0])
            self.assertIsNotNone(tool)
            self.assertTrue(hasattr(tool, 'get_definition'))
    
    def test_registry_execute(self):
        """Testeaza executia unui tool."""
        from tools.base import registry
        
        # Incearca sa execute un tool simplu
        # File operations ar trebui sa fie intotdeauna disponibile
        result = registry.execute("file_operations", operation="list", path=".")
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'is_success'))


class TestBasicTools(TestCase):
    """Teste pentru tool-uri individuale."""
    
    def test_files_tool(self):
        """Testeaza FilesTool."""
        from tools.files import FilesTool
        
        tool = FilesTool()
        definition = tool.get_definition()
        
        self.assertIsNotNone(definition)
        self.assertEqual(definition.name, "file_operations")
    
    def test_system_tool(self):
        """Testeaza SystemTool."""
        from tools.system import SystemTool
        
        tool = SystemTool()
        definition = tool.get_definition()
        
        self.assertIsNotNone(definition)
        self.assertEqual(definition.name, "system_control")
    
    def test_code_tool(self):
        """Testeaza CodeTool."""
        from tools.code import CodeTool
        
        tool = CodeTool()
        definition = tool.get_definition()
        
        self.assertIsNotNone(definition)
        self.assertEqual(definition.name, "code_operations")
    
    def test_web_tool(self):
        """Testeaza WebTool."""
        from tools.web import WebTool
        
        tool = WebTool()
        definition = tool.get_definition()
        
        self.assertIsNotNone(definition)
        self.assertEqual(definition.name, "web_operations")


class TestToolExecution(TestCase):
    """Teste de executie pentru tool-uri."""
    
    def test_file_list_operation(self):
        """Testeaza listarea fisierelor."""
        from tools.base import registry
        
        result = registry.execute("file_operations", operation="list", path=".")
        
        self.assertTrue(result.is_success)
        self.assertIsNotNone(result.data)
        self.assertIsInstance(result.data, dict)
        self.assertIn("files", result.data)
    
    def test_system_vitals(self):
        """Testeaza obtinerea informatiilor de sistem."""
        from tools.base import registry
        
        result = registry.execute("system_control", operation="vitals")
        
        self.assertTrue(result.is_success)
        self.assertIsNotNone(result.data)
        self.assertIsInstance(result.data, dict)
    
    def test_invalid_tool(self):
        """Testeaza executia unui tool invalid."""
        from tools.base import registry
        
        with self.assertRaises(Exception):
            registry.execute("nonexistent_tool")
    
    def test_invalid_operation(self):
        """Testeaza o operatie invalida."""
        from tools.base import registry
        
        result = registry.execute("file_operations", operation="invalid_op")
        
        self.assertFalse(result.is_success)
        self.assertIsNotNone(result.error)


class TestToolDefinitions(TestCase):
    """Teste pentru definitiile tool-urilor."""
    
    def test_tool_definition_structure(self):
        """Testeaza structura definitiei unui tool."""
        from tools.files import FilesTool
        
        tool = FilesTool()
        definition = tool.get_definition()
        
        # Verifica atributele necesare
        self.assertTrue(hasattr(definition, 'name'))
        self.assertTrue(hasattr(definition, 'description'))
        self.assertTrue(hasattr(definition, 'category'))
        self.assertTrue(hasattr(definition, 'parameters'))
        
        # Verifica tipurile
        self.assertIsInstance(definition.name, str)
        self.assertIsInstance(definition.description, str)
        self.assertIsInstance(definition.category, str)
    
    def test_tool_definition_to_dict(self):
        """Testeaza conversia definitiei in dict."""
        from tools.files import FilesTool
        
        tool = FilesTool()
        definition = tool.get_definition()
        
        data = definition.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertIn("name", data)
        self.assertIn("description", data)


if __name__ == "__main__":
    main()