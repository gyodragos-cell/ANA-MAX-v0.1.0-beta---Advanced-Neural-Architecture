# Session Checkpoint - 2026-05-31T21:20:43+00:00

## Autonomy WARN example aligned

## Summary

Updated the Autonomy Runner WARN follow-up example so pure live_behavior stale guidance recommends direct ANA MCP restart plus Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass, instead of generic restart/reload wording.

## Current Goal

Keep ANA MAX operator examples and diagnostics aligned around precise MCP restart guidance.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- docs/examples/AUTONOMY_RUNNER_WARN_FOLLOWUP_EXAMPLE.md

## Validation

```text
python -m pytest tests/runtime/test_ana_autonomy_runner.py tests/runtime/test_ana_lab_state_summary.py tests/runtime/test_ana_reload_consistency_check.py -q => 20 passed; reload consistency aligned=True with shared Restart ANA MCP next_action
```

## Risks

- No MCP restart was performed. Live behavior WARN remains expected until restart.

## Lab/Release Sync Status

mother-lab only; public/repo pending
