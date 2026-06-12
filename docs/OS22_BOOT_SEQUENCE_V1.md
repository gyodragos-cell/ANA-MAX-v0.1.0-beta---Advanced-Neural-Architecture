# OS-22 Boot Sequence v1

## Overview

`ANA_MAX/local/os22_boot.py` builds a deterministic boot and health report for
the OS-22 local brain stack without loading a model at import time or mutating
runtime state.

The boot sequence checks:

- local LLM backend metadata
- prompt engine availability
- RAG bridge readiness
- tool manifest and dispatcher readiness
- local brain agent metadata

## Report Shape

The boot report uses schema `ana.os22.boot_sequence.v1` and includes:

- `metadata_only`
- `local_only`
- `overall_success`
- `health_score`
- `profile_layer`
- `prompt_engine`
- `rag_bridge`
- `tool_bridge`
- `backend`
- `agent`

## Operating Rules

- No model load during import.
- No cloud calls.
- No tool execution during boot.
- No OS-21.5 baseline drift.
- Optional backend availability is reported, not required for import safety.

## CLI

```text
python -m ANA_MAX.local.os22_boot --summary
python -m ANA_MAX.local.os22_boot --validate
python -m ANA_MAX.local.os22_boot --write
python -m ANA_MAX.local.os22_boot --cycle
```

## Suggested Next Step

After a clean boot report, run a bounded `infer_with_rag()` smoke test that
confirms the manifest-backed `TOOL_CALL` prompt block reaches the model layer.
