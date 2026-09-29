"""
Smoke test: spawn a benign subprocess and invoke ReflexDispatcher._execute_remediation
This script spawns: python -c "import time; time.sleep(60)" and then calls remediation to kill it.
"""
import subprocess
import sys
import time
from pathlib import Path

# ensure project root on path
proj_root = Path(__file__).resolve().parents[1]
import os
import json
sys.path.insert(0, str(proj_root))

from tools.reflex_dispatcher import dispatcher

# spawn a benign process that sleeps for 60s
python_exe = sys.executable
# Use a simple cross-platform sleep via Python
proc = subprocess.Popen([python_exe, "-c", "import time; time.sleep(60)"])
print(f"Spawned test process PID={proc.pid}")

# give it a moment
time.sleep(0.5)

# craft a minimal rule that requests kill
rule = {
    "id": "smoke-kill-test",
    "severity": "critical",
    "message": "Smoke test kill",
    "remediation": {
        "enabled": True,
        "action": "kill_process",
        "dry_run": False
    }
}

event_data = {"pid": proc.pid, "api": "SMOKE_TEST", "details": {"reason": "smoke"}}

print("Invoking dispatcher._execute_remediation...")
dispatcher._execute_remediation(rule, event_data)

# wait briefly to let dispatcher act
time.sleep(0.5)

# check process status
still_alive = proc.poll() is None
print(f"Process alive after remediation? {still_alive}")

# if still alive, attempt to terminate (cleanup)
if still_alive:
    try:
        proc.terminate()
        print("Cleanup: terminated process")
    except Exception as e:
        print(f"Cleanup failed: {e}")

# read small tail of audit log
audit_path = proj_root / "logs" / "os26_audit.jsonl"
if audit_path.exists():
    print("--- Audit tail ---")
    with open(audit_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-10:]
        for ln in lines:
            try:
                print(json.dumps(json.loads(ln.strip()), ensure_ascii=False))
            except Exception:
                print(ln.strip())
else:
    print("Audit log not found")

print("Smoke test complete.")
