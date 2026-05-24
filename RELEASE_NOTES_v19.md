# PATCH_START v19_phase5
# ANA MAX v19.0.0 Release Notes

## Release Summary

ANA MAX v19.0.0 introduces the Self-Aware Runtime diagnostics layer. The new
layer adds manual, read-only tools that help verify runtime state, validate
tool response contracts, and compare response objects against expected schemas.

## New Diagnostic Tools

- `ana_runtime_inspector` - returns runtime snapshots and compares development
  and release folders by file hash.
- `tool_contract_validator` - runs deterministic, allowlisted contract probes
  and reports PASS, WARN, or FAIL.
- `schema_diff` - compares an expected schema with an actual response and
  reports missing fields, extra fields, and type mismatches.

## Public Baseline

```text
Version: 19.0.0
Tools: 80 loaded tools
AI Core adapters: 7
Premium-gated families: 4
```

## Safety Notes

- Diagnostics are manual-call tools.
- Diagnostics do not auto-run.
- Diagnostics do not modify files.
- Diagnostics do not patch code.
- Diagnostics do not change existing tool behavior.

## Verification

Recommended release checks:

```powershell
python -m compileall -q main.py tools tests
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
python -m unittest discover -s tests\test_v19_phase1 -v
```

Expected key result:

```text
80 loaded tools
FAIL 0 in the ANA MAX bridge smoke and compatibility reports
```
# PATCH_END v19_phase5
