"""
OS27 Hyper++ Tool Auto-Fix Engine
Detecteaza tooluri stricate si trimite la SelfEvolvingTool pentru reparare.
"""

import time
from typing import Any, Dict, List
from tools.tool_smoke_test import run_all_smoke_tests, get_failed_tools, smoke_test_tool
from tools.tool_priority_map import get_priority


def auto_fix_tools(tool_names: List[str] | None = None) -> Dict[str, Any]:
    """
    Auto-fix broken tools by detecting failures and attempting repairs.
    
    Process:
    1. Run smoke tests to identify broken tools
    2. For each broken tool, analyze with SelfEvolvingTool
    3. Attempt auto-fix if SelfEvolvingTool suggests fixes
    4. Re-test to verify fix
    
    Returns:
        Dictionary with broken tools, analysis results, and fix attempts.
    """
    # Step 1: Run smoke tests to find broken tools
    smoke_report = run_all_smoke_tests(tool_names)
    broken_tools = get_failed_tools(smoke_report)
    
    if not broken_tools:
        return {
            "schema": "ana.tool_auto_fix.v1",
            "status": "no_broken_tools",
            "broken_tools": [],
            "fix_attempts": [],
            "summary": {
                "total_checked": smoke_report["summary"]["total_tools"],
                "broken": 0,
                "fixed": 0,
                "failed_to_fix": 0,
            },
        }
    
    # Step 2: Analyze each broken tool with SelfEvolvingTool
    fix_attempts = []
    fixed_count = 0
    failed_fix_count = 0
    
    try:
        from tools.self_evolving_tool import SelfEvolvingTool
        evolver = SelfEvolvingTool()
    except Exception:
        evolver = None
    
    for tool_name in broken_tools:
        fix_attempt = {
            "tool": tool_name,
            "priority": get_priority(tool_name),
            "original_error": None,
            "analysis": None,
            "fix_suggested": None,
            "fix_applied": False,
            "retest_result": None,
            "fixed": False,
        }
        
        # Get original error from smoke test
        for result in smoke_report["results"]:
            if result["tool"] == tool_name:
                fix_attempt["original_error"] = result.get("error", "unknown")
                break
        
        # Analyze with SelfEvolvingTool
        if evolver:
            try:
                analysis_result = evolver.execute(
                    action="analyze_anomaly",
                    anomaly_type="tool_failure",
                    details={
                        "tool_name": tool_name,
                        "error": fix_attempt["original_error"],
                        "smoke_test_result": next((r for r in smoke_report["results"] if r["tool"] == tool_name), None),
                    }
                )
                fix_attempt["analysis"] = {
                    "status": analysis_result.status.value if hasattr(analysis_result.status, "value") else str(analysis_result.status),
                    "suggestion": analysis_result.data.get("suggestion") if analysis_result.data else None,
                }
                
                # Check if fix was suggested
                if analysis_result.is_success and analysis_result.data:
                    fix_attempt["fix_suggested"] = analysis_result.data.get("suggestion")
                    
                    # Apply fix if suggested (this is a placeholder - actual fix logic would be tool-specific)
                    if fix_attempt["fix_suggested"]:
                        fix_attempt["fix_applied"] = attempt_auto_fix(tool_name, fix_attempt["fix_suggested"])
            except Exception as e:
                fix_attempt["analysis"] = {"status": "failed", "error": str(e)}
        
        # Re-test if fix was applied
        if fix_attempt["fix_applied"]:
            retest_result = smoke_test_tool(tool_name)
            fix_attempt["retest_result"] = retest_result["status"]
            
            if retest_result["status"] in ["passed", "partial"]:
                fix_attempt["fixed"] = True
                fixed_count += 1
            else:
                failed_fix_count += 1
        else:
            failed_fix_count += 1
        
        fix_attempts.append(fix_attempt)
    
    return {
        "schema": "ana.tool_auto_fix.v1",
        "status": "completed",
        "broken_tools": broken_tools,
        "fix_attempts": fix_attempts,
        "summary": {
            "total_checked": smoke_report["summary"]["total_tools"],
            "broken": len(broken_tools),
            "fixed": fixed_count,
            "failed_to_fix": failed_fix_count,
            "fix_success_rate": round((fixed_count / len(broken_tools)) * 100, 2) if broken_tools else 0,
        },
    }


def attempt_auto_fix(tool_name: str, suggestion: str) -> bool:
    """
    Attempt to apply auto-fix for a tool based on SelfEvolvingTool suggestion.
    This is a placeholder implementation - actual fix logic would be tool-specific.
    
    Returns:
        True if fix was applied, False otherwise.
    """
    # Placeholder: In a real implementation, this would:
    # 1. Parse the suggestion to understand the fix
    # 2. Apply code patches using file_patch_tool
    # 3. Update imports or dependencies
    # 4. Modify configuration if needed
    
    # For now, return False to indicate no auto-fix was applied
    # This would be expanded with actual fix logic per tool type
    return False


def auto_fix_critical_tools() -> Dict[str, Any]:
    """Auto-fix only critical priority tools."""
    from tools.tool_priority_map import get_tools_by_priority
    critical_tools = get_tools_by_priority("critical")
    return auto_fix_tools(critical_tools)


def get_fix_recommendations(tool_name: str) -> Dict[str, Any]:
    """
    Get fix recommendations for a specific tool without applying fixes.
    Useful for manual review before auto-fix.
    """
    smoke_result = smoke_test_tool(tool_name)
    
    if smoke_result["status"] == "passed":
        return {
            "tool": tool_name,
            "status": "healthy",
            "message": "Tool is healthy, no fix needed",
        }
    
    recommendation = {
        "tool": tool_name,
        "status": "needs_fix",
        "error": smoke_result.get("error"),
        "failed_tests": [test for test, result in smoke_result["tests"].items() if result.get("status") == "failed"],
    }
    
    # Try to get SelfEvolvingTool analysis
    try:
        from tools.self_evolving_tool import SelfEvolvingTool
        evolver = SelfEvolvingTool()
        
        analysis_result = evolver.execute(
            action="analyze_anomaly",
            anomaly_type="tool_failure",
            details={
                "tool_name": tool_name,
                "error": smoke_result.get("error"),
                "smoke_test_result": smoke_result,
            }
        )
        
        if analysis_result.is_success and analysis_result.data:
            recommendation["analysis"] = {
                "suggestion": analysis_result.data.get("suggestion"),
                "confidence": analysis_result.data.get("confidence"),
                "estimated_fix_time": analysis_result.data.get("estimated_fix_time"),
            }
    except Exception as e:
        recommendation["analysis"] = {"error": str(e)}
    
    return recommendation


def generate_fix_report() -> Dict[str, Any]:
    """
    Generate comprehensive fix report for all tools.
    Includes health status, fix recommendations, and auto-fix potential.
    """
    from tools.tool_smoke_test import run_all_smoke_tests
    from tools.tool_health_dashboard import get_tool_health_dashboard
    
    smoke_report = run_all_smoke_tests()
    health_dashboard = get_tool_health_dashboard()
    
    broken_tools = get_failed_tools(smoke_report)
    
    # Get recommendations for broken tools
    recommendations = {}
    for tool in broken_tools:
        recommendations[tool] = get_fix_recommendations(tool)
    
    return {
        "schema": "ana.tool_fix_report.v1",
        "generated_at": time.time(),
        "smoke_test_summary": smoke_report["summary"],
        "health_summary": health_dashboard["summary"],
        "broken_tools": broken_tools,
        "recommendations": recommendations,
        "auto_fix_potential": {
            "total_broken": len(broken_tools),
            "can_auto_fix": sum(1 for r in recommendations.values() if r.get("analysis", {}).get("suggestion")),
            "requires_manual": sum(1 for r in recommendations.values() if not r.get("analysis", {}).get("suggestion")),
        },
    }
