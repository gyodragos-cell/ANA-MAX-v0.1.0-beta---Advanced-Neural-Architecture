"""
ANA MAX - Project Audit & Cleanup Strategy
=========================================
Audit complet pentru ana-manus si ana_dev (2 GB total)
Identifica ce pastrezi, ce arunci, ce repara
"""

import os
import json
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectAuditor:
    """Auditor complet pentru proiecte ANA."""
    
    def __init__(self):
        self.ana_manus = Path(r"C:\Users\billy\Desktop\ana-manus")
        self.ana_dev = Path(r"C:\Users\billy\Desktop\ana_dev")
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "audit_phase": "complete_audit",
            "projects": {},
            "duplicates": [],
            "large_files": [],
            "unused_files": [],
            "errors": [],
            "recommendations": []
        }
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Ruleaza audit complet."""
        print(f"\n{'='*80}")
        print(f"ANA PROJECT AUDIT - STRATEGIE CURATARE")
        print(f"Analyzing: ana-manus + ana_dev (2 GB total)")
        print(f"{'='*80}\n")
        
        # Audit ana-manus
        if self.ana_manus.exists():
            print("Auditing ana-manus...")
            self.results["projects"]["ana_manus"] = self._audit_project(self.ana_manus)
        else:
            print("❌ ana-manus not found")
        
        # Audit ana-dev
        if self.ana_dev.exists():
            print("Auditing ana-dev...")
            self.results["projects"]["ana_dev"] = self._audit_project(self.ana_dev)
        else:
            print("❌ ana-dev not found")
        
        # Identifica duplicate
        print("\nIdentifying duplicates...")
        self._find_duplicates()
        
        # Identifica fisiere mari
        print("Finding large files...")
        self._find_large_files()
        
        # Genereaza strategie
        print("\nGenerating cleanup strategy...")
        self._generate_strategy()
        
        # Save results
        self._save_results()
        
        return self.results
    
    def _audit_project(self, project_path: Path) -> Dict[str, Any]:
        """Audit unui proiect."""
        project_data = {
            "path": str(project_path),
            "size_mb": 0,
            "file_count": 0,
            "directory_count": 0,
            "by_type": defaultdict(int),
            "structure": {},
            "errors": []
        }
        
        try:
            # Calculeaza dimensiune totala
            total_size = 0
            file_count = 0
            dir_count = 0
            
            exclude_dirs = {
                "venv", "venv_corrupted", "__pycache__", ".git",
                "node_modules", "archives", "sandbox", "logs"
            }
            
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                dir_count += 1
                
                for file in files:
                    file_path = Path(root) / file
                    try:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_count += 1
                        
                        file_ext = file_path.suffix.lower()
                        project_data["by_type"][file_ext] += 1
                        
                    except Exception as e:
                        project_data["errors"].append(str(file_path))
            
            project_data["size_mb"] = total_size / 1024 / 1024
            project_data["file_count"] = file_count
            project_data["directory_count"] = dir_count
            
            print(f"✅ {project_path.name}: {project_data['size_mb']:.2f} MB, {file_count} files")
            
        except Exception as e:
            project_data["errors"].append(f"Audit failed: {e}")
            print(f"❌ Audit failed for {project_path.name}: {e}")
        
        return project_data
    
    def _find_duplicates(self):
        """Gaseste fisiere duplicate."""
        file_hashes = defaultdict(list)
        
        # Hash files din ambele proiecte
        for project_path in [self.ana_manus, self.ana_dev]:
            if not project_path.exists():
                continue
            
            for root, dirs, files in os.walk(project_path):
                exclude_dirs = {"venv", "venv_corrupted", "__pycache__", ".git", "node_modules"}
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    try:
                        file_hash = self._hash_file(file_path)
                        file_hashes[file_hash].append(str(file_path))
                    except Exception:
                        continue
        
        # Identifica duplicate
        for file_hash, paths in file_hashes.items():
            if len(paths) > 1:
                self.results["duplicates"].append({
                    "hash": file_hash,
                    "paths": paths,
                    "count": len(paths)
                })
        
        print(f"✅ Found {len(self.results['duplicates'])} duplicate groups")
    
    def _hash_file(self, file_path: Path) -> str:
        """Calculeaza hash fisier."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _find_large_files(self):
        """Gaseste fisiere mari (> 10 MB)."""
        threshold_mb = 10
        
        for project_path in [self.ana_manus, self.ana_dev]:
            if not project_path.exists():
                continue
            
            for root, dirs, files in os.walk(project_path):
                exclude_dirs = {"venv", "venv_corrupted", "__pycache__", ".git", "node_modules"}
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    try:
                        size_mb = file_path.stat().st_size / 1024 / 1024
                        if size_mb > threshold_mb:
                            self.results["large_files"].append({
                                "path": str(file_path),
                                "size_mb": size_mb
                            })
                    except Exception:
                        continue
        
        print(f"✅ Found {len(self.results['large_files'])} large files (>10 MB)")
    
    def _generate_strategy(self):
        """Genereaza strategie de curatare."""
        print("\n📋 STRATEGIE DE CURATARE:")
        
        # 1. Analyzeaza dimensiune
        total_size = 0
        for project_name, project_data in self.results["projects"].items():
            total_size += project_data.get("size_mb", 0)
        
        print(f"Total size: {total_size:.2f} MB")
        
        # 2. Recomandari duplicate
        if self.results["duplicates"]:
            space_saving = 0
            for dup in self.results["duplicates"]:
                for path in dup["paths"][1:]:  # Exclude original
                    try:
                        space_saving += Path(path).stat().st_size
                    except:
                        pass
            
            self.results["recommendations"].append({
                "action": "REMOVE_DUPLICATES",
                "description": f"Remove {len(self.results['duplicates'])} duplicate groups",
                "space_saving_mb": space_saving / 1024 / 1024,
                "priority": "HIGH"
            })
            print(f"   🔴 HIGH: Remove duplicates ({space_saving / 1024 / 1024:.2f} MB)")
        
        # 3. Recomandari fisiere mari
        if self.results["large_files"]:
            large_space = sum(f["size_mb"] for f in self.results["large_files"])
            self.results["recommendations"].append({
                "action": "REVIEW_LARGE_FILES",
                "description": f"Review {len(self.results['large_files'])} large files",
                "space_saving_mb": large_space,
                "priority": "MEDIUM"
            })
            print(f"   🟡 MEDIUM: Review large files ({large_space:.2f} MB)")
        
        # 4. Recomandari directoare neutilizate
        unused_dirs = ["venv", "venv_corrupted", "archives", "sandbox"]
        for project_path in [self.ana_manus, self.ana_dev]:
            if not project_path.exists():
                continue
            
            for dir_name in unused_dirs:
                dir_path = project_path / dir_name
                if dir_path.exists():
                    dir_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                    self.results["recommendations"].append({
                        "action": "REMOVE_UNUSED_DIR",
                        "description": f"Remove {dir_name}",
                        "space_saving_mb": dir_size / 1024 / 1024,
                        "priority": "LOW"
                    })
                    print(f"   🟢 LOW: Remove {dir_name} ({dir_size / 1024 / 1024:.2f} MB)")
        
        # 5. Total potential saving
        total_saving = sum(r["space_saving_mb"] for r in self.results["recommendations"])
        print(f"\n💰 TOTAL POTENTIAL SAVING: {total_saving:.2f} MB")
        
        if total_saving > 500:
            print(f"   ✅ Strategie eficienta - poti salva {total_saving:.2f} MB")
        elif total_saving > 100:
            print(f"   ⚠️ Strategie moderata - poti salva {total_saving:.2f} MB")
        else:
            print(f"   ℹ️ Strategie limitata - doar {total_saving:.2f} MB")
    
    def _save_results(self):
        """Salveaza rezultatele."""
        output_file = Path("project_audit_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✅ Audit results saved: {output_file.absolute()}")
        print("Trimite-mi acest fisier pentru analiza detaliata!")


def main():
    """Main function."""
    auditor = ProjectAuditor()
    results = auditor.run_full_audit()
    
    print(f"\n{'='*80}")
    print("✅ AUDIT COMPLET")
    print("Verifica project_audit_results.json pentru detalii")
    print("Trimite-mi rezultatele pentru strategie personalizata!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
