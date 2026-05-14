"""
A.N.A. v15.0 - Backup Plugin
=============================
Plugin pentru arhivarea și salvarea proiectului.
"""

import os
import zipfile
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)

from plugins import Plugin, PluginMetadata

class BackupPlugin(Plugin):
    """
    Plugin care permite crearea de snapshot-uri complete ale proiectului.
    """
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            # Detectăm root-ul proiectului (presupunem că suntem în plugins/)
            self.project_root = Path(__file__).parent.parent.resolve()
        else:
            self.project_root = Path(project_root).resolve()
            
        self.backup_dir = self.project_root / "backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="backup_plugin",
            version="1.1.0",
            description="Plugin pentru arhivarea și salvarea proiectului ANA.",
            author="Ghost",
            capabilities=["backup", "archive"]
        )

    def initialize(self) -> bool:
        """Inițializează plugin-ul."""
        return True

    def get_tools(self) -> List[Callable]:
        """Returnează tool-urile plugin-ului."""
        return [self.create_project_backup, self.list_project_backups]

    def create_project_backup(self) -> str:
        """Creează o arhivă ZIP de siguranță cu tot proiectul ANA."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"ana_backup_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'backups', 'node_modules'}
        exclude_files = {backup_name, '.DS_Store'}
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.project_root):
                    # Excludem directoarele nedorite
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    
                    for file in files:
                        if file in exclude_files:
                            continue
                            
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.project_root)
                        zipf.write(file_path, arcname)
            
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            logger.info(f"Backup creat cu succes: {backup_name} ({size_mb:.2f} MB)")
            
            return f"✅ Backup creat: {backup_name} ({size_mb:.2f} MB). Îl găsești în folderul 'backups/'."
        except Exception as e:
            logger.error(f"Eroare la crearea backup-ului: {e}")
            return f"❌ Eroare: {str(e)}"

    def list_project_backups(self) -> str:
        """Listează toate arhivele de backup disponibile."""
        if not self.backup_dir.exists():
            return "Nu am găsit niciun backup."
            
        backups = []
        for f in self.backup_dir.glob("*.zip"):
            stats = f.stat()
            backups.append({
                "name": f.name,
                "size_mb": round(stats.st_size / (1024 * 1024), 2),
                "created": datetime.datetime.fromtimestamp(stats.st_ctime).isoformat()
            })
        
        if not backups:
            return "Nu am găsit niciun backup."
            
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        lines = ["📚 Backup-uri disponibile:"]
        for b in backups:
            lines.append(f"  • {b['name']} ({b['size_mb']} MB) - {b['created']}")
        return "\n".join(lines)
