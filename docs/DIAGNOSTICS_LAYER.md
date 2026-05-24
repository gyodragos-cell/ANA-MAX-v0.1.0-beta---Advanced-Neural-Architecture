# PATCH_START v20_phase3
# ANA MAX Diagnostics Layer - v20

ANA MAX v20.0.0-alpha extends diagnostics with a manual autonomy foundation.

## v20 Tools

- `ana_health_check`
- `baseline_update_suggester`
- `docs_generator`
- `ana_patch_suggester`
- `runtime_guard`

## v20 Safety Model

- Manual-call only.
- No auto-run.
- No file writes.
- No patch application.
- No bridge, adapter, core, or existing-tool behavior changes.
# PATCH_END v20_phase3

# PATCH_START v19_phase5
# ANA MAX Diagnostics Layer

ANA MAX v19.0.0 adds a Self-Aware Runtime diagnostics layer. The layer is
designed to help maintainers understand the runtime without changing it.

## Tools

### `ana_runtime_inspector`

Actions:

- `snapshot` - returns current working directory, port state, bridge PID when
  detectable, loaded module names, and hashes for selected runtime files.
- `compare_envs` - compares two folders by file hash and reports modified,
  missing, and extra files.

### `tool_contract_validator`

Actions:

- `validate_tool` - validates one allowlisted tool using a safe probe.
- `validate_all` - validates discoverable tools, reporting PASS, WARN, and
  FAIL without running risky probes.

### `schema_diff`

Inputs:

- `expected_schema`
- `actual_response`

Output:

- `missing`
- `extra`
- `type_mismatch`

## Safety Model

- Read-only.
- Deterministic.
- No auto-run.
- No auto-patching.
- No file modification.
- No bridge or core behavior changes.
# PATCH_END v19_phase5
