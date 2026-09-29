#!/usr/bin/env python3
"""Test simplu pentru verificare mitmproxy"""

import subprocess
import sys

def test_mitmproxy_install():
    """Verifica daca mitmproxy este instalat corect"""
    print("=" * 60)
    print("MITMPROXY INSTALLATION TEST")
    print("=" * 60)
    
    try:
        # Test import
        print("\n[TEST] Importing mitmproxy...")
        import mitmproxy
        print(f"[PASS] mitmproxy imported successfully")
        
        # Test mitmproxy tools
        print("\n[TEST] Checking mitmproxy tools...")
        result = subprocess.run(
            ["venv\\Scripts\\mitmdump.exe", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=True
        )
        
        if result.returncode == 0:
            print(f"[PASS] mitmproxy CLI works")
            print(f"Version info: {result.stdout[:200]}")
        else:
            print(f"[FAIL] mitmproxy CLI failed")
            print(f"Error: {result.stderr}")
            return False
        
        # Test addon
        print("\n[TEST] Checking ANA addon...")
        import os
        addon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ANA_MAX", "tools", "mitmproxy_live_analyzer.py")
        if os.path.exists(addon_path):
            print(f"[PASS] ANA addon exists: {addon_path}")
        else:
            print(f"[FAIL] ANA addon not found: {addon_path}")
            # Try alternative path
            alt_path = "C:\\Users\\billy\\Desktop\\ana-manus\\ANA_MAX\\tools\\mitmproxy_live_analyzer.py"
            if os.path.exists(alt_path):
                print(f"[PASS] ANA addon found at: {alt_path}")
            else:
                return False
        
        print("\n" + "=" * 60)
        print("MITMPROXY TEST SUMMARY")
        print("=" * 60)
        print("[PASS] All mitmproxy tests passed!")
        print("\nNext steps:")
        print("1. Run START_MITM_LIVE.bat to start capture")
        print("2. Configure your target to use proxy 127.0.0.1:8080")
        print("3. For ANA MCP testing: traffic goes through reverse proxy")
        
        return True
        
    except ImportError as e:
        print(f"[FAIL] mitmproxy import failed: {str(e)}")
        return False
    except Exception as e:
        print(f"[FAIL] Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_mitmproxy_install()
    sys.exit(0 if success else 1)
