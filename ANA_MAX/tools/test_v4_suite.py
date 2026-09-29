"""
ANA Ultrafast Web Executor v4 — Automated Test Suite
=====================================================
Runs all 4 tests defined in the system prompt spec.
"""
import json, sys, subprocess
from pathlib import Path

PYTHON = str(Path(__file__).parent.parent / "venv" / "Scripts" / "python.exe")
AGENT = str(Path(__file__).parent / "ana_ultrafast_web_executor_v4.py")

def run(goal, start_url, steps, test_name):
    print(f"\n{'='*60}")
    print(f"  TEST: {test_name}")
    print(f"{'='*60}")
    result = subprocess.run(
        [PYTHON, AGENT, "--goal", goal, "--start_url", start_url, "--steps", json.dumps(steps), "--headless"],
        capture_output=False, text=True
    )
    return result.returncode == 0

results = {}

# TEST 1 — Basic Navigation + Extract
results["T1_basic_navigation"] = run(
    goal="Open Wikipedia and extract AGI definition",
    start_url="https://www.wikipedia.org",
    steps=["Search for Artificial General Intelligence", "Open the first article", "Extract the first paragraph"],
    test_name="T1 — Basic Navigation + Extract"
)

# TEST 2 — Screenshot Fallback (DOM-sparse page)
results["T2_screenshot_fallback"] = run(
    goal="Extract text from minimal page",
    start_url="https://example.com",
    steps=["Extract the first paragraph"],
    test_name="T2 — Screenshot Fallback (minimal DOM)"
)

# TEST 3 — Self-Healing (navigate + back + repeat)
results["T3_self_healing"] = run(
    goal="Test self-healing navigate back and repeat",
    start_url="https://www.wikipedia.org",
    steps=["Search for Artificial General Intelligence", "Open the first article", "Navigate back", "Repeat the search"],
    test_name="T3 — Self-Healing + Repeat Search"
)

# TEST 4 — Full Flow (real web, Google Flights)
results["T4_full_flow"] = run(
    goal="Find flights from Zurich to London",
    start_url="https://www.google.com/travel/flights?hl=en",
    steps=["Search ZRH to LHR", "Extract price"],
    test_name="T4 — Full Flow (Google Flights)"
)

print("\n" + "="*60)
print("  TEST SUITE RESULTS")
print("="*60)
for name, passed in results.items():
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}")
print("="*60)
passed = sum(results.values())
print(f"  {passed}/{len(results)} tests passed")
