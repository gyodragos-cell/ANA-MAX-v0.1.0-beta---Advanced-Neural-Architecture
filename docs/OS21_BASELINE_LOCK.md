# OS-21 Baseline Lock

`os21_baseline_lock.py` builds the final metadata-only OS-21 baseline report.

## What it verifies

- Browser pack metadata
- Browser recon agent
- Web recon orchestrator
- Capsule schema, store, merge, and sync
- Reasoning graph builder and query API
- Agent scheduler
- Distributed pipeline and recovery planner
- Web scraper and web recon agents
- Agent capability registry
- Tool virtualization contracts

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No tool execution
- No transport execution
- No memory mutation
- No OS-20.1 runtime changes

## Usage

```powershell
python -m ANA_MAX.kernel.os21_baseline_lock --summary
python -m ANA_MAX.kernel.os21_baseline_lock --validate
python -m ANA_MAX.kernel.os21_baseline_lock --cycle
```

## Finalization rule

The baseline is considered locked only when:

- `status` is `PASS`
- `overall_success` is `true`
- `failed_module_count` is `0`
- OS-21 focused tests pass
- Compile and ASCII checks pass
