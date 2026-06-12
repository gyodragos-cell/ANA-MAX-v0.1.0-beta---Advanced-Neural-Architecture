# ANA Memory

Durable operating notes for ANA DEV agents.

- Use local direct execution before scoped ANA work.
- Prefer `cascade_integration/direct_bridge.py` for lab checks.
- Keep MCP disabled unless explicitly profiling local overhead.
- Document significant changes in `docs/` immediately after verification.
- All agents must read `AGENTS.md` and follow the Universal Agent Protocol before work.
- Required startup docs: `PROJECT_SUMMARY.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and `ANA_MEMORY.md`.
- Required report format: `ACTION -> RESULT -> NEXT STEP`.
- `ANA_MAX/tools/__init__.py` must stay lazy-loaded; do not reintroduce eager imports of all tools.
- Placeholder modules are quarantined under `ANA_MAX/archives/placeholders_quarantine/`; do not recreate fake external dependency modules in active paths.
- OS-3 health scanners should exclude archives, sandbox snapshots, logs, memory DBs, venvs, and caches from active health scoring.
- OS-4 layers are additive and report-only by default: `self_reasoning_engine`, `toolchain_discovery`, `knowledge_graph_history`, and `os4_daemon` should not auto-enable tools.
- `toolchain_discovery.py` never registers tools automatically; dangerous tools stay report-only.
- `os4_daemon.py` should remain bounded with explicit `--max-cycles` unless the operator intentionally supervises continuous mode.
- Preserve the OS-3 baseline when evolving: health 100, warnings 0, direct bridge 14/14, skills parse_error_count 0.

## 2026-06-10 04:59:14

- Self-Expanding Skills Layer executed
- Detected 8 capability gaps
- Generated 7 total skills
- Skills manifest updated

## 2026-06-10 05:07:57

- Self-Expanding Skills Layer executed
- Detected 1 capability gaps
- Generated 7 total skills
- Skills manifest updated

## 2026-06-10 - Shared Memory Layer

- Use `ANA_MAX/self_optimization/memory_context.py` as the canonical way to read the bounded shared memory state.
- Read `ANA_MAX/memory/core_memory.json`, `self_consistency_report.json`, and `memory_system_report.json` before making reasoning, evolution, or daemon changes.
- Keep consolidation bounded: preferences, patterns, and long-term keys should stay compact and local-only.
- If memory context fails to load, fall back safely with `module_missing` or `failed_to_load` instead of mutating state blindly.

## 2026-06-10 - OS-20 Agent Bootstrap Context

- Use `ANA_MAX/context/context_injector.py` to build the current context bundle for new execution agents.
- Treat `bundle.summary.current_os_level` as the deterministic OS level signal; it selects the highest numeric PASS level report.
- `personal_ai_studio.py` now exposes the context summary and agent bootstrap prompt while keeping the full report in `ANA_MAX/memory/personal_ai_studio_report.json`.

## 2026-06-10 05:08:15

- Self-Expanding Skills Layer executed
- Detected 1 capability gaps
- Generated 7 total skills
- Skills manifest updated

## 2026-06-10 05:08:50

- Self-Expanding Skills Layer executed
- Detected 1 capability gaps
- Generated 7 total skills
- Skills manifest updated
## 2026-06-10 - Final Memory State

- Memory consolidation and self-consistency both returned clean results after the last sync cycle: `health_score=100`, `warning_count=0`, `parse_error_count=0`, `overall_consistent=true`.
- OS-21 is now the highest PASS level after the finalizer wrote `ANA_MAX/memory/os_level_OS21_report.json`, so the bootstrap context resolves to `current_os_level=OS-21`.
- The current memory history length is `2`, which is a good stable baseline for future additive work.

## 2026-06-10 - OS-21 Context Completion

- Use `ANA_MAX/kernel/os21_finalizer.py` as the canonical OS-21 stop marker.
- `ANA_MAX/memory/os21_final_report.json` is the detailed finalizer artifact.
- `ANA_MAX/memory/os_level_OS21_report.json` is the context-visible PASS artifact.
- Do not start OS-22 unless the operator explicitly asks for a new phase.

## 2026-06-10 - OS-21.5 Local Brain

- Use `ANA_MAX/local/local_llm_backend.py` as the optional local LLM adapter.
- `ollm` is not a hard dependency; missing backend must return metadata with `available=false`.
- `LocalBrainAgent` and `PipelineReasoningHelper` must stay deterministic unless inference is explicitly enabled.
- Keep Phi-3 Medium as primary model metadata and Phi-3 Mini as fallback model metadata.

## 2026-06-11 - Vector Memory And RAG Bridge

- Use `ANA_MAX/core/vector_memory.py` as the canonical SQLite-backed semantic memory store for local retrieval.
- Use `ANA_MAX/local/rag_bridge.py` for metadata-only ingest, retrieve, and context assembly.
- Use `LocalLLMBackend.infer_with_rag()` and `LocalBrainAgent` tool prompts to inject retrieved context into Phi-3 without changing the default `infer()` path.
- Keep vector memory and RAG bridge deterministic, local-only, and compatible with the existing `VectorMemoryTool` contract.

## 2026-06-11 - Dual Python Local LLM Setup

- Keep Python 3.12 as the main ANA MAX interpreter.
- Use Python 3.11 only inside `local_llm_env/` for optional OLLM and model inference.
- Helper scripts under `scripts/local_llm/` must remain dry-run unless `--apply` is explicitly passed.
- `.env.local_llm` defaults to `ANA_LOCAL_LLM_ENABLED=0`.

## 2026-06-10 - OS-20 Final Baseline

- `docs/OS20_FINAL_BASELINE.md` is the official OS-20 checkpoint for future agents.
- Baseline gate: `ana.full_auto_audit.v2` PASS, `health_score=100`, `warnings=0`, `parse_error_count=0`, `drift_detected=false`.
- Context files were refreshed from `ANA_MAX.context.context_injector`: `current_os_level=OS-20`, `os_report_count=20`, `stable_cycles=7`.
- Treat compatibility modules for `skill_engine`, `fallback_engine`, and `error_model` as non-mutating audit surfaces unless explicitly promoted later.
- Keep voice bridge text ASCII-safe: `chat_voice_bridge.py` and `live_voice_bridge.py` normalize queue and temp-file text before logging or speech fallback.

## 2026-06-10 - OS-21 Planning Notes

- `prompt.txt` and `prompt 2.txt` on the desktop were rewritten as ASCII-safe planning notes.
- `docs/OS21_PLAN.md` is now the canonical local plan for the OS-20.1 to OS-21 discovery path.
- Keep OS-21 work additive, local-only, and verified against the current OS-20 baseline before promotion.

## 2026-06-10 - OS-21 Recon Capsules

- Use `ANA_MAX/orchestrators/web_recon_orchestrator.py` as the planning-only handoff from `BrowserReconAgent` to future capsule storage.
- Use `ANA_MAX/knowledge/capsule_schema.py` and `ANA_MAX/knowledge/capsule_store.py` as the canonical recon capsule metadata layer.
- Keep capsule work metadata-only, JSON-friendly, and ASCII-safe until a future storage or sync slice is explicitly promoted.

## 2026-06-10 - OS-21 Reasoning Graph And Distributed Skeleton

- Use `ANA_MAX/graph/reasoning_graph_builder.py` as the canonical deterministic graph builder for agent, topology, capsule, and recon metadata.
- Use `ANA_MAX/agents/agent_scheduler.py` to create role-aware task assignments from the local agent registry.
- Use `ANA_MAX/distributed/distributed_pipeline.py` to combine the scheduler and graph builder into a simulated local-first pipeline.

## 2026-06-10 - OS-21.5 Capsule Sync

- Use `ANA_MAX/knowledge/capsule_merge.py` for deterministic three-way recon capsule merge planning.
- Use `ANA_MAX/knowledge/capsule_sync.py` for metadata-only capsule sync plans and in-memory previews.
- Treat `merge_required` as a planning state; do not auto-resolve scalar conflicts without an explicit higher-level policy.

## 2026-06-10 - OS-21.5 Reasoning Graph Query

- Use `ANA_MAX/graph/reasoning_graph_query.py` for read-only graph metadata lookups.
- Keep graph queries deterministic and bounded; missing node IDs should return empty result sets.
- Do not let query helpers execute tools, mutate graph artifacts, or change OS-20.1 runtime behavior.

## 2026-06-10 - OS-21.5 Pipeline Recovery

- Use `ANA_MAX/distributed/pipeline_recovery.py` for distributed pipeline recovery metadata.
- Recovery plans are checkpoint, retry, shard state, and migration metadata only.
- Do not treat migration candidates as real transport operations until an explicit execution layer is approved.

## 2026-06-10 - OS-21 Web Agents

- Use `ANA_MAX/agents/web_scraper_agent.py` for scraper tool planning without network execution.
- Use `ANA_MAX/agents/web_recon_agent.py` as the composition layer for browser recon, scraper metadata, and web recon orchestration.
- Keep active web agent modes review-only until a future execution layer is explicitly approved.

## 2026-06-10 - OS-21 Agent Capability Registry

- Use `ANA_MAX/kernel/agent_capability_registry.py` as the metadata-only OS-21 kernel registry.
- Agent capability registration must remain read-only and keep `execution_allowed=false` until an explicit execution layer is approved.
- Prefer capability and tool indexes from the registry instead of ad-hoc agent introspection in future OS-21 slices.

## 2026-06-10 - OS-21 Final Metadata Baseline

- Use `ANA_MAX/kernel/tool_virtualization_contracts.py` for sandboxed metadata contracts and no-op tool simulation.
- Use `ANA_MAX/kernel/os21_baseline_lock.py` as the OS-21 final metadata baseline gate.
- Treat OS-21 as metadata-finalized only when baseline lock returns `PASS`, compile succeeds, ASCII checks pass, and OS-21 focused tests pass.

## 2026-06-10 - OS-21 Finalized Stop Point

- Use `ANA_MAX/kernel/os21_finalizer.py` and `ANA_MAX/memory/os21_final_report.json` as the final OS-21 completion marker.
- OS-21 status is `FINALIZED`; OS-22 is not started.
- Do not start OS-22 unless the operator gives a new explicit instruction.
