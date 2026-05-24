# PATCH_START v19_phase4
# ANA MAX Tools

Current public baseline:

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

## v19 Diagnostics

The v19 Self-Aware Runtime adds three read-only diagnostics tools:

- `ana_runtime_inspector` - runtime snapshot and environment comparison.
- `tool_contract_validator` - safe, allowlisted tool contract checks.
- `schema_diff` - schema/response comparison for missing, extra, and type
  mismatch fields.

These diagnostics are manual tools. They do not auto-run, patch files, or
modify runtime state.
# PATCH_END v19_phase4
