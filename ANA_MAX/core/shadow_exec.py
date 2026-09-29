import subprocess
import os

class ShadowExec:
    def __init__(self, sandbox_dir: str = "ANA_MAX/sandbox/temp_exec"):
        self.sandbox_dir = sandbox_dir
        if not os.path.exists(self.sandbox_dir):
            os.makedirs(self.sandbox_dir)

    def dry_run(self, command: str):
        print(f"[Shadow] Dry-running command: {command}")
        # In a real scenario, this would use a container or a restricted environment
        # For now, we simulate the analysis of the command
        if "rm -rf /" in command or "del /s /q C:\\" in command:
            return {"safe": False, "reason": "Destructive command detected."}
        
        return {"safe": True, "reason": "Command appears safe for local execution."}

    def execute_in_sandbox(self, script_content: str, filename: str = "test_script.py"):
        path = os.path.join(self.sandbox_dir, filename)
        with open(path, "w") as f:
            f.write(script_content)
        
        print(f"[Shadow] Executing script in sandbox: {path}")
        try:
            result = subprocess.run(["python", path], capture_output=True, text=True, timeout=30)
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out."}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    shadow = ShadowExec()
    print(shadow.dry_run("rm -rf /"))
    print(shadow.execute_in_sandbox("print('Hello from Shadow Sandbox')"))
