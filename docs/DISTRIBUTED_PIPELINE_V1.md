# Distributed Pipeline v1

`distributed_pipeline.py` is a metadata-only distributed runtime skeleton. It
combines the agent scheduler and reasoning graph into a local-only plan.

## What it includes

- Topology ingestion
- Deterministic agent scheduling
- Shard partitioning
- Dispatch simulation
- Aggregation and validation phases
- Optional hybrid transport abstraction metadata
- Recovery metadata through `pipeline_recovery.py`

## OS-21 alignment

- Distributed runtime: models local, hybrid, and placeholder transport modes
- Multi-agent kernel: uses the agent scheduler for deterministic assignments
- Reasoning graph: embeds the graph builder output into the pipeline plan

## Current behavior

- Local only
- Simulated only
- Metadata only
- No transport or execution side effects

## Recovery layer

`PipelineRecoveryPlanner` builds phase checkpoints, shard checkpoints, retry
queues, shard states, and task migration candidates. It is read-only and uses
schema `ana.os21.pipeline_recovery.v1`.
