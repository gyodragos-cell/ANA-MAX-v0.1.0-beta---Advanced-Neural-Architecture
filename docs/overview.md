# PATCH_START v20_phase3
# ANA MAX v20 Overview

ANA MAX v20.0.0-alpha adds a manual autonomy layer on top of the existing
diagnostics runtime.

<!-- # PATCH_START v20_final -->
The final v20 alpha includes the read-only `autonomy_dashboard` tool and keeps
the public baseline at 80 loaded tools.
<!-- # PATCH_END v20_final -->

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

The v20 layer is read-only, manual-call only, and does not auto-run.
# PATCH_END v20_phase3

# PATCH_START v19_phase4
# ANA MAX Overview

ANA MAX is a Windows-first local MCP runtime for agent workflows that need
files, terminal state, desktop awareness, diagnostics, and verification.

Current public release baseline:

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

The v19 Self-Aware Runtime integration adds manual read-only diagnostics:

- `ana_runtime_inspector`
- `tool_contract_validator`
- `schema_diff`

These tools improve release verification and runtime debugging without changing
existing tool behavior.
# PATCH_END v19_phase4
