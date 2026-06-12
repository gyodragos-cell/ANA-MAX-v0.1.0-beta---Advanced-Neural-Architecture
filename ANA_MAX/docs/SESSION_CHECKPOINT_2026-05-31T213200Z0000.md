# Session Checkpoint - 2026-05-31T21:32:00+00:00

## Patch Advisor local dirty-tree evidence

## Summary

Improved Patch Advisor so large dirty-tree evidence prefers local Dirty Tree classification over stale live Error Radar details. The advisor now reports dirty_tree_available/dirty_tree_total and includes local categories such as runtime and script counts, preventing undercounting while MCP live behavior awaits restart.

## Current Goal

Keep ANA MAX self-healing diagnostics evidence-based and robust even when live MCP tool behavior is stale.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- ANA_MAX/dev_artifacts/scripts/ana_patch_advisor.py
- tests/runtime/test_ana_patch_advisor.py
- docs/examples/PATCH_ADVISOR_EXAMPLE.md
- docs/AGENT_MEMORY.md
- docs/ANA_LAB_MASTER_CONTEXT.md

## Validation

```text
python -m pytest tests/runtime/test_ana_patch_advisor.py tests/runtime/test_ana_dirty_tree_report.py -q => 13 passed; focused live-behavior suite => 16 passed; no_reload_quality_gate.py => PASS 8/8 with expected live_behavior advisory
```

## Risks

- Live MCP still has known live_behavior WARN until restart. Patch Advisor remains suggest-only and read-only.

## Lab/Release Sync Status

mother-lab only; public/repo pending
