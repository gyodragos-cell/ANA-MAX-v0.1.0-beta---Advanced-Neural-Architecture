"""
ANA MAX - Configuration Loader
===================================
Incarca si valideaza configuratia din YAML.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Singleton pentru configuratia A.N.A."""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config:
            self.load()

    _legacy_key_map = {
        'safety.sandbox_mode': 'security.sandbox.enabled',
    }
    
    def load(self, config_path: Optional[str] = None) -> None:
        """Incarca configuratia din fisier YAML."""
        if config_path is None:
            # Cauta config in directorul curent sau in config/
            possible_paths = [
                Path(__file__).parent.parent / "config" / "settings.yaml",
                Path("config/settings.yaml"),
                Path("settings.yaml"),
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            self._normalize_paths(Path(config_path).resolve().parent)
            logger.info(f"Configuratie incarcata din: {config_path}")
        else:
            logger.warning("Nu s-a gasit fisier de configuratie, folosesc valori implicite")
            self._config = self._get_defaults()

    def _normalize_paths(self, base_dir: Path) -> None:
        """Rezolva caile relative din config fata de directorul fisierului YAML."""
        path_keys = [
            'memory.database_path',
            'logging.file',
            'plugins.directory',
            'evolution.evolution_log_path',
            'evolution.backup_directory',
            'ai.gemini.api_key_file',
            'ai.grok.api_key_file',
            'engineer.workspace_root',
            'engineer.generated_projects_dir',
        ]
        for key in path_keys:
            value = self.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            path_value = Path(value)
            if path_value.is_absolute():
                continue
            self.set(key, str((base_dir / path_value).resolve()))
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Returneaza configuratia implicita."""
        return {
            'ai': {
                'primary_backend': 'gemini',
                'fallback_backend': 'ollama',
                'routing': {
                    'enabled': False,
                    'cooldown_seconds': 300,
                    'max_failures': 1,
                    'rotate_at_percent': 70,
                    'backends': [],
                },
                'gemini': {
                    'model': 'models/gemini-flash-latest',
                    'api_key_file': 'API_KEY.txt',
                    'max_retries': 3,
                },
                'ollama': {
                    'api_url': 'http://localhost:11434/api/generate',
                    'model': 'qwen2.5:7b',
                    'temperature': 0.7,
                    'max_tokens': 2000,
                }
            },
            'memory': {
                'type': 'sqlite',
                'database_path': 'memory/ana_brain.db',
                'max_conversation_history': 50,
                'max_error_entries': 1000,
            },
            'security': {
                'shell': {
                    'enabled': True,
                    'require_confirmation': False,
                    'allowed_commands': ['*'],  # Permite orice comanda
                    'blocked_commands': [],    # Nu blocheaza niciuna
                },
                'sandbox': {
                    'enabled': False,
                    'timeout_seconds': 0,
                    'max_memory_mb': 1256,
                },
                'self_modification': {
                    'enabled': True,
                }
            },
            'plugins': {
                'enabled': True,
                'directory': 'plugins/',
                'auto_load': True,
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/ana.log',
            },
            'ui': {
                'language': 'ro',
                'colored_output': True,
            },
            'evolution': {
                'autonomous_study': True,
                'idle_time_seconds': 300,
                'max_changes_per_day': 10
            },
            'engineer': {
                'enabled': False,
                'workspace_root': '.',
                'generated_projects_dir': 'generated_bots',
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtine o valoare din configuratie folosind notatie cu punct.
        Exemplu: config.get('ai.gemini.model')
        """
        for candidate in (key, self._legacy_key_map.get(key)):
            if not candidate:
                continue

            keys = candidate.split('.')
            value = self._config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    value = None
                    break

            if value is not None:
                return value

        return default
    
    def set(self, key: str, value: Any) -> None:
        """Seteaza o valoare in configuratie."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    @property
    def all(self) -> Dict[str, Any]:
        """Returneaza intreaga configuratie."""
        return self._config.copy()


# Instanta globala
config = Config()
