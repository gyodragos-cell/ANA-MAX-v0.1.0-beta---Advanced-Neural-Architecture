# OS-21 Plan

This document is the ASCII-safe action plan extracted from the two desktop prompt files.
It stays local-only, additive, and aligned with the current OS-20 baseline.

## Goal

Build OS-21 as a layered extension on top of OS-20.1 without changing stable OS-20 logic.

## Constraints

- Local only
- Standard library first
- Additive changes only
- No schema drift for existing OS-3 to OS-20 reports
- No MCP/cloud behavior by default
- No destructive automation

## Workstreams

### 1. Browser Expansion Pack

- Extend browser control in a safe hybrid mode.
- Keep default direct bridge counts unchanged.
- Add browser_open, browser_extract, browser_click, and other read-only helpers first.
- Require explicit confirmation for risky browser actions.

### 2. Web Agents

- Add scraper, recon, and browser-oriented helper agents.
- Keep scraping and extraction local-only and bounded.
- Prefer deterministic output and clear tool contracts.
- Keep web agents metadata-only until an explicit execution layer is approved.

### 3. Multi-Agent Kernel

- Add agent scheduler and coordinator layers.
- Add capability registration and a sandbox boundary.
- Keep agent routing explicit and observable.
- Add deterministic agent scheduling metadata before any execution layer.
- Use `agent_capability_registry.py` as the metadata-only kernel registry.

### 4. Knowledge Capsules

- Add bounded capsule store, sync, versioning, and security.
- Keep memory compact and local.
- Prefer snapshot and diff style updates.
- Use `ana.os21.recon_capsule.v1` for recon artifacts and pipeline handoffs.
- Use `capsule_sync.py` and `capsule_merge.py` for metadata-only sync planning and conflict handling.

### 5. Tool Virtualization

- Define tool capability contracts.
- Add tool sandboxing and isolation boundaries.
- Keep versioning explicit and deterministic.
- Use `tool_virtualization_contracts.py` for sandboxed metadata contracts and no-op simulations.

### 6. Distributed Runtime

- Model local, remote, and hybrid nodes as additive abstractions.
- Keep transport local-first and fake-transport friendly when real transport is absent.

### 7. Reasoning Graph

- Connect agent, tool, memory, and context graphs.
- Use graph output to guide next-step planning and cleanup.
- Build the graph from agent registry, distributed topology, recon pipeline, and capsule metadata.
- Query graph metadata by node type, agent, capsule URL, tool degree, and bounded paths.

### 8. Distributed Runtime

- Model local, hybrid, and placeholder remote nodes as additive abstractions.
- Keep transport local-first and fake-transport friendly.
- Derive shards and dispatch metadata from the scheduler and reasoning graph.
- Plan checkpoint, retry, shard state, and task migration metadata without executing transport.

### 9. Local Brain

- Add optional local LLM backend metadata for Phi-3 Medium and Phi-3 Mini through `ollm`.
- Keep local brain usage feature-checked and optional; ANA MAX must run without `ollm`.
- Use `LocalBrainAgent`, `PipelineReasoningHelper`, and `RAGBridge` for deterministic reasoning hints and optional memory-grounded prompt injection before any runtime promotion.

## Immediate Sequence

1. Stabilize OS-20.1 baseline.
2. Normalize the prompt files and keep them ASCII-safe.
3. Implement browser expansion pack.
4. Add browser recon agent metadata.
5. Add the web recon orchestrator metadata pipeline.
6. Add capsule schema and capsule store for recon artifacts.
7. Add the reasoning graph builder.
8. Add the distributed pipeline skeleton.
9. Add the agent scheduler.
10. Add capsule sync and merge conflict handling.
11. Add reasoning graph query API.
12. Add task migration and recovery metadata.
13. Add web agents for scraping and recon.
14. Add OS-21 kernel scaffolding.
15. Add knowledge capsules and tool virtualization.
16. Lock OS-21 baseline after tests, docs, and verification.
17. Add optional OS-21.5 local brain hooks without changing baseline runtime behavior.

## Current Completion State

- OS-21 metadata pillars are implemented as additive local layers.
- `os21_baseline_lock.py` is the final metadata-only baseline gate.
- Runtime execution remains blocked by default for all new OS-21 kernel contracts.
- `os21_finalizer.py` marks OS-21 as `FINALIZED` and writes `ANA_MAX/memory/os21_final_report.json`.
- OS-22 LLM Core work has started as the local brain and tool bridge slice; the OS-21 stop boundary remains documented in `docs/OS21_FINALIZATION.md`.
- OS-21.5 local brain hooks are optional and report metadata only when `ollm` is absent.

## Validation

- `python -m compileall -q ANA_MAX`
- direct bridge health check
- browser hybrid safety check
- dry-run smoke tests for new modules
- baseline lock verification before any promotion

## Design References

- Agent Zero: https://github.com/agent0ai/agent-zero
- Space Agent: https://github.com/agent0ai/space-agent
