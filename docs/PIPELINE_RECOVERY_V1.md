# Pipeline Recovery v1

`pipeline_recovery.py` adds metadata-only recovery planning for OS-21
distributed pipeline skeletons.

## What it includes

- Phase checkpoints
- Shard checkpoints
- Retry queue metadata
- Shard state metadata
- Task migration candidates
- Compact recovery summaries

## Current behavior

- Local only
- Simulated only
- Metadata only
- Deterministic ordering
- No task execution
- No transport activity
- No file writes

## Usage

```powershell
python -m ANA_MAX.distributed.pipeline_recovery --summary
python -m ANA_MAX.distributed.pipeline_recovery --failed-task task-2 --failed-shard shard:node-1 --max-retries 3
```

## OS-21 alignment

- Distributed runtime: models task migration and shard recovery before real transport exists.
- Multi-agent kernel: preserves scheduled task IDs and shard assignments as recovery metadata.
- Reasoning graph: keeps recovery compatible with the distributed pipeline and graph builder.
- Self-healing: creates safe recovery plans without applying mutations.
