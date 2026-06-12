# Agent Scheduler v1

`agent_scheduler.py` turns the current agent registry into a deterministic
schedule without executing any work.

## What it does

- Loads the local agent registry
- Orders agents by role
- Builds a deterministic task queue
- Assigns tasks to agents based on role hints
- Marks gated work when explicit enablement is required

## OS-21 alignment

- Multi-agent kernel: makes agent roles and assignments explicit
- Reasoning graph: emits scheduler nodes and assignment edges
- Distributed runtime: gives later pipeline slices a deterministic handoff plan

## Current behavior

- Local only
- Metadata only
- No work execution
- No OS-20.1 runtime changes

