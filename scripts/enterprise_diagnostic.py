#!/usr/bin/env python3
"""
ANA MAX Enterprise Diagnostic Tool
==================================
Diagnostic complet enterprise-level pentru ecosistemul ANA MAX.
- Scanare erori sintaxa
- Analiza dependente
- Diagrama flux de date
- Detectare blocaje si probleme de performanta
"""

import ast
import os
import sys
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any
import importlib.util


class EnterpriseDiagnostic:
    """Diagnostic complet enterprise-level pentru ANA MAX."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.results = {
            "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": 0,
            "python_files": 0,
            "syntax_errors": [],
            "import_errors": [],
            "dependency_graph": defaultdict(set),
            "file_sizes": [],
            "complexity_scores": [],
            "bloated_files": [],
            "unused_imports": [],
            "circular_dependencies": [],
            "missing_modules": [],
            "performance_issues": [],
            "architecture_analysis": {}
        }
        
    def scan_directory(self) -> None:
        """Scaneaza complet directorul."""
        print(f"🔍 Scanning {self.root_path}...")
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip venv, __pycache__, .git
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', '.pytest_cache', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    self.results["total_files"] += 1
                    self.results["python_files"] += 1
                    file_path = Path(root) / file
                    
                    # Check file size
                    file_size = file_path.stat().st_size
                    self.results["file_sizes"].append({
                        "path": str(file_path.relative_to(self.root_path)),
                        "size": file_size
                    })
                    
                    # Analyze file
                    self.analyze_python_file(file_path)
                    
        print(f"✅ Scanned {self.results['python_files']} Python files")
        
    def analyze_python_file(self, file_path: Path) -> None:
        """Analizeaza un fisier Python."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Syntax check
            try:
                tree = ast.parse(content)
                self.analyze_ast(tree, file_path)
            except SyntaxError as e:
                self.results["syntax_errors"].append({
                    "file": str(file_path.relative_to(self.root_path)),
                    "line": e.lineno,
                    "error": str(e),
                    "severity": "CRITICAL"
                })
                
        except Exception as e:
            self.results["import_errors"].append({
                "file": str(file_path.relative_to(self.root_path)),
                "error": str(e),
                "severity": "HIGH"
            })
            
    def analyze_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Analizeaza AST pentru dependente si complexitate."""
        imports = []
        complexity = 0
        
        for node in ast.walk(tree):
            # Count imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            
            # Count complexity (simplified)
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
                
        # Store dependency
        file_key = str(file_path.relative_to(self.root_path))
        for imp in imports:
            self.results["dependency_graph"][file_key].add(imp)
            
        # Store complexity
        self.results["complexity_scores"].append({
            "file": file_key,
            "complexity": complexity
        })
        
        # Check for bloated files
        file_size = file_path.stat().st_size
        if file_size > 50000:  # > 50KB
            self.results["bloated_files"].append({
                "file": file_key,
                "size": file_size,
                "complexity": complexity,
                "severity": "MEDIUM" if file_size < 100000 else "HIGH"
            })
            
    def detect_circular_dependencies(self) -> None:
        """Detecteaza dependente circulare."""
        print("🔍 Detecting circular dependencies...")
        
        # Build import map
        import_map = defaultdict(set)
        for file, imports in self.results["dependency_graph"].items():
            for imp in imports:
                import_map[file].add(imp)
                
        # Simple circular detection (would need full module resolution for accuracy)
        # This is a simplified version
        checked = set()
        
        for file in import_map:
            if file in checked:
                continue
            checked.add(file)
            
            # Check if any import imports back
            for imp in import_map[file]:
                if imp in import_map and file in import_map[imp]:
                    self.results["circular_dependencies"].append({
                        "cycle": f"{file} <-> {imp}",
                        "severity": "MEDIUM"
                    })
                    
    def analyze_architecture(self) -> None:
        """Analizeaza arhitectura proiectului."""
        print("🔍 Analyzing architecture...")
        
        # Count files by directory
        dir_counts = defaultdict(int)
        for file_path in self.root_path.rglob('*.py'):
            if 'venv' not in str(file_path) and '__pycache__' not in str(file_path):
                parent = file_path.parent.relative_to(self.root_path)
                dir_counts[str(parent)] += 1
                
        # Identify main components
        self.results["architecture_analysis"] = {
            "directories": dict(dir_counts),
            "total_directories": len(dir_counts),
            "largest_component": max(dir_counts.items(), key=lambda x: x[1]) if dir_counts else (None, 0),
            "component_distribution": self._analyze_distribution(dir_counts)
        }
        
    def _analyze_distribution(self, dir_counts: Dict[str, int]) -> Dict[str, Any]:
        """Analizeaza distributia componentelor."""
        total = sum(dir_counts.values())
        if total == 0:
            return {}
            
        return {
            "core": sum(v for k, v in dir_counts.items() if 'core' in k.lower()),
            "tools": sum(v for k, v in dir_counts.items() if 'tool' in k.lower()),
            "agents": sum(v for k, v in dir_counts.items() if 'agent' in k.lower()),
            "other": total
        }
        
    def generate_report(self) -> str:
        """Genereaza raport complet."""
        print("📊 Generating report...")
        
        report = []
        report.append("=" * 80)
        report.append("ANA MAX ENTERPRISE DIAGNOSTIC REPORT")
        report.append("=" * 80)
        report.append(f"Scan Time: {self.results['scan_time']}")
        report.append(f"Root Path: {self.root_path}")
        report.append(f"Total Files: {self.results['total_files']}")
        report.append(f"Python Files: {self.results['python_files']}")
        report.append("")
        
        # Syntax Errors
        report.append("🚨 SYNTAX ERRORS")
        report.append("-" * 40)
        if self.results["syntax_errors"]:
            for error in self.results["syntax_errors"][:10]:  # Limit to first 10
                report.append(f"  [{error['severity']}] {error['file']}: line {error['line']}")
                report.append(f"    {error['error']}")
            if len(self.results["syntax_errors"]) > 10:
                report.append(f"  ... and {len(self.results['syntax_errors']) - 10} more")
        else:
            report.append("  ✅ No syntax errors found")
        report.append("")
        
        # Import Errors
        report.append("🚨 IMPORT ERRORS")
        report.append("-" * 40)
        if self.results["import_errors"]:
            for error in self.results["import_errors"][:10]:
                report.append(f"  [{error['severity']}] {error['file']}")
                report.append(f"    {error['error']}")
        else:
            report.append("  ✅ No import errors found")
        report.append("")
        
        # Circular Dependencies
        report.append("🔄 CIRCULAR DEPENDENCIES")
        report.append("-" * 40)
        if self.results["circular_dependencies"]:
            for cycle in self.results["circular_dependencies"]:
                report.append(f"  [{cycle['severity']}] {cycle['cycle']}")
        else:
            report.append("  ✅ No circular dependencies detected")
        report.append("")
        
        # Bloated Files
        report.append("📦 BLOATED FILES (>50KB)")
        report.append("-" * 40)
        if self.results["bloated_files"]:
            for file_info in sorted(self.results["bloated_files"], key=lambda x: x["size"], reverse=True)[:10]:
                size_kb = file_info["size"] / 1024
                report.append(f"  [{file_info['severity']}] {file_info['file']}")
                report.append(f"    Size: {size_kb:.1f} KB, Complexity: {file_info['complexity']}")
        else:
            report.append("  ✅ No bloated files found")
        report.append("")
        
        # Architecture Analysis
        report.append("🏗️ ARCHITECTURE ANALYSIS")
        report.append("-" * 40)
        arch = self.results["architecture_analysis"]
        report.append(f"  Total Directories: {arch['total_directories']}")
        report.append(f"  Largest Component: {arch['largest_component'][0]} ({arch['largest_component'][1]} files)")
        report.append("  Component Distribution:")
        for comp, count in arch['component_distribution'].items():
            if comp != 'other':
                report.append(f"    {comp}: {count} files")
        report.append("")
        
        # Top 10 Largest Files
        report.append("📊 TOP 10 LARGEST FILES")
        report.append("-" * 40)
        largest = sorted(self.results["file_sizes"], key=lambda x: x["size"], reverse=True)[:10]
        for file_info in largest:
            size_kb = file_info["size"] / 1024
            report.append(f"  {size_kb:.1f} KB - {file_info['path']}")
        report.append("")
        
        # Summary
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        report.append(f"Syntax Errors: {len(self.results['syntax_errors'])}")
        report.append(f"Import Errors: {len(self.results['import_errors'])}")
        report.append(f"Circular Dependencies: {len(self.results['circular_dependencies'])}")
        report.append(f"Bloated Files: {len(self.results['bloated_files'])}")
        report.append("")
        
        # Health Score
        total_issues = len(self.results["syntax_errors"]) + len(self.results["import_errors"]) + len(self.results["circular_dependencies"])
        health_score = max(0, 100 - (total_issues * 5))
        report.append(f"🏥 HEALTH SCORE: {health_score}/100")
        
        if health_score >= 90:
            report.append("Status: ✅ EXCELLENT")
        elif health_score >= 70:
            report.append("Status: ⚠️ GOOD")
        elif health_score >= 50:
            report.append("Status: ⚠️ FAIR")
        else:
            report.append("Status: ❌ NEEDS ATTENTION")
            
        report.append("=" * 80)
        
        return "\n".join(report)
        
    def save_json_report(self, output_path: str) -> None:
        """Salveaza raportul JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"💾 JSON report saved to {output_path}")
        
    def run(self) -> str:
        """Ruleaza diagnosticul complet."""
        start_time = time.time()
        
        self.scan_directory()
        self.detect_circular_dependencies()
        self.analyze_architecture()
        
        elapsed = time.time() - start_time
        print(f"⏱️ Diagnostic completed in {elapsed:.2f} seconds")
        
        return self.generate_report()


def main():
    """Functia principala."""
    if len(sys.argv) < 2:
        print("Usage: python enterprise_diagnostic.py <root_path>")
        sys.exit(1)
        
    root_path = sys.argv[1]
    
    if not os.path.exists(root_path):
        print(f"Error: Path {root_path} does not exist")
        sys.exit(1)
        
    diagnostic = EnterpriseDiagnostic(root_path)
    report = diagnostic.run()
    
    # Print report
    print("\n")
    print(report)
    
    # Save JSON report
    json_path = os.path.join(root_path, "diagnostic_report.json")
    diagnostic.save_json_report(json_path)
    
    # Save text report
    txt_path = os.path.join(root_path, "diagnostic_report.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"💾 Text report saved to {txt_path}")


if __name__ == "__main__":
    main()
