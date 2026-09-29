---
name: ana-self-repair
description: Execute the ANA MAX OS v2 self.repair skill to diagnose and patch errors in the local workspace. Trigger with /self-repair, "run self repair", or "ana self repair".
---

# ANA Self Repair Skill

**Triggered.** You (Antigravity/Manus) must now execute the ANA MAX OS v2 `self.repair` skill via the direct bridge to initiate an automated repair sequence.

## Instructions
1. Ensure the user has provided a `target` file path and an `error_pattern`. If they haven't, ask them first.
2. Run the following command exactly as written, replacing `<TARGET>` and `<PATTERN>` with the actual values:
   ```powershell
   python ANA_MAX/bridge/direct_bridge.py --execute --tool skill_tool --args '{"action":"execute", "capability":"self.repair", "payload": {"target": "<TARGET>", "error_pattern": "<PATTERN>"}}'
   ```
3. Read the output JSON. The engine will return a `tool_chain` array.
4. Execute the returned `tool_chain` array **step-by-step** in order. The sequence typically is: scan (error_radar), checkpoint, patch, verify (smoke test).
5. If the smoke test verification step fails, immediately execute the rollback step specified in the tool chain.
6. Format the final output professionally (ACTION -> RESULT -> NEXT STEP).
