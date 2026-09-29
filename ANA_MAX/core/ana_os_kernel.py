import json
import time
import os
import subprocess
from pathlib import Path

class AnaOSKernel:
    def __init__(self, ana_max_root: Path, default_ollama_port: int = 11434, default_openrouter_port: int = 8767):
        self.ana_max_root = ana_max_root
        self.ollama_port = default_ollama_port
        self.openrouter_port = default_openrouter_port
        self.state = {}
        self._load_state()

    def _load_state(self):
        state_file = self.ana_max_root / "memory" / "ana_os_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    self.state = json.load(f)
                print(f"[Kernel] Loaded state from {state_file}")
            except json.JSONDecodeError:
                print(f"[Kernel] Error decoding state file {state_file}. Starting with empty state.")
                self.state = {}
        else:
            print(f"[Kernel] No state file found at {state_file}. Starting with empty state.")

    def _save_state(self):
        state_file = self.ana_max_root / "memory" / "ana_os_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(self.state, f, indent=4)
        print(f"[Kernel] Saved state to {state_file}")

    def _run_curl_via_bat(self, url: str, timeout: int = 15) -> dict:
        bat_path = self.ana_max_root / "sandbox" / f"temp_curl_{int(time.time())}.bat"
        output_path = self.ana_max_root / "sandbox" / f"temp_curl_output_{int(time.time())}.txt"
        
        bat_content = f"@echo off\nC:\\WINDOWS\\system32\\curl.exe -s {url} > {output_path} 2>&1\nexit /b %errorlevel%"
        
        with open(bat_path, "w") as f:
            f.write(bat_content)
        
        try:
            # Execute the bat file using cmd.exe
            cmd = ["cmd.exe", "/c", str(bat_path)]
            print(f"[Kernel Debug] Executing BAT: {" ".join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False, timeout=timeout)
            
            stdout = ""
            if output_path.exists():
                with open(output_path, "r") as f:
                    stdout = f.read()
            
            return {"stdout": stdout, "stderr": result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out.", "returncode": 1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": 1}
        finally:
            if bat_path.exists():
                os.remove(bat_path)
            if output_path.exists():
                os.remove(output_path)

    def get_ana_status(self, port: int) -> dict:
        url = f"http://127.0.0.1:{port}/health"
        curl_result = self._run_curl_via_bat(url)
        
        if curl_result["returncode"] == 0 and curl_result["stdout"]:
            try:
                health_data = json.loads(curl_result["stdout"])
                return {"status": "online", "details": health_data}
            except json.JSONDecodeError:
                return {"status": "offline", "error": f"Invalid JSON from {url}: {curl_result["stdout"]}"}
        else:
            return {"status": "offline", "error": curl_result["stderr"] or "No output"}

    def get_ollama_status(self) -> dict:
        url = f"http://127.0.0.1:{self.ollama_port}/api/tags"
        curl_result = self._run_curl_via_bat(url)

        if curl_result["returncode"] == 0 and curl_result["stdout"]:
            try:
                ollama_data = json.loads(curl_result["stdout"])
                return {"status": "online", "details": ollama_data}
            except json.JSONDecodeError:
                return {"status": "offline", "error": f"Invalid JSON from {url}: {curl_result["stdout"]}"}
        else:
            return {"status": "offline", "error": curl_result["stderr"] or "No output"}

    def route_task(self, task_description: str, complexity: str = "medium") -> str:
        # Simple routing logic for now, will be expanded
        if complexity == "low" or self.get_ollama_status()["status"] == "online":
            print("[Kernel] Routing task to Ollama (local)...")
            return "ollama"
        elif self.get_ana_status(self.openrouter_port)["status"] == "online":
            print("[Kernel] Routing task to OpenRouter (cloud)...")
            return "openrouter"
        else:
            print("[Kernel] No active backend found. Task cannot be routed.")
            return "none"

    def execute_batch(self, commands: list[str]) -> list[dict]:
        results = []
        for cmd_str in commands:
            print(f"[Kernel] Executing: {cmd_str}")
            try:
                # This is a placeholder for actual execution via direct_bridge or similar
                # For now, just simulate success
                print(f"[Kernel] Simulating execution of: {cmd_str}")
                result = {"stdout": "Simulated output", "stderr": "", "returncode": 0}
                results.append({"command": cmd_str, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode})
            except Exception as e:
                results.append({"command": cmd_str, "error": str(e)})
        return results

    def update_state(self, key: str, value: any):
        self.state[key] = value
        self._save_state()

    def get_state(self, key: str, default: any = None):
        return self.state.get(key, default)

if __name__ == "__main__":
    # Example usage (for testing purposes)
    ana_max_path = Path(os.getcwd()).parent # Assuming ana_os_kernel.py is in ANA_MAX/core
    kernel = AnaOSKernel(ana_max_path)

    print("\n--- Initial Status ---")
    print("Ollama Status:", kernel.get_ollama_status())
    print("OpenRouter Status:", kernel.get_ana_status(kernel.openrouter_port))

    print("\n--- Routing Test ---")
    print("Route low complexity task:", kernel.route_task("list files", complexity="low"))
    print("Route high complexity task:", kernel.route_task("analyze code for vulnerabilities", complexity="high"))

    print("\n--- State Management Test ---")
    kernel.update_state("last_task", "Vibe Coding Scan")
    print("Last task from state:", kernel.get_state("last_task"))

    print("\n--- Batch Execution Test ---")
    test_commands = [
        "echo Hello from batch 1",
        "dir C:\\Users\\billy\\Desktop\\ana-manus\\ANA_MAX\\core",
        "echo This is an error && exit 1"
    ]
    batch_results = kernel.execute_batch(test_commands)
    for res in batch_results:
        print(f"Command: {res.get("command")}, Return Code: {res.get("returncode")}, Error: {res.get("error")}")
        if res.get("stdout"):
            print(f"  Stdout: {res["stdout"].strip()}")
        if res.get("stderr"):
            print(f"  Stderr: {res["stderr"].strip()}")

    print("\n--- Final State ---")
    print(kernel.state)
