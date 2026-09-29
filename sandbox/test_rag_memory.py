"""
OS-27 Phase 2 — CPU RAG Episodic Memory Test
Ruleaza acest script pentru a verifica viteza si calitatea cautarii BM25.
"""

import os
import sys
import time

ANA_MAX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ANA_MAX")
sys.path.insert(0, ANA_MAX)

from core.memory_cortex import ANAMemoryCortex

print("=" * 50)
print(" OS-27 Episodic Memory RAG Test (Phase 2)")
print("=" * 50)

cortex = ANAMemoryCortex()

# 1. Inject some fake logs for testing BM25
print("\n[1/3] Injecting test events...")
cortex.record_event("tool_error", {"error": "Failed to compile C++ bindings for DXCam due to missing VS Build Tools."})
cortex.record_event("action", {"desc": "User asked to optimize the screen_grid parsing."})
cortex.record_event("tool_error", {"error": "EventStream.emit() got an unexpected keyword argument 'event'"})
cortex.record_event("telemetry", {"ram": "99.3%", "cpu": "100%"})

# 2. Test Linear Fallback (empty query)
print("\n[2/3] Fetching recent errors (Linear Fallback)...")
start = time.time()
recent_errors = cortex.get_recent_errors(limit=2)
print(f"      Got {len(recent_errors)} errors in {round((time.time() - start)*1000, 2)}ms")
for e in recent_errors:
    print(f"      - {e.get('data', {}).get('error', '')[:60]}...")

# 3. Test RAG Search (BM25)
query = "unexpected keyword argument eventstream"
print(f"\n[3/3] Testing RAG Search (Query: '{query}')...")
start = time.time()
rag_results = cortex.query_memory(query, type="tool_error", top_k=2)
elapsed = round((time.time() - start)*1000, 2)
print(f"      Search completed in {elapsed}ms")

if rag_results:
    print(f"      [OK] BM25 found best match:")
    for i, res in enumerate(rag_results):
        data = res.get("data", {})
        print(f"      {i+1}. Source: {res.get('source')} | Match: {str(data)[:100]}...")
else:
    print("      [FAIL] No matches found via RAG.")

print("\n[ALL TESTS FINISHED]")
