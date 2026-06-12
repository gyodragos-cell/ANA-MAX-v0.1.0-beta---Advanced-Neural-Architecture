import requests
import json

MCP = "http://127.0.0.1:8766/mcp"

def mcp_call(method, params=None):
    r = requests.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}, timeout=15)
    return r.json()

res = mcp_call("tools/list")
tools = res.get("result", {}).get("tools", [])
names = sorted([t["name"] for t in tools])

with open("all_tools.txt", "w") as f:
    f.write("\n".join(names))

print(f"Wrote {len(names)} tools to all_tools.txt")
