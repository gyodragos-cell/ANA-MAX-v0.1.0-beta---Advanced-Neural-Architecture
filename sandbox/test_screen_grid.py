"""
OS-27 Phase 3 — Screen Grid Smoke Test
Ruleaza direct din terminalul tau Windows.
"""
import sys
import os

# Path setup
ANA_MAX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ANA_MAX")
sys.path.insert(0, ANA_MAX)

import time
import logging
logging.basicConfig(level=logging.WARNING, format='%(name)s: %(message)s')

print("=" * 50)
print(" OS-27 Screen Grid Smoke Test (Phase 3)")
print("=" * 50)

# Step 1: Check PaddleOCR
print("\n[1/3] Checking OCR engine...")
from tools.ocr_tool import _check_engine
eng = _check_engine()
print(f"      Backend: {eng.get('backend', 'N/A')}")
print(f"      Status : {eng.get('status')}")

# Step 2: Screenshot + OCR grid
print("\n[2/3] Running screenshot + OCR grid...")
from tools.screen_grid import _get_screen_grid_with_coords, _format_grid_for_llm

start = time.time()
data = _get_screen_grid_with_coords()
elapsed = round(time.time() - start, 2)

if data['status'] != 'success':
    print(f"      [FAIL] {data.get('error')}")
    sys.exit(1)

print(f"      [OK] Backend   : {data['backend']}")
print(f"      [OK] Resolution: {data['screen_w']}x{data['screen_h']}")
print(f"      [OK] Elements  : {data['element_count']}")
print(f"      [OK] Time      : {elapsed}s")

# Step 3: First 5 elements
print("\n[3/3] Sample elements (first 5):")
for item in data['grid'][:5]:
    print(f"      '{item['text'][:30]}' -> X={item['x']}, Y={item['y']} (conf={item['confidence']})")

# Step 4: LLM formatted output
print("\n--- LLM Grid (top 10) ---")
print(_format_grid_for_llm(data, top_n=10))

print("\n[ALL TESTS PASSED] screen_grid Tool functional!")
