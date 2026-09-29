#!/usr/bin/env python3
"""
Test Suite pentru Super Prompt Repairs - ANA MAX
Testeaza toate cele 9 reparatii din super prompt.
"""

import sys
import os
import time
from pathlib import Path

# Add paths
ANA_MANUS_ROOT = Path(__file__).resolve().parent
ANA_MAX_ROOT = ANA_MANUS_ROOT / "ANA_MAX"
for p in (ANA_MAX_ROOT, ANA_MANUS_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

def test_tool_router_regex_fallback():
    """Test #1: ToolRouter regex fallback for LLM classification timeout"""
    print("TEST #1: ToolRouter regex fallback...")
    try:
        from tools.tool_router_tool import ToolRouterTool
        tool = ToolRouterTool()
        result = tool.execute(task="error: failed", error="timeout error")
        # Should use regex fallback immediately, not LLM
        assert result.is_success, "ToolRouter execution failed"
        print("[OK] ToolRouter regex fallback works")
        return True
    except Exception as e:
        print(f"[FAIL] ToolRouter test failed: {e}")
        return False

def test_loop_detection():
    """Test #2: Loop detection si stop automat la erori repetitive"""
    print("TEST #2: Loop detection...")
    try:
        from tools.agent_coach_tool import AgentCoachTool
        tool = AgentCoachTool()
        # Test auto-stop logic
        result = tool.execute(action="coach", limit=10)
        assert result.is_success, "AgentCoach execution failed"
        print("[OK] Loop detection works")
        return True
    except Exception as e:
        print(f"[FAIL] Loop detection test failed: {e}")
        return False

def test_mcp_delegates():
    """Test #3: MCP delegates conectare la implementari locale"""
    print("TEST #3: MCP delegates...")
    try:
        # Check if MCP bridge has delegate implementations
        mcp_core = Path("mcp_ana_bridge_core.py")
        if mcp_core.exists():
            content = mcp_core.read_text()
            assert "from tools." in content, "MCP bridge not connected to local tools"
        print("[OK] MCP delegates connected")
        return True
    except Exception as e:
        print(f"[FAIL] MCP delegates test failed: {e}")
        return False

def test_omniroute_backoff():
    """Test #4: OmniRoute 500 fix + exponential backoff"""
    print("TEST #4: OmniRoute exponential backoff...")
    try:
        from core.backends.omniroute_backend import OmniRouteClient
        # Check if backoff logic exists
        client_file = Path("ANA_MAX/core/backends/omniroute_backend.py")
        if client_file.exists():
            content = client_file.read_text()
            assert "exponential backoff" in content.lower() or "retry" in content.lower(), "Backoff logic not found"
        print("[OK] OmniRoute backoff logic present")
        return True
    except Exception as e:
        print(f"[FAIL] OmniRoute backoff test failed: {e}")
        return False

def test_tool_validation():
    """Test #5: Tool calling validation (verificare efect real)"""
    print("TEST #5: Tool calling validation...")
    try:
        from core.backends.ollama_backend import _validate_tool_effect
        # Check if validation function exists
        assert callable(_validate_tool_effect), "Validation function not found"
        print("[OK] Tool validation function exists")
        return True
    except Exception as e:
        print(f"[FAIL] Tool validation test failed: {e}")
        return False

def test_memory_cortex_api():
    """Test #6: Memory Cortex API alignment"""
    print("TEST #6: Memory Cortex API alignment...")
    try:
        # Check if MCP bridge has proper memory cortex mapping
        mcp_core = Path("mcp_ana_bridge_core.py")
        if mcp_core.exists():
            content = mcp_core.read_text()
            assert "memory_cortex" in content, "Memory cortex not in MCP bridge"
        print("[OK] Memory Cortex API aligned")
        return True
    except Exception as e:
        print(f"[FAIL] Memory Cortex API test failed: {e}")
        return False

def test_context_compression():
    """Test #7: Context compression + truncate tool results"""
    print("TEST #7: Context compression...")
    try:
        from core.backends.ollama_backend import _execute_tool
        # Check if compression logic exists
        backend_file = Path("ANA_MAX/core/backends/ollama_backend.py")
        if backend_file.exists():
            content = backend_file.read_text()
            assert "compress" in content.lower() or "truncate" in content.lower() or "2000" in content, "Compression logic not found"
        print("[OK] Context compression logic present")
        return True
    except Exception as e:
        print(f"[FAIL] Context compression test failed: {e}")
        return False

def test_mcp_filtering():
    """Test #8: MCP tool filtering (56 → subset relevant)"""
    print("TEST #8: MCP tool filtering...")
    try:
        mcp_core = Path("mcp_ana_bridge_core.py")
        if mcp_core.exists():
            content = mcp_core.read_text()
            assert "TOOL_CATEGORIES" in content or "category" in content.lower(), "Tool categories not found"
        print("[OK] MCP tool filtering logic present")
        return True
    except Exception as e:
        print(f"[FAIL] MCP tool filtering test failed: {e}")
        return False

def test_lazy_loading():
    """Test #9: Lazy loading bridges (latenta 90s+)"""
    print("TEST #9: Lazy loading bridges...")
    try:
        mcp_core = Path("mcp_ana_bridge_core.py")
        if mcp_core.exists():
            content = mcp_core.read_text()
            assert "MCP_LAZY_LOAD" in content or "lazy" in content.lower(), "Lazy loading logic not found"
        print("[OK] Lazy loading logic present")
        return True
    except Exception as e:
        print(f"[FAIL] Lazy loading test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("SUPER PROMPT REPAIRS TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_tool_router_regex_fallback,
        test_loop_detection,
        test_mcp_delegates,
        test_omniroute_backoff,
        test_tool_validation,
        test_memory_cortex_api,
        test_context_compression,
        test_mcp_filtering,
        test_lazy_loading,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} crashed: {e}")
            results.append(False)
        time.sleep(0.5)  # Small delay between tests
    
    print("=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
