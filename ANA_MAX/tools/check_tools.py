import requests
import json

MCP_URL = "http://127.0.0.1:8766/mcp"

def check_tool(tool_name):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    try:
        res = requests.post(MCP_URL, json=payload)
        tools = res.json().get("result", {}).get("tools", [])
        names = [t["name"] for t in tools]
        print(f"Tool '{tool_name}' present: {tool_name in names}")
        if tool_name not in names:
            print(f"Total tools: {len(names)}")
            print(f"First 10 tools: {names[:10]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tool("session_checkpoint")
    check_tool("ana_identity")
