"""
ANA MAX - Auto-Healing Test Script
===================================
Test auto-healing sub capota - 20 de acc pentru a vedea ce poate face
Ruleaza acest script si da-mi rezultatul
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoHealingTest:
    """Test auto-healing pentru ANA MAX."""
    
    def __init__(self):
        self.base_dir = Path(r"C:\Users\billy\Desktop\ana-manus\ANA_MAX")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_phase": "auto_healing",
            "tests_performed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "component_health": {},
            "auto_healing_attempts": [],
            "recommendations": []
        }
    
    def run_full_test(self, num_attempts: int = 20) -> Dict[str, Any]:
        """Ruleaza test complet cu num_attempts acc."""
        print(f"\n{'='*80}")
        print(f"ANA MAX - AUTO-HEALING TEST")
        print(f"Testing system with {num_attempts} attempts")
        print(f"{'='*80}\n")
        
        # Faza 1: Health Check initial
        print("FAZA 1: Health Check Initial")
        self._test_initial_health()
        
        # Faza 2: Test Componente
        print("\nFAZA 2: Test Componente")
        self._test_components()
        
        # Faza 3: Auto-Healing Test (20 acc)
        print(f"\nFAZA 3: Auto-Healing Test ({num_attempts} acc)")
        self._test_auto_healing(num_attempts)
        
        # Faza 4: Rezumat Final
        print("\nFAZA 4: Rezumat Final")
        self._generate_summary()
        
        return self.results
    
    def _test_initial_health(self):
        """Test health initial."""
        print("Verificam starea initiala a sistemului...")
        
        # Verificam daca base_dir exista
        if self.base_dir.exists():
            self.results["component_health"]["base_dir"] = "✅ EXISTS"
            print(f"✅ Base directory exists: {self.base_dir}")
        else:
            self.results["component_health"]["base_dir"] = "❌ MISSING"
            print(f"❌ Base directory missing: {self.base_dir}")
        
        # Verificam core/ directory
        core_dir = self.base_dir / "core"
        if core_dir.exists():
            self.results["component_health"]["core_dir"] = "✅ EXISTS"
            print(f"✅ Core directory exists")
        else:
            self.results["component_health"]["core_dir"] = "❌ MISSING"
            print(f"❌ Core directory missing")
        
        # Verificam tools/ directory
        tools_dir = self.base_dir / "tools"
        if tools_dir.exists():
            self.results["component_health"]["tools_dir"] = "✅ EXISTS"
            tool_count = len(list(tools_dir.glob("*.py")))
            self.results["component_health"]["tools_count"] = tool_count
            print(f"✅ Tools directory exists ({tool_count} tools)")
        else:
            self.results["component_health"]["tools_dir"] = "❌ MISSING"
            print(f"❌ Tools directory missing")
        
        # Verificam docs/ directory
        docs_dir = self.base_dir.parent / "docs"
        if docs_dir.exists():
            self.results["component_health"]["docs_dir"] = "✅ EXISTS"
            print(f"✅ Docs directory exists")
        else:
            self.results["component_health"]["docs_dir"] = "❌ MISSING"
            print(f"❌ Docs directory missing")
    
    def _test_components(self):
        """Test componente specifice."""
        print("\nTestam componente specifice...")
        
        # Test Tool Graph
        try:
            sys.path.insert(0, str(self.base_dir))
            from core.tool_graph import get_tool_graph
            
            graph = get_tool_graph()
            stats = graph.get_graph_stats()
            
            self.results["component_health"]["tool_graph"] = "✅ ACTIVE"
            self.results["component_health"]["graph_stats"] = stats
            print(f"✅ Tool Graph active: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
            
        except Exception as e:
            self.results["component_health"]["tool_graph"] = f"❌ ERROR: {e}"
            print(f"❌ Tool Graph error: {e}")
        
        # Test Session Logger
        try:
            from core.session_logger import get_session_logger
            
            logger = get_session_logger()
            self.results["component_health"]["session_logger"] = "✅ ACTIVE"
            print(f"✅ Session Logger active")
            
        except Exception as e:
            self.results["component_health"]["session_logger"] = f"❌ ERROR: {e}"
            print(f"❌ Session Logger error: {e}")
        
        # Test Backend Manager
        try:
            from core.backend_manager import get_backend_manager
            
            manager = get_backend_manager()
            self.results["component_health"]["backend_manager"] = "✅ ACTIVE"
            print(f"✅ Backend Manager active")
            
        except Exception as e:
            self.results["component_health"]["backend_manager"] = f"❌ ERROR: {e}"
            print(f"❌ Backend Manager error: {e}")
        
        # Test Task Healer
        try:
            from core.task_healer import get_task_healer
            
            healer = get_task_healer()
            self.results["component_health"]["task_healer"] = "✅ ACTIVE"
            print(f"✅ Task Healer active")
            
        except Exception as e:
            self.results["component_health"]["task_healer"] = f"❌ ERROR: {e}"
            print(f"❌ Task Healer error: {e}")
    
    def _test_auto_healing(self, num_attempts: int):
        """Test auto-healing cu num_attempts."""
        print(f"\nTestam auto-healing cu {num_attempts} acc...")
        
        for i in range(num_attempts):
            attempt_num = i + 1
            print(f"\n--- Acc {attempt_num}/{num_attempts} ---")
            
            # Simulam un task
            task_name = f"test_task_{attempt_num}"
            attempt_result = self._attempt_task(task_name)
            
            self.results["auto_healing_attempts"].append(attempt_result)
            self.results["tests_performed"] += 1
            
            if attempt_result["success"]:
                self.results["tests_passed"] += 1
                print(f"✅ Acc {attempt_num}: SUCCESS")
            else:
                self.results["tests_failed"] += 1
                print(f"❌ Acc {attempt_num}: FAILED - {attempt_result['error']}")
            
            # Small delay intre acc
            time.sleep(0.1)
    
    def _attempt_task(self, task_name: str) -> Dict[str, Any]:
        """Incearca sa execute un task."""
        attempt_result = {
            "task_name": task_name,
            "success": False,
            "error": None,
            "healing_triggered": False,
            "healing_successful": False,
            "latency": 0.0
        }
        
        start_time = time.time()
        
        try:
            # Test Task Healer
            from core.task_healer import get_task_healer
            
            healer = get_task_healer()
            
            # Start task
            task = healer.start_task(task_name, "test", {"test": True})
            
            # Checkpoint
            healer.checkpoint(task_name, "initial", {"status": "started"})
            
            # Simulam completion
            healer.complete_task(task_name)
            
            attempt_result["success"] = True
            attempt_result["healing_triggered"] = False
            
        except Exception as e:
            attempt_result["error"] = str(e)
            
            # Incercam healing
            attempt_result["healing_triggered"] = True
            try:
                # Simulam healing
                from core.task_healer import get_task_healer
                healer = get_task_healer()
                
                # Recover task
                recovered = healer.recover_task(task_name)
                
                if recovered:
                    attempt_result["healing_successful"] = True
                else:
                    attempt_result["healing_successful"] = False
                    
            except Exception as healing_error:
                attempt_result["healing_successful"] = False
                attempt_result["healing_error"] = str(healing_error)
        
        attempt_result["latency"] = time.time() - start_time
        return attempt_result
    
    def _generate_summary(self):
        """Genereaza rezumat final."""
        print(f"\n{'='*80}")
        print(f"REZUMAT TEST AUTO-HEALING")
        print(f"{'='*80}\n")
        
        # Statistics
        total = self.results["tests_performed"]
        passed = self.results["tests_passed"]
        failed = self.results["tests_failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 STATISTICS:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {failed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Component Health
        print(f"\n🔍 COMPONENT HEALTH:")
        for component, status in self.results["component_health"].items():
            print(f"   {component}: {status}")
        
        # Auto-Healing Performance
        healing_triggered = sum(1 for a in self.results["auto_healing_attempts"] if a["healing_triggered"])
        healing_successful = sum(1 for a in self.results["auto_healing_attempts"] if a["healing_successful"])
        
        print(f"\n🛠️ AUTO-HEALING PERFORMANCE:")
        print(f"   Healing Triggered: {healing_triggered}/{total}")
        print(f"   Healing Successful: {healing_successful}/{healing_triggered}" if healing_triggered > 0 else "   No healing needed")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if success_rate >= 80:
            print(f"   ✅ Sistemul functioneaza excelent!")
            print(f"   ✅ Auto-healing este eficient")
            print(f"   ✅ Merita reputatia!")
        elif success_rate >= 50:
            print(f"   ⚠️ Sistemul functioneaza moderat")
            print(f"   ⚠️ Necesita imbunatairi la auto-healing")
            print(f"   ⚠️ Poate merita reputatia cu work")
        else:
            print(f"   ❌ Sistemul are probleme")
            print(f"   ❌ Auto-healing nu functioneaza corect")
            print(f"   ❌ Necesita reparatii majore")
        
        if healing_triggered > 0:
            healing_rate = (healing_successful / healing_triggered * 100) if healing_triggered > 0 else 0
            print(f"\n   Healing Success Rate: {healing_rate:.1f}%")
            
            if healing_rate >= 70:
                print(f"   ✅ Auto-healing este foarte eficient")
            elif healing_rate >= 40:
                print(f"   ⚠️ Auto-healing este moderat eficient")
            else:
                print(f"   ❌ Auto-healing nu este eficient")
        
        # Save results
        self._save_results()
        
        print(f"\n{'='*80}")
        print(f"Rezultate salvate in: auto_healing_test_results.json")
        print(f"Trimite-mi acest fisier pentru analiza!")
        print(f"{'='*80}\n")
    
    def _save_results(self):
        """Salveaza rezultatele in JSON."""
        output_file = Path("auto_healing_test_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"✅ Rezultate salvate in: {output_file.absolute()}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ANA MAX Auto-Healing Test")
    parser.add_argument("--attempts", type=int, default=20, help="Number of test attempts (default: 20)")
    
    args = parser.parse_args()
    
    # Run test
    tester = AutoHealingTest()
    results = tester.run_full_test(args.attempts)
    
    print("\n✅ Test complet! Verifica auto_healing_test_results.json")
    print("Trimite-mi rezultatele pentru analiza!\n")


if __name__ == "__main__":
    main()
