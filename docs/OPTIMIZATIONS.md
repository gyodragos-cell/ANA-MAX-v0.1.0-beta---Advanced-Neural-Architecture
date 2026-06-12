# Optimizations

## 2026-06-11 - OS-22 Launch Readiness

- Added a single launch audit command so future agents do not re-check Python, requirements, model files, doctor, boot, and focused tests by hand.
- Kept the audit metadata-only and model-free by default; real model smoke remains a separate explicit launch validation.
- Classified `beautifulsoup4` as optional because the active OS-22 Web Learning path uses standard-library extraction.
- Kept `ANA_LOCAL_LLM_ENABLED=0` non-blocking because explicit launch scripts pass the local backend and model path without altering the stable OS-20.1 default runtime.

## 2026-06-10 - Agent Runtime Readability

- Added an encoding normalizer so local agents and PowerShell can read active docs/scripts without BOM, diacritic, emoji, or mojibake noise.
- Kept browser automation optional so local agents can still inspect pages through HTTP fallback when Playwright browsers are missing.
- Preserved direct bridge startup latency by not adding browser tooling to the stable 14-tool core set.

## 2026-06-10

- Prefer direct execution for `agent_coach`, `tool_router`, and read-only file inspection.
- Keep benchmark iterations small during interactive work; increase only during profiling sessions.
- Use `scripts/ana_maintenance.ps1` to monitor log/cache growth before it affects local I/O.
- Archive old logs to `ANA_MAX/sandbox/log_archive/` instead of deleting them.
- Rotate oversized active logs into `ANA_MAX/sandbox/log_archive/rotated_*` and recreate empty stubs for continued writes.
- Compress archived log directories with `scripts/ana_maintenance.ps1 -CompressArchive -Apply`.
- Use `scripts/ana_log_compress.ps1` for repeatable incremental compression and retention cleanup.
- Use `scripts/ana_benchmark_tools.ps1` to identify slow direct tools before optimizing.
- Avoid calling `system_control operation=vitals` and `tool_healthcheck scope=safe` inside high-frequency loops; both measure above 1 second.
- Use `scripts/ana_filesystem_health.ps1` to monitor large files, duplicate groups, old files, and cleanup candidates.
- Treat duplicate groups under `node_modules`, `.pytest_cache`, and sandbox snapshots as low-priority unless disk pressure rises.
- For high-frequency direct tool calls, prefer a persistent process/in-process bridge over repeated `python direct_bridge.py --execute` invocations.
- Use `python -m ANA_MAX.self_optimization.self_evolution_engine --health-monitor --max-cycles 1` as the cheapest OS-3 status probe.
- Use `--fast-parallel` for broad OS-3 refreshes; keep `--cycle` as the safest deterministic default.
- Use `--auto-evolution --max-cycles N --interval S` for scheduled local lab bursts instead of unbounded loops.
- Use `python -m ANA_MAX.self_optimization.self_reasoning_engine --cycle` to derive local hypotheses and priorities from existing evaluation artifacts before broader changes.
- Use `python -m ANA_MAX.tools.toolchain_discovery --dry-run` when you need a safe manifest of active and archived tools without enabling anything.
- Use `knowledge_graph_history/` diffs to compare graph evolution instead of reconstructing context from scratch.
- Keep `os4_daemon` bounded with `--max-cycles N`; reserve `--max-cycles 0` for explicit supervised continuous runs.
- `self_evolution_engine.py` now carries OS-4 snapshot metadata additively, so OS-3 `--cycle` remains the deterministic default.
- Lazy tool package loading reduces bridge startup fragility and avoids importing optional heavy tools during `tools.base` access.
- Active OS-3 scans exclude archives and sandbox snapshots, reducing false positives and scan time.

## 2026-06-10 04:58:27

### Safe Reorganization Proposals

- **move**: .qoder\skills\ana-max-tools\scripts\list_tools.py -> ANA_MAX/tools/list_tools.py
  Reason: Tool file should be in ANA_MAX/tools/
- **move**: .qoder\skills\ana-max-tools\scripts\test_connection.py -> tests/test_connection.py
  Reason: Test file should be in tests/ directory
- **move**: ana\smoke_test.py -> tests/smoke_test.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\integration\test_cooperation_module.py -> tests/test_cooperation_module.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\integration\test_mcp_server.py -> tests/test_mcp_server.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\integration\test_os_v2_flow.py -> tests/test_os_v2_flow.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\integration\test_unified_system.py -> tests/test_unified_system.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\unit\test_config_services.py -> tests/test_config_services.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\unit\test_event_bus.py -> tests/test_event_bus.py
  Reason: Test file should be in tests/ directory
- **move**: ana\tests\unit\test_fallback_sandbox.py -> tests/test_fallback_sandbox.py
  Reason: Test file should be in tests/ directory

## 2026-06-10 05:05:58

- Structuring remains dry-run by default.
- Mutations require explicit apply path and are logged to `ANA_MAX/logs/self_structuring_actions.jsonl`.
- Moves and archives create backups under `ANA_MAX/sandbox/structuring_backups/`.

## 2026-06-10 05:06:40

- Structuring remains dry-run by default.
- Mutations require explicit apply path and are logged to `ANA_MAX/logs/self_structuring_actions.jsonl`.
- Moves and archives create backups under `ANA_MAX/sandbox/structuring_backups/`.

## 2026-06-10 05:07:46

- Structuring remains dry-run by default.
- Mutations require explicit apply path and are logged to `ANA_MAX/logs/self_structuring_actions.jsonl`.
- Moves and archives create backups under `ANA_MAX/sandbox/structuring_backups/`.

## 2026-06-10 05:08:58

- Structuring remains dry-run by default.
- Mutations require explicit apply path and are logged to `ANA_MAX/logs/self_structuring_actions.jsonl`.
- Moves and archives create backups under `ANA_MAX/sandbox/structuring_backups/`.

## 2026-06-10 05:11:09


## 2026-06-10 05:12:06

### Integration Proposals

- **src_layout** (inspire)
  Target: ANA_MAX/
  Rationale: Consider src_layout pattern for ANA MAX structure
  Effort: low, Priority: low
- **network_pentest_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from tests\network_pentest_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **test_tool_router_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from tests\test_tool_router_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **setuptools_ext** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from .venv\Lib\site-packages\cffi\setuptools_ext.py for ANA MAX
  Effort: medium, Priority: medium
- **tool_support** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from .venv\Lib\site-packages\sqlalchemy\util\tool_support.py for ANA MAX
  Effort: medium, Priority: medium
- **adal_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\adal_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **adb_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\adb_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **agent_coach_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\agent_coach_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **ana_context_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\ana_context_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **autonomous_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\autonomous_tool.py for ANA MAX
  Effort: medium, Priority: medium

## 2026-06-10 - Memory Layer Optimizations

- Reused one bounded `memory_context` view across reasoning, evolution, and daemon flows to avoid duplicating artifact parsing.
- Kept memory snapshots compact by summarizing preferences, patterns, long-term keys, and consistency state instead of copying full artifacts into every report.
- Added bounded consolidation and consistency engines so memory drift can be detected without mutating the OS-3/OS-4 baseline.
- Preserved RAW-tagged output and local-only execution for all memory-aware flows.

## 2026-06-10 - OS-20 Context Output Optimization

- Added a shared context bundle so future agents can read one deterministic bootstrap source instead of re-parsing every memory artifact independently.
- Kept OS-20 CLI output bounded by returning summary fields and the bootstrap prompt while preserving the full report on disk.
- Avoided eager package imports in `ANA_MAX/context/__init__.py`, removing the `python -m ANA_MAX.context.context_injector` runtime warning.

## 2026-06-10 07:45

- Dry-run level reports now write to disk for OS-8, OS-9, and OS-10, closing the missing-artifact gap without mutating proposal or policy payloads.
- This keeps the orchestration ladder observable while preserving additive-only behavior for the actual apply artifacts.
- The OS-5OS-10 stack stayed local-only and bounded, so report persistence does not increase external coupling.

## 2026-06-10 05:12:46

### Integration Proposals

- **src_layout** (inspire)
  Target: ANA_MAX/
  Rationale: Consider src_layout pattern for ANA MAX structure
  Effort: low, Priority: low
- **network_pentest_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from tests\network_pentest_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **test_tool_router_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from tests\test_tool_router_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **setuptools_ext** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from .venv\Lib\site-packages\cffi\setuptools_ext.py for ANA MAX
  Effort: medium, Priority: medium
- **tool_support** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from .venv\Lib\site-packages\sqlalchemy\util\tool_support.py for ANA MAX
  Effort: medium, Priority: medium
- **adal_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\adal_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **adb_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\adb_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **agent_coach_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\agent_coach_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **ana_context_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\ana_context_tool.py for ANA MAX
  Effort: medium, Priority: medium
- **autonomous_tool** (adapt)
  Target: ANA_MAX/tools/
  Rationale: Adapt tool pattern from ANA_MAX\tools\autonomous_tool.py for ANA MAX
  Effort: medium, Priority: medium
## 2026-06-10 - Final Lab Stabilization

- `habit_routine_engine.py` false negatives were removed by switching from memory-relative doc scans to workspace-relative doc scans.
- Memory consolidation and consistency checks now feed back into the same bootstrap context that OS-20 consumes, so follow-up runs see the stable state immediately.
