---
name: ana-fs-inspect
description: Execute the ANA MAX OS v2 fs.inspect skill to analyze the workspace file structure. Trigger with /fs-inspect, "run fs inspect", or "ana fs inspect".
---

# ANA FS Inspect Skill

**Triggered.** You (Antigravity/Manus) must now execute the ANA MAX OS v2 `fs.inspect` skill via the direct bridge to analyze a target directory.

## Instructions
1. Determine the `path` the user wants to inspect. If not specified, default to `.` (the workspace root).
2. Run the following command exactly as written, replacing `<PATH>` with the requested directory:
   ```powershell
   python ANA_MAX/bridge/direct_bridge.py --execute --tool skill_tool --args '{"action":"execute", "capability":"fs.inspect", "payload": {"path": "<PATH>"}}'
   ```
3. Read the output JSON.
4. Provide a professional summary (ACTION -> RESULT -> NEXT STEP) displaying the total file count, directory count, size, and highlighting any abnormally large files found in the `large_files` array.
