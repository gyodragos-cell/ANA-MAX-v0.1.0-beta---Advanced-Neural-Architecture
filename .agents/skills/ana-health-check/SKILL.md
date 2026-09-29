---
name: ana-health-check
description: Execute the ANA MAX OS v2 health.check skill to verify local system status (Ollama, Bridge, Tools). Trigger with /health-check, "run health check", or "ana health check".
---

# ANA Health Check Skill

**Triggered.** You (Antigravity/Manus) must now execute the ANA MAX OS v2 `health.check` skill via the direct bridge to verify the local system status.

## Instructions
1. Run the following command exactly as written:
   ```powershell
   python ANA_MAX/bridge/direct_bridge.py --execute --tool skill_tool --args '{"action":"execute", "capability":"health.check"}'
   ```
2. Read the output JSON.
3. Report the `overall_status` (healthy, degraded, unhealthy) and explicitly list the status of Ollama, tool_registry, and memory pressure to the user.
4. Format the output professionally (ACTION -> RESULT -> NEXT STEP) as per the AGENTS.md rules.
