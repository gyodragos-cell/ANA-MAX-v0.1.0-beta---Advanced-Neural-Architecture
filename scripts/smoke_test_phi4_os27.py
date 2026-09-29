#!/usr/bin/env python3
"""
Smoke Test for ANA MAX Phi-4 OS27
==================================
Quick verification that the system is working correctly.
"""

import os
import sys
import subprocess
import requests
import time

def test_foundry_server():
    """Test Foundry server is running"""
    print("[1/5] Testing Foundry server...")
    try:
        result = subprocess.run(
            ["foundry", "server", "status"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=5
        )
        if result.returncode == 0 and result.stdout and "Ready" in result.stdout:
            print("[OK] Foundry server is running")
            return True
        else:
            print("[FAIL] Foundry server not ready")
            return False
    except Exception as e:
        print(f"[FAIL] Foundry server check failed: {e}")
        return False

def test_foundry_model():
    """Test Phi-4-mini model is available"""
    print("[2/5] Testing Phi-4-mini model...")
    try:
        result = subprocess.run(
            ["foundry", "model", "list", "--cached"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )
        if result.stdout and "phi-4-mini" in result.stdout.lower():
            print("[OK] Phi-4-mini is available")
            return True
        else:
            print("[FAIL] Phi-4-mini not found")
            return False
    except Exception as e:
        print(f"[FAIL] Model check failed: {e}")
        return False

def test_ana_max_health():
    """Test ANA MAX health endpoint"""
    print("[3/5] Testing ANA MAX health endpoint...")
    try:
        response = requests.get("http://127.0.0.1:8767/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "online":
                print(f"[OK] ANA MAX is online (backend: {data.get('active_backend')}, model: {data.get('active_model')})")
                return True
            else:
                print(f"[FAIL] ANA MAX status: {data.get('status')}")
                return False
        else:
            print(f"[FAIL] ANA MAX returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Health endpoint check failed: {e}")
        return False

def test_ana_max_tools():
    """Test ANA MAX tools endpoint"""
    print("[4/5] Testing ANA MAX tools...")
    try:
        response = requests.get("http://127.0.0.1:8767/tools", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tool_count = len(data.get("tools", []))
            print(f"[OK] ANA MAX has {tool_count} tools available")
            return True
        else:
            print(f"[FAIL] Tools endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Tools check failed: {e}")
        return False

def test_ana_max_chat():
    """Test ANA MAX chat endpoint"""
    print("[5/5] Testing ANA MAX chat endpoint...")
    try:
        response = requests.post(
            "http://127.0.0.1:8767/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ana.chat",
                "params": {"message": "hello"}
            },
            timeout=30
        )
        if response.status_code == 200:
            print("[OK] ANA MAX chat endpoint responded")
            return True
        else:
            print(f"[FAIL] Chat endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Chat check failed: {e}")
        return False

def main():
    """Run all smoke tests"""
    print("=" * 60)
    print("SMOKE TEST: ANA MAX Phi-4 OS27")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Foundry Server", test_foundry_server()))
    results.append(("Phi-4-mini Model", test_foundry_model()))
    results.append(("ANA MAX Health", test_ana_max_health()))
    results.append(("ANA MAX Tools", test_ana_max_tools()))
    results.append(("ANA MAX Chat", test_ana_max_chat()))
    
    print()
    print("=" * 60)
    print("SMOKE TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("SUCCESS: All systems operational!")
        return 0
    else:
        print()
        print("WARNING: Some tests failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
