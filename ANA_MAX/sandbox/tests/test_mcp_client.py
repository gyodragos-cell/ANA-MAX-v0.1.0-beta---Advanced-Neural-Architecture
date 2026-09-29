import subprocess
import json
import time
import os

env = os.environ.copy()
env["PYTHONPATH"] = r"C:\Users\billy\Desktop\ana-manus"

p = subprocess.Popen(
    [r"C:\Users\billy\Desktop\ana-manus\venv\Scripts\python.exe", "-u", r"C:\Users\billy\Desktop\ana-manus\mcp_ana_bridge.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}
req_str = json.dumps(req) + "\n"

print(f"Sending: {req_str}")
start = time.time()
p.stdin.write(req_str)
p.stdin.flush()

# Also try to read stderr non-blocking or just read stdout
try:
    stdout_line = p.stdout.readline()
    print(f"Received in {time.time()-start:.2f}s: {stdout_line}")
except Exception as e:
    print(f"Error: {e}")

p.kill()
