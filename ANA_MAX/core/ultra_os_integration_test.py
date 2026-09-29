import os
from pathlib import Path
from ana_os_kernel import AnaOSKernel
from semantic_memory import SemanticMemory
from self_healing import SelfHealingEngine
from shadow_exec import ShadowExec
from datetime import datetime

class MockAnaOSKernel(AnaOSKernel):
    def get_ollama_status(self) -> dict:
        print("[Mock Kernel] Returning mocked Ollama status: online")
        return {"status": "online", "details": {"models": [{"name": "qwen2.5-coder:7b"}]}}

    def get_ana_status(self, port: int) -> dict:
        print(f"[Mock Kernel] Returning mocked ANA status for port {port}: online")
        return {"status": "online", "details": {"agent": "A.N.A. MAX", "mcp_ready": True}}

def run_ultra_os_test():
    script_dir = Path(__file__).parent
    ana_max_root = script_dir.parent # Assuming script is in ANA_MAX/core

    print(f"[DEBUG] ana_max_root calculated as: {ana_max_root}")

    print("\n--- Initializing ULTRA-OS Components (with Mock Kernel) ---")
    kernel = MockAnaOSKernel(ana_max_root)
    semantic_memory = SemanticMemory(ana_max_root / "memory")
    self_healing = SelfHealingEngine(ana_max_root)
    shadow_exec = ShadowExec(str(ana_max_root / "sandbox" / "temp_exec"))

    print("\n--- System Status Check (Mocked) ---")
    ollama_status = kernel.get_ollama_status()
    openrouter_status = kernel.get_ana_status(kernel.openrouter_port)
    print(f"Ollama Status: {ollama_status['status']}")
    print(f"OpenRouter Status: {openrouter_status['status']}")

    print("\n--- Semantic Memory Indexing ---")
    semantic_memory.index_directory(ana_max_root / "core")
    print(f"Indexed files: {list(semantic_memory.index['files'].keys())}")
    search_results = semantic_memory.search("kernel")
    print(f"Search for 'kernel': {search_results}")

    print("\n--- Task Routing and Execution ---")
    task1 = "List all Python files in ANA_MAX/core"
    route1 = kernel.route_task(task1, complexity="low")
    print(f"Task '{task1}' routed to: {route1}")
    if route1 == "ollama":
        print("[Simulated Ollama Execution] Listing files...")

    task2 = "Analyze the security vulnerabilities in the current codebase"
    route2 = kernel.route_task(task2, complexity="high")
    print(f"Task '{task2}' routed to: {route2}")
    if route2 == "openrouter":
        print("[Simulated OpenRouter Execution] Analyzing vulnerabilities...")

    print("\n--- Self-Healing Test ---")
    error_msg1 = "NameError: name '_get_tool_registry' is not defined"
    healing_suggestion1 = self_healing.analyze_error(error_msg1)
    print(f"Error: {error_msg1}\n  Healing Suggestion: {healing_suggestion1['suggestion']}")

    error_msg2 = "ModuleNotFoundError: No module named 'non_existent_module'"
    healing_suggestion2 = self_healing.analyze_error(error_msg2)
    print(f"Error: {error_msg2}\n  Healing Suggestion: {healing_suggestion2['suggestion']}")

    print("\n--- Shadow Execution Test ---")
    dangerous_command = "rm -rf /"
    dry_run_result = shadow_exec.dry_run(dangerous_command)
    print(f"Dry run for '{dangerous_command}': {dry_run_result}")

    safe_script = "print('Hello from Shadow Sandbox')"
    sandbox_result = shadow_exec.execute_in_sandbox(safe_script)
    print(f"Sandbox execution result: {sandbox_result}")

    print("\n--- State Management ---")
    kernel.update_state("last_ultra_os_run", datetime.now().isoformat())
    print(f"Last ULTRA-OS run: {kernel.get_state('last_ultra_os_run')}")

    print("\n--- ULTRA-OS Test Complete ---")

if __name__ == "__main__":
    run_ultra_os_test()
