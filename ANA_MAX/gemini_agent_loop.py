"""
ANA Agent Loop — Gemini Brain + ANA OS27 Tools (INTEGRATED)
============================================================
Connects Gemini (free LLM via proxy) to ANA MAX OS27 tools (122 tools).
Gemini = creier, ANA OS27 = maini.

Usage:
  python gemini_agent_loop.py "creeaza un website simplu"
  python gemini_agent_loop.py   (interactive mode)
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
PROXY_URL  = "http://127.0.0.1:11435"
WORKSPACE  = r"c:\Users\billy\Desktop\ana-manus"
MAX_LOOPS  = 20
TIMEOUT_S  = 120

# ── ANA MAX Bridge Integration ─────────────────────────────────────────────────
ANA_MAX_ROOT = Path(__file__).parent.parent / "ANA_MAX"
sys.path.insert(0, str(ANA_MAX_ROOT))
sys.path.insert(0, str(ANA_MAX_ROOT.parent))

try:
    from bridge.direct_bridge import DirectBridge
    from tools.base import registry
    ANA_BRIDGE = DirectBridge(include_hybrid_tools=True)
    ANA_AVAILABLE = True
    print(f"[OK] ANA MAX Bridge connected with {ANA_BRIDGE.loaded_tools + ANA_BRIDGE.hybrid_loaded_tools} tools")
except Exception as e:
    print(f"[WARN] ANA MAX Bridge not available: {e}")
    print("[FALLBACK] Using basic tools only")
    ANA_AVAILABLE = False

def get_ana_tools_doc():
    """Generate tool documentation from ANA registry."""
    if not ANA_AVAILABLE:
        return "  [FALLBACK MODE - Limited basic tools only]"
    
    tools_doc = []
    tool_names = registry.list_tools()
    for tool_name in tool_names:
        try:
            tool_obj = registry.get_tool(tool_name)
            desc = getattr(tool_obj, 'description', tool_name)
            tools_doc.append(f"  - {tool_name}: {desc}")
        except:
            tools_doc.append(f"  - {tool_name}: [No description]")
    
    return "\n".join(tools_doc)

SYSTEM_PROMPT = f"""You are an autonomous AI agent with direct access to ANA MAX OS27 tools on a Windows PC.
Your job: receive a task, plan, execute using tools, verify, report done.

CRITICAL: You MUST call tools to complete tasks. Do NOT ask the user to run commands manually.
When user asks to list files, use the file_operations tool. When user asks to run commands, use the terminal tool.

AVAILABLE TOOLS (ANA MAX OS27):
{get_ana_tools_doc()}

HOW TO CALL A TOOL - wrap each call in XML tags like this:
<tool_call> tags:
Example:<tool_call>
{{"tool": "file_write", "args": {{"path": "project/index.html", "content": "<!DOCTYPE html>..."}}}}
</tool_call>

RULES:
1. You can make MULTIPLE tool calls in one response.
2. After receiving tool results, continue working or say TASK_COMPLETE when done.
3. File paths are relative to workspace: {WORKSPACE}
4. For terminal commands, use PowerShell syntax (this is Windows).
5. Always mkdir before writing files in subdirectories.
6. When building websites, write COMPLETE files — no placeholders, no "add your code here".
7. Test your work: after creating files, use list_dir to verify.
8. Think step by step but be concise.
"""


# ── HTTP client (stdlib only) ─────────────────────────────────────────────────
def _post(url: str, payload: dict, timeout: int = TIMEOUT_S) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


# ── Duck.ai chat ──────────────────────────────────────────────────────────────
def chat(messages: list[dict]) -> str:
    """Send messages to Gemini via the Ollama-compatible proxy."""
    result = _post(f"{PROXY_URL}/api/chat", {
        "model": "gemini-ai:latest",
        "messages": messages,
        "stream": False,
    })
    if "error" in result:
        raise RuntimeError(f"Gemini proxy error: {result['error']}")
    return result["message"]["content"]


# ── Tool call parser ──────────────────────────────────────────────────────────
_TOOL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def extract_tool_calls(text: str) -> list[dict]:
    """Extract all <tool_call>...</tool_call> JSON blocks from LLM response."""
    calls = []
    for match in _TOOL_RE.findall(text):
        raw = match.strip()
        # Sometimes LLMs wrap JSON in ```json ... ``` inside the tags
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            obj = json.loads(raw)
            calls.append(obj)
        except json.JSONDecodeError:
            _p(f"  [!] Bad JSON in tool_call: {raw[:120]}", "WARN")
    return calls


# ── Tool executor ─────────────────────────────────────────────────────────────
def _resolve(path: str) -> str:
    """Resolve relative path to absolute workspace path."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(WORKSPACE, path))


def execute_tool(name: str, args: dict) -> str:
    """Execute a single tool call using ANA MAX bridge when available."""
    # Try ANA MAX bridge first
    if ANA_AVAILABLE:
        try:
            result = ANA_BRIDGE.execute_tool(name, args)
            if result.get("success"):
                data = result.get("data", {})
                if isinstance(data, str):
                    return f"[ANA] {data}"
                elif isinstance(data, dict):
                    return f"[ANA] {json.dumps(data, indent=2)}"
                else:
                    return f"[ANA] Success: {name}"
            else:
                error = result.get("error", "Unknown error")
                return f"[ANA ERROR] {name}: {error}"
        except Exception as e:
            _p(f"ANA bridge failed for {name}: {e}, trying fallback", "WARN")
    
    # Fallback to basic tools
    try:
        if name == "file_write":
            fp = _resolve(args["path"])
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return f"OK — wrote {fp} ({len(args['content'])} bytes)"

        elif name == "file_read":
            fp = _resolve(args["path"])
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read(50_000)  # cap at 50KB
            return f"Content of {fp}:\n{content}"

        elif name == "list_dir":
            fp = _resolve(args.get("path", "."))
            entries = sorted(os.listdir(fp))
            types = []
            for e in entries:
                full = os.path.join(fp, e)
                kind = "DIR" if os.path.isdir(full) else "FILE"
                types.append(f"  {kind}  {e}")
            return f"Directory {fp}:\n" + "\n".join(types)

        elif name == "mkdir":
            fp = _resolve(args["path"])
            os.makedirs(fp, exist_ok=True)
            return f"OK — directory created: {fp}"

        elif name == "terminal":
            cmd = args["command"]
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=WORKSPACE,
            )
            out = (r.stdout + r.stderr).strip()
            return f"Exit {r.returncode}\n{out}" if out else f"Exit {r.returncode} (no output)"

        else:
            return f"ERROR — unknown tool: {name}"

    except Exception as e:
        return f"ERROR — {type(e).__name__}: {e}"


# ── Pretty print ──────────────────────────────────────────────────────────────
_COLORS = {"INFO": "\033[36m", "TOOL": "\033[33m", "OK": "\033[32m",
           "WARN": "\033[91m", "GEMINI": "\033[35m", "RESET": "\033[0m"}


def _p(msg: str, tag: str = "INFO"):
    c = _COLORS.get(tag, "")
    r = _COLORS["RESET"]
    try:
        print(f"{c}[{tag}]{r} {msg}")
    except UnicodeEncodeError:
        print(f"{c}[{tag}]{r} {msg.encode('utf-8', errors='replace').decode('cp1252', errors='replace')}")


# ── Main agent loop ──────────────────────────────────────────────────────────
def run_agent(task: str):
    """The agentic loop: send task → get response → execute tools → repeat."""
    if ANA_AVAILABLE:
        _p(f"ANA MAX Bridge active with {ANA_BRIDGE.loaded_tools + ANA_BRIDGE.hybrid_loaded_tools} tools", "OK")
    else:
        _p("Running in fallback mode (basic tools only)", "WARN")
    
    _p(f"Starting agent loop with MAX_LOOPS={MAX_LOOPS}", "INFO")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": task},
    ]

    _p(f"Messages prepared: {len(messages)} messages", "INFO")

    for i in range(1, MAX_LOOPS + 1):
        _p(f"Starting loop iteration {i}", "INFO")
        print(f"\n{'=' * 60}")
        _p(f"Loop {i}/{MAX_LOOPS} — sending to Gemini...", "INFO")

        try:
            _p(f"Sending {len(messages)} messages to Duck.ai...", "INFO")
            _p(f"Messages content preview: {messages[-1]['content'][:100]}...", "INFO")
            response = chat(messages)
            _p(f"Got response from Gemini: {len(response)} chars", "INFO")
            
            if not response or len(response) < 10:
                _p("Empty or too short response from Duck.ai", "WARN")
                break
        except Exception as e:
            _p(f"Gemini error: {e}", "WARN")
            import traceback
            traceback.print_exc()
            break

        # Show (truncated) response
        preview = response[:600] + ("..." if len(response) > 600 else "")
        _p(preview, "GEMINI")

        # Check for TASK_COMPLETE
        if "TASK_COMPLETE" in response:
            _p("Task marked complete by agent.", "OK")
            break

        # Extract and execute tool calls
        calls = extract_tool_calls(response)

        if not calls:
            _p("No tool calls found. Task may be done.", "OK")
            break

        # Execute each tool
        results = []
        for c in calls:
            tool = c.get("tool", "?")
            args = c.get("args", {})
            summary = json.dumps(args, ensure_ascii=False)
            if len(summary) > 200:
                summary = summary[:200] + "..."
            _p(f"{tool}({summary})", "TOOL")

            result = execute_tool(tool, args)
            _p(result[:300], "OK")
            results.append(f"[{tool}] {result}")

        # Feed results back to the conversation
        messages.append({"role": "assistant", "content": response})
        results_text = "\n---\n".join(results)
        messages.append({
            "role": "user",
            "content": (
                f"Tool execution results:\n{results_text}\n\n"
                "Continue working on the task. "
                "If everything is done, say TASK_COMPLETE."
            ),
        })

    print(f"\n{'=' * 60}")
    _p("Agent loop finished (exited normally).", "INFO")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    # Check proxy health first
    _p("Checking Duck.ai proxy...", "INFO")
    try:
        h = _get(f"{PROXY_URL}/health")
        _p(f"Proxy OK: {h}", "OK")
    except Exception as e:
        _p(f"Proxy not running at {PROXY_URL}: {e}", "WARN")
        _p("Start the proxy first: START_GEMINI_PROXY.bat", "WARN")
        return

    # Get task
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("\n" + "=" * 42)
        print("  ANA Agent Loop — Gemini + ANA OS27 Tools")
        print("=" * 42)
        print()
        task = input("  What should I build? > ").strip()

    if not task:
        _p("No task provided.", "WARN")
        return

    _p(f"Task: {task}", "INFO")
    print()

    try:
        run_agent(task)
    except Exception as e:
        _p(f"Agent loop error: {e}", "WARN")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
