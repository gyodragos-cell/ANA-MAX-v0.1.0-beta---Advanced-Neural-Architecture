#!/usr/bin/env python3
"""Test atomic-agent safe mode - without breaking existing agents"""

import subprocess
import json
import os
import time

def check_ollama_status():
    """Check if Ollama is running (non-destructive)"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"[INFO] Ollama running: {len(models)} models available")
            return True, models
        return False, []
    except:
        return False, []

def check_ana_status():
    """Check ANA MAX status (non-destructive)"""
    try:
        result = subprocess.run(
            ["python", "ANA_MAX/bridge/direct_bridge.py", "--smoke-test"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=True
        )
        if result.returncode == 0:
            print("[INFO] ANA MAX bridge: Healthy")
            return True
        else:
            print(f"[WARN] ANA MAX bridge: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"[WARN] ANA check failed: {str(e)}")
        return False

def check_atomic_config():
    """Check atomic-agent config without modifying"""
    config_path = os.path.expanduser("~/.atomic-agent/config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        mode = config['localModels']['mode']
        url = config['localModels']['url']
        print(f"[INFO] Atomic config: mode={mode}, url={url}")
        return config
    else:
        print("[WARN] Atomic config not found")
        return None

def safe_test_atomic():
    """Test atomic connectivity without starting it"""
    config = check_atomic_config()
    if config and config['localModels']['mode'] == 'external':
        ollama_ok, models = check_ollama_status()
        if ollama_ok:
            print("[PASS] Atomic can connect to Ollama (external mode)")
            print(f"[INFO] Available models: {[m['name'] for m in models]}")
            return True
        else:
            print("[SKIP] Ollama not running - atomic cannot connect")
            return False
    else:
        print("[SKIP] Atomic not in external mode - won't use Ollama")
        return False

def main():
    print("=" * 70)
    print("SAFE MODE TEST - No agents will be started or modified")
    print("=" * 70)
    
    print("\n1. Checking Ollama status...")
    ollama_ok, models = check_ollama_status()
    
    print("\n2. Checking ANA MAX status...")
    ana_ok = check_ana_status()
    
    print("\n3. Checking Atomic-Agent config...")
    atomic_config = check_atomic_config()
    
    print("\n4. Testing Atomic-Agent connectivity (safe)...")
    atomic_ready = safe_test_atomic()
    
    print("\n" + "=" * 70)
    print("SAFE TEST SUMMARY")
    print("=" * 70)
    print(f"Ollama: {'[RUNNING]' if ollama_ok else '[STOPPED]'}")
    print(f"ANA MAX: {'[HEALTHY]' if ana_ok else '[ISSUE]'}")
    print(f"Atomic: {'[READY]' if atomic_ready else '[NOT READY]'}")
    
    print("\n" + "=" * 70)
    print("PROFESSIONAL RECOMMENDATION")
    print("=" * 70)
    print("Keep agents SEPARATE for specialization:")
    print("- ANA MAX: Security/Pentesting (56 MCP tools, whitehat focus)")
    print("- Atomic-Agent: Desktop/Browser automation (skills, memory)")
    print("- Ollama: Shared resource for both (CUDA already optimized)")
    print("\nBenefits: Stability, specialization, redundancy, easier debugging")

if __name__ == "__main__":
    main()
