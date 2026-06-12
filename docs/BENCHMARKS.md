# Benchmarks

## 2026-06-10

- Direct bridge benchmark command: `python .\cascade_integration\direct_bridge.py --benchmark --iterations 3`
- Latest observed averages: `agent_coach` 123.641 ms, `tool_router` 7.106 ms, `file_operations` 8.22 ms.
- MCP comparison skipped by default in local-only mode.
- OS-4 bounded daemon run: `python -m ANA_MAX.self_optimization.os4_daemon --interval-seconds 1 --max-cycles 2`
- Observed runtime: 60.49 s, PASS.
- Self-evolution fast-parallel refresh: `python -m ANA_MAX.self_optimization.self_evolution_engine --fast-parallel --max-workers 3 --timeout 180`
- Observed runtime: 16.01 s, PASS.
- Smoke-level OS-4 commands for reasoning, toolchain discovery, and graph history are validated in `docs/TEST_REPORT.md`.

## 2026-06-10 02:54

- Full direct tool benchmark command: `.\scripts\ana_benchmark_tools.ps1 -Iterations 1 -Json`
- All benchmark payloads succeeded after correction.
- Fast tools: `privacy_shield` 5.215 ms, `code_search` 5.839 ms, `tool_router` 6.302 ms, `file_operations` 6.891 ms.
- Slow tools: `system_control` 1015.552 ms, `tool_healthcheck` 1158.456 ms.
- Next optimization target: avoid slow health/vitals calls in frequent loops unless explicitly requested.

## 2026-06-10 02:58

- Filesystem scan command: `.\scripts\ana_filesystem_health.ps1 -Apply -Json`
- Scanned files: 7319.
- Large files: 0.
- Cleanup candidates: 0.
- Duplicate groups: 812.

## 2026-06-10 03:04

- Profile command: `.\scripts\ana_profile_tool.ps1 -Tool agent_coach -Iterations 3 -Json`
- `agent_coach` avg tool latency: 93.212 ms.
- `agent_coach` avg CLI process latency: 12194.271 ms.
- Startup overhead dominates one-shot CLI profiling.

## 2026-06-10 06:55

- `python -m ANA_MAX.self_optimization.self_evolution_engine --cycle`: 17.33 s, PASS.
- `python -m ANA_MAX.self_optimization.self_evolution_engine --fast-parallel --max-workers 3 --timeout 180`: 77.00 s, PASS.
- `python -m ANA_MAX.self_optimization.self_evolution_engine --health-monitor --max-cycles 1 --interval 1 --timeout 180`: 0.20 s, PASS.
- `python -m ANA_MAX.self_optimization.self_evolution_engine --auto-evolution --max-cycles 1 --interval 1 --timeout 180`: 57.37 s, PASS.
- Note: `--fast-parallel` covers more engines than `--cycle`; compare only after aligning phase sets.

## 2026-06-10 07:45:11

- `python -m compileall -q ANA_MAX`: 7.4 s, PASS.
- `python -m ANA_MAX.self_optimization.architecture_executor --dry-run`: 0.4 s, PASS.
- `python -m ANA_MAX.self_optimization.global_orchestrator --dry-run`: 0.4 s, PASS.
- `python -m ANA_MAX.self_optimization.enterprise_orchestrator --dry-run`: 0.4 s, PASS.
- `python -m ANA_MAX.self_optimization.os4_daemon --interval-seconds 1 --max-cycles 2`: 60.3 s, PASS, 18 total phases, 0 failures.

## 2026-06-10 07:27

- `python -m ANA_MAX.self_optimization.self_profiling_engine --cycle`: 2.55 s, PASS.
- `python -m ANA_MAX.self_optimization.self_healing_engine --cycle`: 12.32 s, PASS.
- `python -m ANA_MAX.self_optimization.self_skills_engine --cycle`: 1.56 s, PASS.
- `python -m ANA_MAX.self_optimization.self_evolution_engine --cycle`: 8.57 s, PASS.
- `python -m ANA_MAX.self_optimization.multi_agent_orchestrator --cycle`: 22.98 s, PASS.
- `.\scripts\ana_quick_check.ps1 -Iterations 1 -Json`: PASS; direct avg ms `agent_coach` 6.768, `tool_router` 2.154, `file_operations` 3.384.

## 2026-06-10 - Memory Benchmarks

- `python -m ANA_MAX.self_optimization.memory_consolidation_engine --cycle`: 10.82 ms, PASS.
- `python -m ANA_MAX.self_optimization.self_consistency_engine --cycle`: 2.87 ms, PASS.
- `python -m ANA_MAX.self_optimization.self_reasoning_engine --cycle`: 9.62 ms, PASS.
- `python -m ANA_MAX.self_optimization.self_evolution_engine --fast-parallel --max-workers 3 --timeout 180`: 36.7 s, PASS.
- `python -m ANA_MAX.self_optimization.os4_daemon --interval-seconds 1 --max-cycles 1`: 50.9 s, PASS.

## 2026-06-10 - OS-20 Context Bundle

- `python -m compileall -q ANA_MAX\context ANA_MAX\self_optimization\personal_ai_studio.py`: PASS.
- `python -m ANA_MAX.context.context_injector`: PASS, exports `ana.context.export.v1` with bundle schema `ana.context.bundle.v1`.
- `python -m ANA_MAX.self_optimization.personal_ai_studio --dry-run`: PASS, OS-20 summary remains `overall_success=true`.
