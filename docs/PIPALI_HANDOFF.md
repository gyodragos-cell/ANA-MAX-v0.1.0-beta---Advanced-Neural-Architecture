# Pipali Handoff — ANA MAX

**Updated:** 2026-08-04  
**Project root:** `C:\Users\billy\Desktop\ana-manus`  
**Purpose:** Fast resume checkpoint. Read this first when Robert says “reluam de unde am ramas”; then inspect only the files relevant to the new task.

## Current connection state

- Pipali MCP connector: `ana-manus`
- Transport: STDIO; no manual HTTP server startup is required.
- Command: `"C:/Program Files/Python312/python.exe" "C:/Users/billy/Desktop/ana-manus/mcp_ana_bridge.py"`
- Status after native test: connected, 18 tools, no last error.
- Confirmation mode: `unsafe_only`.
- Environment safeguards: `ANA_MCP_PROFILE=pipali`, `ANA_TOOL_STDOUT=0`.
- Other agents remain isolated: the two extra tools are advertised only for the Pipali profile; default clients keep their original compact list.

## Work completed

1. Repaired `mcp_ana_bridge.py` for the installed MCP SDK:
   - replaced unsupported constructor callbacks with registered low-level handlers;
   - corrected MCP error field `isError`;
   - replaced eager DirectBridge initialization with per-tool lazy loading;
   - moved synchronous tool execution to a worker thread;
   - preserved Pipali as the approval layer while satisfying ANA internal confirmation guards.
2. Replaced the invalid deleted venv path with explicit system Python 3.12 in the Pipali connector.
3. Added a Pipali-only compact profile with:
   - `large_file_reader`
   - `ocr_tool`
4. Enhanced `ANA_MAX/tools/large_file_reader.py`:
   - added `start_line`;
   - added targeted chunking;
   - added `next_start_line` and `has_more` cursors;
   - enables reading only relevant journal/code ranges to reduce tokens.
5. Created persistent Pipali skill:
   - `C:\Users\billy\.pipali\skills\ana-manus-workspace\SKILL.md`
   - enforces MCP-first discovery, targeted memory reads, minimal patches, verification and secret redaction.

## Validation evidence

- MCP handshake and tool list: OK, approximately 0.97 s.
- `project_navigator` real call: OK, approximately 44 ms.
- Pipali native MCP test: 18 tools, connected, `lastError=null`.
- `large_file_reader`: successfully read lines 1050–1154 from a 1,252-line `ANA_MEMORY.md` file and returned `next_start_line`.
- `ocr_tool action=check`: success; local PaddleOCR is available and lazy-loaded.

## What did not work and why

- Old HTTP connector at port 8767: disconnected because the HTTP runtime was not running.
- Template path `ANA_MAX\venv\Scripts\python.exe`: invalid because that duplicate venv had been deleted.
- Original MCP bridge: crashed because `Server(..., on_list_tools=..., on_call_tool=...)` is incompatible with the installed SDK.
- First real tool call: timed out beyond 90 seconds because all DirectBridge modules were loaded eagerly.
- Unlimited-OCR: still requires its specialized local server/model. Use `ocr_tool` with PaddleOCR for normal image OCR without that server.

## Project context already reviewed

- `AGENTS.md`
- `docs/ANA_MEMORY.md` checkpoints and latest relevant sections
- `docs/PROJECT_STATUS.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `ENGINEERING_JOURNAL.md`
- `docs/TOOLS.md`
- tool orchestration and OCR/large-file implementations

Known documentation gaps:

- `docu/ANA_MAX_Mother_Lab_Stability_Report_v2.md` is referenced by `AGENTS.md` but was not found.
- `docs/PROJECT_SUMMARY.md` was not found.
- `docs/ROADMAP.md` is older than later checkpoints in `ANA_MEMORY.md`; verify runtime truth before acting.

## Resume protocol

When Robert says “reluam de unde am ramas”:

1. Read this file first.
2. Call `tool_router` or `agent_coach` for the new goal.
3. Read only the latest applicable section of `ANA_MEMORY.md` with `large_file_reader`.
4. Verify current code/config/log state; do not rely solely on historical status.
5. Apply the smallest patch and verify it.
6. Update this handoff and append a checkpoint to `ANA_MEMORY.md` after meaningful work.

## Security note

Historical memory/config files contain plaintext credentials. Never reproduce them in chat, logs, patches, or public files. Redact and recommend rotation when relevant.

## Next decision point

No MCP/OCR setup work is currently blocked. For the next project task, choose from current documented priorities: investigate active log errors, synchronize roadmap/status docs, or improve installation/troubleshooting/API documentation.
