"""
A.N.A. v15.0 - Plugin System
============================
Sistem de plugin-uri pentru extensibilitate.
Înlocuiește self_modify_code cu o abordare sigură.
"""

import os
import json
import importlib.util
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadate pentru un plugin."""
    name: str
    version: str
    description: str
    author: str = "Unknown"
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True


class Plugin(ABC):
    """
    Clasă de bază pentru plugin-uri.
    Toate plugin-urile trebuie să extindă această clasă.
    """
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Returnează metadatele plugin-ului."""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Inițializează plugin-ul. Returnează True dacă succes."""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[Callable]:
        """Returnează funcțiile/tool-urile oferite de plugin."""
        pass
    
    def cleanup(self) -> None:
        """Curăță resursele la dezactivare. Override opțional."""
        pass
    
    def on_message(self, message: str) -> Optional[str]:
        """
        Hook pentru procesare mesaje. Override opțional.
        Returnează None pentru a nu interveni sau un răspuns pentru a intercepta.
        """
        return None


class PluginManager:
    """
    Manager pentru încărcarea și gestionarea plugin-urilor.
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, Plugin] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Creează directorul de plugin-uri dacă nu există."""
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Creează __init__.py
        init_file = self.plugins_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""A.N.A. Plugins Directory"""\n')
    
    def discover_plugins(self) -> List[str]:
        """Descoperă plugin-urile disponibile."""
        discovered = []
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "plugin.py").exists():
                discovered.append(item.name)
            elif item.suffix == ".py" and item.name != "__init__.py":
                discovered.append(item.stem)
        
        return discovered
    
    def load_plugin(self, name: str) -> bool:
        """Încarcă un plugin după nume."""
        try:
            # Caută fișierul plugin-ului
            plugin_path = None
            
            # Director cu plugin.py
            dir_path = self.plugins_dir / name / "plugin.py"
            if dir_path.exists():
                plugin_path = dir_path
            else:
                # Fișier direct
                file_path = self.plugins_dir / f"{name}.py"
                if file_path.exists():
                    plugin_path = file_path
            
            if not plugin_path:
                logger.error(f"Plugin-ul '{name}' nu a fost găsit")
                return False
            
            # Încarcă modulul
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", plugin_path)
            if not spec or not spec.loader:
                logger.error(f"Nu pot încărca spec pentru plugin '{name}'")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Găsește clasa Plugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr is not Plugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.error(f"Nu am găsit clasă Plugin în '{name}'")
                return False
            
            # Instanțiază și inițializează
            plugin_instance = plugin_class()
            
            if not plugin_instance.initialize():
                logger.error(f"Inițializare eșuată pentru plugin '{name}'")
                return False
            
            # Salvează
            self.plugins[name] = plugin_instance
            self.metadata[name] = plugin_instance.get_metadata()
            
            logger.info(f"Plugin încărcat: {name} v{self.metadata[name].version}")
            return True
            
        except Exception as e:
            logger.error(f"Eroare la încărcarea plugin-ului '{name}': {e}")
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """Descarcă un plugin."""
        if name not in self.plugins:
            return False
        
        try:
            self.plugins[name].cleanup()
            del self.plugins[name]
            del self.metadata[name]
            logger.info(f"Plugin descărcat: {name}")
            return True
        except Exception as e:
            logger.error(f"Eroare la descărcarea plugin-ului '{name}': {e}")
            return False
    
    def load_all(self) -> int:
        """Încarcă toate plugin-urile disponibile."""
        loaded = 0
        for name in self.discover_plugins():
            if self.load_plugin(name):
                loaded += 1
        return loaded
    
    def get_all_tools(self) -> List[Callable]:
        """Obține toate tool-urile de la toate plugin-urile."""
        tools = []
        for plugin in self.plugins.values():
            tools.extend(plugin.get_tools())
        return tools
    
    def process_message(self, message: str) -> Optional[str]:
        """Permite plugin-urilor să proceseze mesaje."""
        for plugin in self.plugins.values():
            response = plugin.on_message(message)
            if response is not None:
                return response
        return None
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Listează toate plugin-urile încărcate."""
        return {
            name: {
                'version': meta.version,
                'description': meta.description,
                'author': meta.author,
                'capabilities': meta.capabilities,
                'enabled': meta.enabled
            }
            for name, meta in self.metadata.items()
        }


# Template pentru plugin nou
PLUGIN_TEMPLATE = '''"""
{name} Plugin for A.N.A.
========================
{description}
"""

from plugins import Plugin, PluginMetadata
from typing import List, Callable, Optional


class {class_name}Plugin(Plugin):
    """Plugin: {name}"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{name}",
            version="1.0.0",
            description="{description}",
            author="{author}",
            capabilities=["custom_tool"]
        )
    
    def initialize(self) -> bool:
        """Inițializare plugin."""
        # Adaugă logica de inițializare aici
        return True
    
    def get_tools(self) -> List[Callable]:
        """Returnează tool-urile plugin-ului."""
        return [self.my_custom_tool]
    
    def my_custom_tool(self, param: str) -> str:
        """
        Tool personalizat.
        
        Args:
            param: Parametru de exemplu
        
        Returns:
            Rezultatul operației
        """
        return f"Plugin {self.get_metadata().name}: procesat '{{param}}'"
    
    def cleanup(self) -> None:
        """Curățare la dezactivare."""
        pass
'''


def create_plugin_template(name: str, description: str = "", 
                           author: str = "Unknown",
                           plugins_dir: str = "plugins") -> str:
    """Creează un template pentru un plugin nou."""
    # Normalizează numele
    class_name = ''.join(word.capitalize() for word in name.replace('-', '_').split('_'))
    
    content = PLUGIN_TEMPLATE.format(
        name=name,
        class_name=class_name,
        description=description or f"Plugin {name} pentru A.N.A.",
        author=author
    )
    
    # Creează directorul și fișierul
    plugin_dir = Path(plugins_dir) / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    plugin_file = plugin_dir / "plugin.py"
    plugin_file.write_text(content)
    
    # Creează __init__.py
    (plugin_dir / "__init__.py").write_text(f'from .plugin import {class_name}Plugin\n')
    
    return str(plugin_file)
