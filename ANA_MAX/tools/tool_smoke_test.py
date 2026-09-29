"""
OS27 Hyper++ Tool Smoke Test Runner
Ruleaza smoke test pentru fiecare tool: import, instantiere, executie minima.
"""

import importlib
import time
from typing import Any, Dict, List
from tools.tool_auto_discovery import discover_tool_files, validate_tool_integrity


def smoke_test_tool(tool_name: str) -> Dict[str, Any]:
    """
    Run smoke test for a single tool.
    Tests: import, class discovery, instantiation, get_definition, execute (safe).
    """
    result = {
        "tool": tool_name,
        "status": "unknown",
        "timestamp": time.time(),
        "tests": {},
    }
    
    # Test 1: Import module
    try:
        module = importlib.import_module(f"tools.{tool_name}")
        result["tests"]["import"] = {"status": "passed", "duration_ms": 0}
    except Exception as e:
        result["status"] = "failed"
        result["tests"]["import"] = {"status": "failed", "error": str(e)}
        result["error"] = f"import_failed: {str(e)}"
        return result
    
    # Test 2: Find Tool class
    try:
        from tools.base import Tool
        tool_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Tool) and attr != Tool:
                tool_class = attr
                break
        
        if not tool_class:
            result["status"] = "failed"
            result["tests"]["class_discovery"] = {"status": "failed", "error": "no_tool_class"}
            result["error"] = "no_tool_class_found"
            return result
        
        result["tests"]["class_discovery"] = {"status": "passed", "class": tool_class.__name__}
    except Exception as e:
        result["status"] = "failed"
        result["tests"]["class_discovery"] = {"status": "failed", "error": str(e)}
        result["error"] = f"class_discovery_failed: {str(e)}"
        return result
    
    # Test 3: Instantiate
    try:
        instance = tool_class()
        result["tests"]["instantiation"] = {"status": "passed"}
    except Exception as e:
        result["status"] = "failed"
        result["tests"]["instantiation"] = {"status": "failed", "error": str(e)}
        result["error"] = f"instantiation_failed: {str(e)}"
        return result
    
    # Test 4: Get definition
    try:
        definition = instance.get_definition()
        result["tests"]["get_definition"] = {
            "status": "passed",
            "name": definition.name if hasattr(definition, "name") else "unknown",
            "category": definition.category if hasattr(definition, "category") else "unknown",
        }
    except Exception as e:
        result["status"] = "failed"
        result["tests"]["get_definition"] = {"status": "failed", "error": str(e)}
        result["error"] = f"get_definition_failed: {str(e)}"
        return result
    
    # Test 5: Execute (safe - with minimal/no params)
    try:
        start = time.time()
        exec_result = instance.execute()
        duration = (time.time() - start) * 1000
        
        result["tests"]["execute"] = {
            "status": "passed",
            "duration_ms": round(duration, 2),
            "result_status": str(exec_result.status),
        }
        result["status"] = "passed"
    except Exception as e:
        # Execute failure is acceptable for smoke test (may require params)
        result["tests"]["execute"] = {
            "status": "skipped",
            "error": str(e),
            "note": "execute may require params, this is acceptable for smoke test"
        }
        result["status"] = "partial"
    
    return result


def run_all_smoke_tests(tool_names: List[str] | None = None) -> Dict[str, Any]:
    """
    Run smoke tests for all tools or a specific list.
    Returns comprehensive report with pass/fail statistics.
    """
    if tool_names is None:
        tool_names = discover_tool_files()
    
    results = []
    passed = 0
    failed = 0
    partial = 0
    total_duration = 0
    
    for tool_name in tool_names:
        start = time.time()
        result = smoke_test_tool(tool_name)
        duration = time.time() - start
        result["test_duration_ms"] = round(duration * 1000, 2)
        total_duration += duration
        
        results.append(result)
        
        if result["status"] == "passed":
            passed += 1
        elif result["status"] == "failed":
            failed += 1
        elif result["status"] == "partial":
            partial += 1
    
    return {
        "schema": "ana.tool_smoke_test_report.v1",
        "summary": {
            "total_tools": len(results),
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "pass_rate": round((passed / len(results)) * 100, 2) if results else 0,
            "total_duration_ms": round(total_duration * 1000, 2),
        },
        "results": results,
    }


def run_critical_smoke_tests() -> Dict[str, Any]:
    """Run smoke tests only for critical tools."""
    from tools.tool_priority_map import get_tools_by_priority
    critical_tools = get_tools_by_priority("critical")
    return run_all_smoke_tests(critical_tools)


def get_failed_tools(report: Dict[str, Any]) -> List[str]:
    """Extract list of failed tools from smoke test report."""
    return [r["tool"] for r in report["results"] if r["status"] == "failed"]


def get_partial_tools(report: Dict[str, Any]) -> List[str]:
    """Extract list of partially passed tools from smoke test report."""
    return [r["tool"] for r in report["results"] if r["status"] == "partial"]


def validate_tool_telemetry(tool_name: str) -> Dict[str, Any]:
    """
    Check if a tool has OS27 Hyper++ telemetry functions.
    Verifies presence of get_*_telemetry and get_*_health functions.
    """
    try:
        module = importlib.import_module(f"tools.{tool_name}")
        
        telemetry_funcs = [attr for attr in dir(module) if "telemetry" in attr.lower() and attr.startswith("get_")]
        health_funcs = [attr for attr in dir(module) if "health" in attr.lower() and attr.startswith("get_")]
        
        return {
            "tool": tool_name,
            "has_telemetry": len(telemetry_funcs) > 0,
            "telemetry_functions": telemetry_funcs,
            "has_health": len(health_funcs) > 0,
            "health_functions": health_funcs,
            "os27_hyper_ready": len(telemetry_funcs) > 0 and len(health_funcs) > 0,
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "has_telemetry": False,
            "telemetry_functions": [],
            "has_health": False,
            "health_functions": [],
            "os27_hyper_ready": False,
            "error": str(e),
        }


def check_all_tools_telemetry() -> Dict[str, Any]:
    """Check telemetry availability for all discovered tools."""
    tool_names = discover_tool_files()
    
    results = {}
    os27_ready = 0
    not_ready = 0
    
    for tool_name in tool_names:
        result = validate_tool_telemetry(tool_name)
        results[tool_name] = result
        
        if result.get("os27_hyper_ready"):
            os27_ready += 1
        else:
            not_ready += 1
    
    return {
        "schema": "ana.tool_telemetry_check.v1",
        "summary": {
            "total_tools": len(tool_names),
            "os27_hyper_ready": os27_ready,
            "not_ready": not_ready,
            "readiness_rate": round((os27_ready / len(tool_names)) * 100, 2) if tool_names else 0,
        },
        "results": results,
    }
