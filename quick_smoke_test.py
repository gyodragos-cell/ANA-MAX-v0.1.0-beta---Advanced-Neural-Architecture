import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("Simple Smoke Test\n")

# Test 1: Config
try:
    from core.config import Config
    config = Config()
    print("[PASS] Config loaded")
except Exception as e:
    print(f"[FAIL] Config: {e}")

# Test 2: Tools
try:
    from tools.base import registry
    print(f"[PASS] Tools registry OK ({len(registry.list_tools())} tools)")
except Exception as e:
    print(f"[FAIL] Tools: {e}")

# Test 3: SQLite
try:
    import sqlite3
    from pathlib import Path
    db_path = Path("memory/ana_max_brain.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        print(f"[PASS] SQLite OK ({len(tables)} tables)")
    else:
        print("[FAIL] SQLite DB not found")
except Exception as e:
    print(f"[FAIL] SQLite: {e}")

# Test 4: Vector Memory
try:
    from core.vector_memory import VectorMemoryCortex
    vm = VectorMemoryCortex(db_path="memory/test_quick.db")
    vm.store("Test memory", "test", tags=["test"])
    results = vm.search("test", top_k=1)
    vm.close()
    Path("memory/test_quick.db").unlink(missing_ok=True)
    print(f"[PASS] Vector Memory OK ({len(results)} results)")
except Exception as e:
    print(f"[FAIL] Vector Memory: {e}")

# Test 5: Swarm
try:
    from core.advanced_swarm import AdvancedSwarmOrchestrator, Topology
    swarm = AdvancedSwarmOrchestrator()
    status = swarm.get_swarm_status()
    swarm.close()
    print(f"[PASS] Swarm OK ({status['total_agents']} agents)")
except Exception as e:
    print(f"[FAIL] Swarm: {e}")

print("\nAll critical tests completed!")
