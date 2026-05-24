# PATCH_START v20_phase3
# ANA MAX Tools Overview - v20

Current public baseline:

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

<!-- # PATCH_START v20_final -->
v20.0.0-alpha finalizes this baseline with `autonomy_dashboard` as the manual
read-only dashboard for autonomy outputs.
<!-- # PATCH_END v20_final -->

## v20 Autonomy Layer

- `ana_health_check` - aggregate read-only runtime health report.
- `baseline_update_suggester` - suggests baseline updates without applying
  changes.
- `docs_generator` - generates documentation text previews without writing
  files.
- `ana_patch_suggester` - suggests patch diffs and risk without applying
  patches.
- `runtime_guard` - reports read-only runtime consistency checks.
<!-- # PATCH_START v20_phase5 -->
- `autonomy_dashboard` - renders a read-only HTML dashboard for v20 autonomy
  outputs.
<!-- # PATCH_END v20_phase5 -->

## Operating Rule

The v20 tools are manual, reversible, and non-invasive. They do not auto-run,
write files, apply patches, or change runtime behavior.
# PATCH_END v20_phase3

# PATCH_START v19_phase5
# ANA MAX Tools Overview

Current public baseline:

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

## v19 Diagnostics Tools

- `ana_runtime_inspector` - read-only runtime snapshot and environment diff.
- `tool_contract_validator` - read-only contract validation for safe probes.
- `schema_diff` - read-only schema and response comparison.

## Operating Rule

Diagnostics are manual tools. They do not run automatically and do not modify
runtime state, source files, bridge behavior, or existing tools.
# PATCH_END v19_phase5
