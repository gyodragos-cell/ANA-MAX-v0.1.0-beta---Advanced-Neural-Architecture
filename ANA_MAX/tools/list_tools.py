#!/usr/bin/env python3
"""
List all available ANA_MAX tools with categories
"""

import sys
import json
from pathlib import Path

# Add ANA_MAX to path
ana_max_dir = Path(__file__).resolve().parents[4] / "ANA_MAX"
sys.path.insert(0, str(ana_max_dir))

from tools.qoder_ana_integration import ANAToolClient

# Tool categories
CATEGORIES = {
    "Desktop Control": ["desktop_capture", "desktop_control", "live_desktop_viewer", "windows_insight"],
    "File Operations": ["file_operations", "edit"],
    "Code & Search": ["code_tools", "smart_search", "code_search", "codebase_understanding", 
                      "grep_content", "grep_file", "glob_search"],
    "System & Terminal": ["system_control", "terminal", "system_optimization"],
    "Browser": ["browser_control"],
    "Memory & AI": ["ana_memory", "conversation_learning", "session_log_miner", "web_ai_bridge"],
    "Security": ["security_audit", "privacy_shield", "qa_testing"],
    "Network": ["network_diag", "network_pentest", "mitm_analyzer"],
    "Mobile": ["adb_operations", "frida_instrument", "apk_analyzer"],
    "Web": ["web_search", "web_scraper", "web_fetch"],
    "Development": ["git_operations", "debugger", "todowrite", "task"],
    "Autonomous": ["autonomous_engine"],
    "Advanced": ["advanced_scanner", "hardware_scanner", "bash_exec", "science_research", 
                 "adal_integration"],
    "Meta": ["ana_identity", "tool_healthcheck"]
}

def main():
    print("ANA_MAX Available Tools\n")
    print("=" * 60)
    
    ana = ANAToolClient()
    
    if not ana.is_server_running():
        print(" MCP Server is NOT running!")
        print("\nTo start:")
        print("  cd ANA_MAX")
        print("  python main.py --port 8765")
        return 1
    
    tools = ana.list_tools()
    tool_list = tools.get('result', {}).get('tools', [])
    tool_names = {t['name'] for t in tool_list}
    
    print(f"\nTotal tools available: {len(tool_list)}\n")
    
    for category, expected_tools in CATEGORIES.items():
        available = [t for t in expected_tools if t in tool_names]
        if available:
            print(f"\n{category}:")
            for tool in available:
                # Find tool description
                tool_info = next((t for t in tool_list if t['name'] == tool), None)
                desc = tool_info.get('description', '')[:60] if tool_info else ''
                print(f"  [OK] {tool:30} {desc}")
    
    print("\n" + "=" * 60)
    print(f"\nAll {len(tool_list)} tools are ready to use!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
