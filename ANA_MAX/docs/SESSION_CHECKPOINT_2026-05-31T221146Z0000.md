# Session Checkpoint - 2026-05-31T22:11:46+00:00

## Manager prompt updated for Dirty Tree evidence

## Summary

Updated Codex lab manager prompt and LLM index so Patch Advisor is described as using local Dirty Tree evidence plus graph blast-radius, not graph-only recommendations. Governance remains PASS 116/116.

## Current Goal

Keep future Codex/agent boot context aligned with current ANA self-healing architecture.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- docs/CODEX_LAB_MANAGER_PROMPT.md
- docs/ANA_LAB_LLM_INDEX.md
- docs/AGENT_MEMORY.md

## Validation

```text
ana_governance_check.py => PASS 116/116, report governance_check_20260531_221127.json; pytest autonomy+patch advisor => 22 passed
```

## Risks

- Docs-only alignment. Live behavior WARN remains expected until ANA MCP restart.

## Lab/Release Sync Status

mother-lab only; public/repo pending
