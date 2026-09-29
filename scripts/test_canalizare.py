import time
import json
import logging
from pathlib import Path
import sys

# Adaugam ANA_MAX la path
ANA_ROOT = Path(__file__).resolve().parents[1] / "ANA_MAX"
if str(ANA_ROOT) not in sys.path:
    sys.path.insert(0, str(ANA_ROOT))

from core.memory_cortex import get_memory_cortex
from tools.watchdog_bus import bus

def test_canalizare():
    print("=== TEST CANALIZARE ENTERPRISE OS-27 ===")
    
    # 1. Test Bus
    print("\n1. Test Watchdog Bus...")
    try:
        bus.start()
        bus.publish("test_source", "test_event", {"message": "Salut din scriptul de test!"})
        print(" [OK] Bus publish reusit.")
    except Exception as e:
        print(f" [FAIL] Bus error: {e}")

    # 2. Test Memory Cortex -> Bus Link
    print("\n2. Test Memory Cortex -> Bus Link...")
    try:
        memory = get_memory_cortex()
        # Inregistram un eveniment care ar trebui sa apara pe bus
        memory.record_event("enterprise_test", {"status": "success", "engineer": "Manus"})
        print(" [OK] Memory event recorded si publicat pe bus.")
    except Exception as e:
        print(f" [FAIL] Memory error: {e}")

    # 3. Test Dashboard Feeder (System Telemetry)
    print("\n3. Test Dashboard Feeder Simulation...")
    try:
        bus.publish("dashboard_feeder", "telemetry.system", {
            "cpu_percent": 42,
            "memory_percent": 69,
            "disk_usage": 15
        })
        print(" [OK] Telemetrie simulata trimisa pe bus.")
    except Exception as e:
        print(f" [FAIL] Feeder simulation error: {e}")

    print("\n=== TEST FINALIZAT ===")
    print("Verifica Dashboard-ul (:8766/dashboard sau :8767/dashboard) pentru a vedea rezultatele live!")

if __name__ == "__main__":
    test_canalizare()
