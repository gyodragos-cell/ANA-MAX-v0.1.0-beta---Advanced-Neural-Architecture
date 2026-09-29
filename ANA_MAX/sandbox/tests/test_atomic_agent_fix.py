#!/usr/bin/env python3
"""Test atomic agent connectivity with Ollama"""

import subprocess
import json
import time

def test_ollama_connection():
    """Test if Ollama is running"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"[PASS] Ollama is running on port 11434")
            print(f"Available models: {[m['name'] for m in models]}")
            return True
        else:
            print(f"[FAIL] Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot connect to Ollama: {str(e)}")
        return False

def test_atomic_agent_config():
    """Check atomic agent config"""
    config_path = "C:\\Users\\billy\\.atomic-agent\\config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("\nAtomic Agent Config:")
        print(f"Mode: {config['localModels']['mode']}")
        print(f"URL: {config['localModels']['url']}")
        
        if config['localModels']['mode'] == 'external':
            print("[PASS] Mode is 'external' - will use external Ollama")
            return True
        else:
            print("[FAIL] Mode is not 'external'")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot read config: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("ATOMIC AGENT + OLLAMA CONNECTIVITY TEST")
    print("=" * 60)
    
    ollama_ok = test_ollama_connection()
    config_ok = test_atomic_agent_config()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if ollama_ok and config_ok:
        print("[SUCCESS] Everything is ready!")
        print("Atomic agent should now connect to your Ollama local")
        print("Available models include qwen2.5-coder:7b")
    elif not ollama_ok:
        print("[ACTION REQUIRED] Start Ollama first (run your BAT file)")
        print("Ollama needs to be running on http://127.0.0.1:11434")
    elif not config_ok:
        print("[ACTION REQUIRED] Config needs to be fixed")
        print("Run: python fix_atomic_agent_config.py")

if __name__ == "__main__":
    main()
