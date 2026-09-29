"""
Test Script for Black Mesa Tools
"""
import sys
import time
import json
from pathlib import Path

# Adauga workspace root in path
workspace = Path(r"c:\Users\billy\Desktop\ana-manus")
sys.path.insert(0, str(workspace / "ANA_MAX"))

from tools.base import registry
from tools.latent_telepathy_tool import LatentTelepathyTool
from tools.temporal_branching_tool import TemporalBranchingTool
from tools.polymorphic_core_tool import PolymorphicCoreTool
from tools.win32_telepathy_tool import Win32TelepathyTool

# Register tools
registry.register(LatentTelepathyTool())
registry.register(TemporalBranchingTool())
registry.register(PolymorphicCoreTool())
registry.register(Win32TelepathyTool())

print("\n=== BLACK MESA PROTOCOLS TESTS ===")

# 1. Latent Telepathy
print("\n[1] Testing Latent Telepathy...")
payload = json.dumps({"agent_id": "nexus-1", "mission": "pentest", "target": "10.0.0.5"})
res_enc = registry.execute("latent_telepathy", action="encode", payload=payload)
if res_enc.is_success:
    encoded = res_enc.data['latent_vector']
    print(f"  Encoded: {encoded[:30]}... (Ratio: {res_enc.data['compression_ratio']})")
    res_dec = registry.execute("latent_telepathy", action="decode", payload=encoded)
    print(f"  Decoded: {res_dec.data['decoded_state']}")
else:
    print("  Failed:", res_enc.error)

# 2. Temporal Branching
print("\n[2] Testing Temporal Branching...")
res_freeze = registry.execute("temporal_branch", action="freeze_time")
if res_freeze.is_success:
    branch = res_freeze.data['branch_id']
    print(f"  Frozen Time at Branch: {branch}")
    # Simulam timp care trece... si un rollback
    time.sleep(1)
    res_rollback = registry.execute("temporal_branch", action="rollback", branch_id=branch)
    print(f"  Rollback Status: {res_rollback.is_success}, Restored to: {res_rollback.data.get('restored_to')}")
else:
    print("  Failed:", res_freeze.error)

# 3. Polymorphic Core
print("\n[3] Testing Polymorphic Core (Self-Rewriting)...")
res_test1 = registry.execute("polymorphic_core", action="test")
print(f"  Initial State: {res_test1.data.get('current_state')}")

res_mut = registry.execute("polymorphic_core", action="mutate", new_return_value="REWRITTEN_BY_AI")
print(f"  Mutate Status: {res_mut.is_success}")

res_test2 = registry.execute("polymorphic_core", action="test")
print(f"  New State: {res_test2.data.get('current_state')}")

# Resetam polimorfismul inapoi pentru viitor
registry.execute("polymorphic_core", action="mutate", new_return_value="INITIAL_STATE")

# 4. Win32 Telepathy
print("\n[4] Testing Win32 Telepathy...")
import subprocess
# Open notepad hidden/in background for a second
p = subprocess.Popen(["notepad.exe"])
time.sleep(1) # wait for window to spawn

res_win32 = registry.execute("win32_telepathy", window_title="Notepad", text_payload="Hello from Telepathy!")
if res_win32.is_success:
    print(f"  Injected successfully into HWND: {res_win32.data.get('target_hwnd')}")
else:
    print(f"  Failed: {res_win32.error}")

# Cleanup notepad
p.terminate()

print("\n=== TESTS COMPLETE ===")
