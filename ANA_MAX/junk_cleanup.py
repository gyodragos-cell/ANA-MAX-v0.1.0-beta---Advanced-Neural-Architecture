"""
ANA MAX - Junk Cleanup Tool
==========================
Curata "gomot" si "fiierele monstru" - fisiere descarcate, models, voice
Identifica ce incetineste agentul si ce poate fi sters
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JunkCleaner:
    """Cleaner pentru junk si fisiere descarcate."""
    
    def __init__(self):
        self.ana_manus = Path(r"C:\Users\billy\Desktop\ana-manus")
        self.ana_dev = Path(r"C:\Users\billy\Desktop\ana_dev")
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "cleanup_phase": "junk_removal",
            "found_junk": [],
            "large_downloads": [],
            "voice_files": [],
            "model_files": [],
            "archive_files": [],
            "total_junk_size_mb": 0,
            "recommendations": []
        }
    
    def run_cleanup_audit(self) -> Dict[str, Any]:
        """Ruleaza audit junk."""
        print(f"\n{'='*80}")
        print(f"ANA JUNK CLEANUP - GOMOT & FIIERELE MONSTRU")
        print(f"Identifying: descarcari, models, voice, archives")
        print(f"{'='*80}\n")
        
        # Scan pentru fisiere suspecte
        for project_path in [self.ana_manus, self.ana_dev]:
            if not project_path.exists():
                continue
            
            print(f"Scanning {project_path.name}...")
            self._scan_project(project_path)
        
        # Categorizeaza junk
        print("\nCategorizing junk...")
        self._categorize_junk()
        
        # Genereaza strategie
        print("\nGenerating cleanup strategy...")
        self._generate_cleanup_strategy()
        
        # Save results
        self._save_results()
        
        return self.results
    
    def _scan_project(self, project_path: Path):
        """Scaneaza proiect pentru junk."""
        
        # Pattern-uri suspecte
        suspicious_patterns = {
            "model": [".gguf", ".bin", ".safetensors", ".onnx", ".pt", ".pth"],
            "voice": [".wav", ".mp3", ".ogg", ".flac", ".m4a"],
            "archive": [".zip", ".tar", ".gz", ".rar", ".7z"],
            "download": ["download", "temp", "cache", "model_", "voice_"]
        }
        
        exclude_dirs = {
            "venv", "venv_corrupted", "__pycache__", ".git", 
            "node_modules", "logs"
        }
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()
                file_name_lower = file.lower()
                
                try:
                    file_size_mb = file_path.stat().st_size / 1024 / 1024
                    
                    # Model files
                    if file_ext in suspicious_patterns["model"]:
                        self.results["model_files"].append({
                            "path": str(file_path),
                            "size_mb": file_size_mb,
                            "type": "model"
                        })
                    
                    # Voice files
                    elif file_ext in suspicious_patterns["voice"]:
                        self.results["voice_files"].append({
                            "path": str(file_path),
                            "size_mb": file_size_mb,
                            "type": "voice"
                        })
                    
                    # Archive files
                    elif file_ext in suspicious_patterns["archive"]:
                        self.results["archive_files"].append({
                            "path": str(file_path),
                            "size_mb": file_size_mb,
                            "type": "archive"
                        })
                    
                    # Download directories
                    elif any(pattern in file_name_lower for pattern in suspicious_patterns["download"]):
                        self.results["large_downloads"].append({
                            "path": str(file_path),
                            "size_mb": file_size_mb,
                            "type": "download"
                        })
                    
                    # Fisiere mari (> 5 MB) care nu sunt Python/JSON/MD
                    elif file_size_mb > 5 and file_ext not in [".py", ".json", ".md", ".yaml", ".yml", ".txt"]:
                        self.results["found_junk"].append({
                            "path": str(file_path),
                            "size_mb": file_size_mb,
                            "type": "large_file"
                        })
                        
                except Exception as e:
                    continue
    
    def _categorize_junk(self):
        """Categorizeaza junk."""
        total_size = 0
        
        # Calculate total junk size
        for category in ["model_files", "voice_files", "archive_files", "large_downloads", "found_junk"]:
            for item in self.results[category]:
                total_size += item["size_mb"]
        
        self.results["total_junk_size_mb"] = total_size
        
        print(f"Found junk: {total_size:.2f} MB")
        print(f"  Model files: {len(self.results['model_files'])}")
        print(f"  Voice files: {len(self.results['voice_files'])}")
        print(f"  Archive files: {len(self.results['archive_files'])}")
        print(f"  Download files: {len(self.results['large_downloads'])}")
        print(f"  Large unknown files: {len(self.results['found_junk'])}")
    
    def _generate_cleanup_strategy(self):
        """Genereaza strategie de curatare."""
        print(f"\n📋 STRATEGIE DE CURATARE:")
        
        # 1. Model files (HIGH - ocupa mult spatiu)
        if self.results["model_files"]:
            model_size = sum(f["size_mb"] for f in self.results["model_files"])
            self.results["recommendations"].append({
                "action": "REMOVE_UNUSED_MODELS",
                "description": f"Remove {len(self.results['model_files'])} model files",
                "space_saving_mb": model_size,
                "priority": "HIGH",
                "reason": "Models ocupa mult spatiu si pot fi redescarcate"
            })
            print(f"   🔴 HIGH: Remove model files ({model_size:.2f} MB)")
            print(f"      → Modelele pot fi redescarcate cand ai nevoie")
        
        # 2. Voice files (MEDIUM - incetinesc agentul)
        if self.results["voice_files"]:
            voice_size = sum(f["size_mb"] for f in self.results["voice_files"])
            self.results["recommendations"].append({
                "action": "REMOVE_VOICE_FILES",
                "description": f"Remove {len(self.results['voice_files'])} voice files",
                "space_saving_mb": voice_size,
                "priority": "MEDIUM",
                "reason": "Voice files incetinesc agentul si 'rad de minte'"
            })
            print(f"   🟡 MEDIUM: Remove voice files ({voice_size:.2f} MB)")
            print(f"      → Voice files incetinesc agentul semnificativ")
        
        # 3. Archive files (LOW - pot fi utile)
        if self.results["archive_files"]:
            archive_size = sum(f["size_mb"] for f in self.results["archive_files"])
            self.results["recommendations"].append({
                "action": "REVIEW_ARCHIVES",
                "description": f"Review {len(self.results['archive_files'])} archive files",
                "space_saving_mb": archive_size,
                "priority": "LOW",
                "reason": "Arhivele pot contine backup-uri importante"
            })
            print(f"   🟢 LOW: Review archive files ({archive_size:.2f} MB)")
            print(f"      → Verifica daca sunt backup-uri importante")
        
        # 4. Download files (HIGH - temporare)
        if self.results["large_downloads"]:
            download_size = sum(f["size_mb"] for f in self.results["large_downloads"])
            self.results["recommendations"].append({
                "action": "REMOVE_DOWNLOADS",
                "description": f"Remove {len(self.results['large_downloads'])} download files",
                "space_saving_mb": download_size,
                "priority": "HIGH",
                "reason": "Download files sunt temporare"
            })
            print(f"   🔴 HIGH: Remove download files ({download_size:.2f} MB)")
            print(f"      → Download files sunt temporare si pot fi sterse")
        
        # 5. Large unknown files (MEDIUM - investigare)
        if self.results["found_junk"]:
            junk_size = sum(f["size_mb"] for f in self.results["found_junk"])
            self.results["recommendations"].append({
                "action": "INVESTIGATE_LARGE_FILES",
                "description": f"Investigate {len(self.results['found_junk'])} large unknown files",
                "space_saving_mb": junk_size,
                "priority": "MEDIUM",
                "reason": "Fisiere mari neidentificate necesita investigare"
            })
            print(f"   🟡 MEDIUM: Investigate large unknown files ({junk_size:.2f} MB)")
            print(f"      → Necesita investigare manuala")
        
        # Total potential saving
        total_saving = sum(r["space_saving_mb"] for r in self.results["recommendations"])
        print(f"\n💰 TOTAL POTENTIAL SAVING: {total_saving:.2f} MB")
        
        if total_saving > 100:
            print(f"   ✅ Strategie eficienta - poti salva {total_saving:.2f} MB")
        elif total_saving > 50:
            print(f"   ⚠️ Strategie moderata - poti salva {total_saving:.2f} MB")
        else:
            print(f"   ℹ️ Strategie limitata - doar {total_saving:.2f} MB")
    
    def _save_results(self):
        """Salveaza rezultatele."""
        output_file = Path("junk_cleanup_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✅ Junk cleanup results saved: {output_file.absolute()}")
        print("Trimite-mi acest fisier pentru strategie personalizata!")


def main():
    """Main function."""
    cleaner = JunkCleaner()
    results = cleaner.run_cleanup_audit()
    
    print(f"\n{'='*80}")
    print("✅ JUNK CLEANUP AUDIT COMPLET")
    print("Verifica junk_cleanup_results.json pentru detalii")
    print("Trimite-mi rezultatele pentru curatare automata!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
