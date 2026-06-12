# Performance Log

## 2026-06-10

- Direct bridge health check completed successfully.
- Local mode confirmed with MCP disabled by default.
- OS-4 health stayed aligned with the OS-3 baseline: direct bridge 14/14, evaluation health 100, skills parse_error_count 0.
- Knowledge graph history snapshots are now being written under `ANA_MAX/memory/knowledge_graph_history/`.
- OS-4 daemon completed 2 bounded cycles and wrote `docs/OS4_DAEMON_LOG.md`.
- Self-evolution fast-parallel refresh remained stable while expanding beyond the sequential cycle path.


## 2026-06-10 02:20:39

- Daily check: True
- Smoke: 4 passed / 0 failed
- Benchmark avg ms: agent_coach 75.91, tool_router 5.613, file_operations 7.81
- Resources: disk_free_gb 158.79, memory_free_gb 8.15
- Maintenance: ana_logs_mb 19.199, pycache_mb 112.012, archive_candidates 0, large_log_candidates 0
- Next: Daily check PASS. Continue normal lab work.

## 2026-06-10 02:25:58

- Daily check: True
- Smoke: 4 passed / 0 failed
- Benchmark avg ms: agent_coach 88.49, tool_router 4.961, file_operations 6.258
- Resources: disk_free_gb 158.79, memory_free_gb 8.27
- Maintenance: ana_logs_mb 19.204, pycache_mb 112.012, archive_candidates 0, large_log_candidates 0
- Next: Daily check PASS. Continue normal lab work.

## 2026-06-10 02:29:00

- Planner: PASS, regenerated `docs/ROADMAP.md`.
- Maintenance: compressed 2 log archive directories.
- Post-plan priority: steady-state daily loop.
- Quick check: PASS, smoke 4 passed / 0 failed.
- Benchmark avg ms: agent_coach 87.659, tool_router 6.006, file_operations 6.826.

## 2026-06-10 02:54

- Full direct benchmark: PASS, all benchmark payloads succeeded.
- Slow direct tools: `system_control` 1015.552 ms, `tool_healthcheck` 1158.456 ms.
- Fast direct tools: `privacy_shield` 5.215 ms, `code_search` 5.839 ms, `tool_router` 6.302 ms.
- Planner: PASS, roadmap regenerated from current metrics and technical debt scan.

## 2026-06-10 02:58

- Filesystem health: PASS, scanned 7319 files.
- Large files above 100 MB: 0.
- Cleanup candidates `.tmp/.bak/.old`: 0.
- Duplicate groups: 812, mostly dependency/vendor/cache duplicates.
- Quick check: PASS, smoke 4 passed / 0 failed.

## 2026-06-10 03:04

- `agent_coach` profile: PASS.
- Average tool latency: 93.212 ms.
- Average process-level latency through CLI: 12194.271 ms.
- Conclusion: frequent loops should avoid repeated cold `python direct_bridge.py --execute`; persistent in-process bridge use is the optimization target.

## 2026-06-10 06:55

- Self-evolution sequential cycle: PASS in 17.33 s.
- Self-evolution fast-parallel broad refresh: PASS in 77.00 s with 3 workers.
- Self-evolution health monitor single sample: PASS in 0.20 s.
- Self-evolution auto-evolution single cycle: PASS in 57.37 s.
- Recommendation: use health monitor for frequent checks, sequential cycle for deterministic repair, fast-parallel/auto for broader scheduled refreshes.

## 2026-06-10 07:27

- Direct bridge restored to PASS: 14 loaded / 14 registered tools.
- OS-3 health score: 100 with 0 warnings and 0 suggestions.
- Active profiling scope after exclusions: 655 files, 151 Python files.
- Self-healing active scope: 151 files checked, 0 syntax failures.
- Knowledge graph expanded to 97 nodes and 933 edges.
- Quick check PASS; direct benchmark avg ms: `agent_coach` 6.768, `tool_router` 2.154, `file_operations` 3.384.

## 2026-06-10 04:55:06

### Tool Profiles

- **agent_coach**: avg 81.86ms, min 74.90ms, max 96.50ms, p95 96.50ms, success 100.0%
- **code_search**: avg 873.89ms, min 798.56ms, max 1092.20ms, p95 1092.20ms, success 100.0%
- **error_radar**: avg 111.64ms, min 103.13ms, max 131.09ms, p95 131.09ms, success 100.0%
- **file_operations**: avg 7.38ms, min 6.71ms, max 8.46ms, p95 8.46ms, success 100.0%
- **file_patch**: avg 107.69ms, min 91.27ms, max 137.96ms, p95 137.96ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.03ms, p95 0.03ms, success 0.0%
- **project_navigator**: avg 95.25ms, min 88.26ms, max 103.76ms, p95 103.76ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **smart_search**: avg 96.57ms, min 86.03ms, max 130.44ms, p95 130.44ms, success 0.0%
- **system_control**: avg 1014.95ms, min 1012.63ms, max 1018.41ms, p95 1018.41ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1161.42ms, min 1153.34ms, max 1170.62ms, p95 1170.62ms, success 100.0%
- **tool_router**: avg 6.91ms, min 6.21ms, max 7.73ms, p95 7.73ms, success 100.0%
- **workspace_situational_awareness**: avg 74.12ms, min 26.57ms, max 488.26ms, p95 488.26ms, success 100.0%

### System Profile

- CPU: 22.5%
- Memory: 72.7% (11.52GB used, 4.33GB available)
- Disk: 58.1% (213.04GB used, 153.94GB free)

### Performance Degradation Detected

- **code_search**: {
  "avg_latency_ms": 873.8928,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **tool_healthcheck**: {
  "avg_latency_ms": 1161.4168,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **system_control**: {
  "avg_latency_ms": 1014.9498,
  "threshold_ms": 500.0,
  "severity": "high"
}

## 2026-06-10 05:13:55

### Tool Profiles

- **agent_coach**: avg 6.20ms, min 5.77ms, max 6.82ms, p95 6.82ms, success 100.0%
- **code_search**: avg 767.23ms, min 684.19ms, max 856.06ms, p95 856.06ms, success 100.0%
- **error_radar**: avg 19.30ms, min 18.49ms, max 19.98ms, p95 19.98ms, success 100.0%
- **file_operations**: avg 7.38ms, min 6.56ms, max 8.73ms, p95 8.73ms, success 100.0%
- **file_patch**: avg 20.50ms, min 19.41ms, max 21.97ms, p95 21.97ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 19.90ms, min 18.50ms, max 20.90ms, p95 20.90ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.02ms, p95 0.02ms, success 0.0%
- **smart_search**: avg 19.36ms, min 17.63ms, max 22.27ms, p95 22.27ms, success 0.0%
- **system_control**: avg 1013.33ms, min 1010.81ms, max 1014.81ms, p95 1014.81ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1079.65ms, min 1066.17ms, max 1099.35ms, p95 1099.35ms, success 100.0%
- **tool_router**: avg 5.56ms, min 4.92ms, max 6.37ms, p95 6.37ms, success 100.0%
- **workspace_situational_awareness**: avg 72.83ms, min 33.36ms, max 220.92ms, p95 220.92ms, success 100.0%

### System Profile

- CPU: 3.8%
- Memory: 53.8% (8.53GB used, 7.32GB available)
- Disk: 58.1% (213.08GB used, 153.91GB free)

### Performance Degradation Detected

- **tool_healthcheck**: {
  "avg_latency_ms": 1079.6538,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **code_search**: {
  "avg_latency_ms": 767.2274,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **system_control**: {
  "avg_latency_ms": 1013.3262,
  "threshold_ms": 500.0,
  "severity": "high"
}

## 2026-06-10 05:14:57

### Tool Profiles

- **agent_coach**: avg 6.08ms, min 5.66ms, max 6.54ms, p95 6.54ms, success 100.0%
- **code_search**: avg 632.90ms, min 588.59ms, max 694.00ms, p95 694.00ms, success 100.0%
- **error_radar**: avg 24.33ms, min 21.25ms, max 26.95ms, p95 26.95ms, success 100.0%
- **file_operations**: avg 6.37ms, min 6.27ms, max 6.49ms, p95 6.49ms, success 100.0%
- **file_patch**: avg 18.13ms, min 16.18ms, max 21.42ms, p95 21.42ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 18.31ms, min 17.24ms, max 18.83ms, p95 18.83ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.03ms, p95 0.03ms, success 0.0%
- **smart_search**: avg 20.08ms, min 17.51ms, max 22.99ms, p95 22.99ms, success 0.0%
- **system_control**: avg 1013.35ms, min 1011.95ms, max 1014.38ms, p95 1014.38ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1077.28ms, min 1070.83ms, max 1085.92ms, p95 1085.92ms, success 100.0%
- **tool_router**: avg 6.03ms, min 4.96ms, max 8.53ms, p95 8.53ms, success 100.0%
- **workspace_situational_awareness**: avg 73.51ms, min 27.38ms, max 252.59ms, p95 252.59ms, success 100.0%

### System Profile

- CPU: 17.9%
- Memory: 56.1% (8.89GB used, 6.96GB available)
- Disk: 58.1% (213.08GB used, 153.91GB free)

### Performance Degradation Detected

- **code_search**: {
  "avg_latency_ms": 632.8958,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **tool_healthcheck**: {
  "avg_latency_ms": 1077.2804,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **system_control**: {
  "avg_latency_ms": 1013.349,
  "threshold_ms": 500.0,
  "severity": "high"
}

## 2026-06-10 05:15:59

### Tool Profiles

- **agent_coach**: avg 6.30ms, min 5.71ms, max 7.02ms, p95 7.02ms, success 100.0%
- **code_search**: avg 627.50ms, min 595.43ms, max 685.21ms, p95 685.21ms, success 100.0%
- **error_radar**: avg 21.72ms, min 21.35ms, max 22.62ms, p95 22.62ms, success 100.0%
- **file_operations**: avg 5.63ms, min 5.05ms, max 7.06ms, p95 7.06ms, success 100.0%
- **file_patch**: avg 20.13ms, min 17.98ms, max 23.11ms, p95 23.11ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 15.31ms, min 14.37ms, max 16.19ms, p95 16.19ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **smart_search**: avg 20.90ms, min 18.57ms, max 23.24ms, p95 23.24ms, success 0.0%
- **system_control**: avg 1011.83ms, min 1011.20ms, max 1012.86ms, p95 1012.86ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1084.86ms, min 1075.41ms, max 1110.79ms, p95 1110.79ms, success 100.0%
- **tool_router**: avg 6.22ms, min 5.27ms, max 7.29ms, p95 7.29ms, success 100.0%
- **workspace_situational_awareness**: avg 62.94ms, min 27.84ms, max 193.97ms, p95 193.97ms, success 100.0%

### System Profile

- CPU: 4.8%
- Memory: 54.5% (8.63GB used, 7.22GB available)
- Disk: 58.1% (213.08GB used, 153.91GB free)

### Performance Degradation Detected

- **code_search**: {
  "avg_latency_ms": 627.5002,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **tool_healthcheck**: {
  "avg_latency_ms": 1084.8566,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **system_control**: {
  "avg_latency_ms": 1011.8326,
  "threshold_ms": 500.0,
  "severity": "high"
}

## 2026-06-10 05:22:03

### Tool Profiles

- **agent_coach**: avg 6.36ms, min 6.03ms, max 6.49ms, p95 6.49ms, success 100.0%
- **code_search**: avg 965.50ms, min 872.39ms, max 1014.85ms, p95 1014.85ms, success 100.0%
- **error_radar**: avg 23.60ms, min 22.00ms, max 27.34ms, p95 27.34ms, success 100.0%
- **file_operations**: avg 7.27ms, min 6.46ms, max 7.76ms, p95 7.76ms, success 100.0%
- **file_patch**: avg 21.13ms, min 19.63ms, max 22.91ms, p95 22.91ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 19.84ms, min 18.89ms, max 20.31ms, p95 20.31ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **smart_search**: avg 18.45ms, min 17.17ms, max 19.88ms, p95 19.88ms, success 0.0%
- **system_control**: avg 1013.38ms, min 1012.15ms, max 1014.20ms, p95 1014.20ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1083.44ms, min 1073.32ms, max 1089.84ms, p95 1089.84ms, success 100.0%
- **tool_router**: avg 6.75ms, min 6.11ms, max 8.10ms, p95 8.10ms, success 100.0%
- **workspace_situational_awareness**: avg 70.54ms, min 32.29ms, max 216.09ms, p95 216.09ms, success 100.0%

### System Profile

- CPU: 28.8%
- Memory: 55.6% (8.81GB used, 7.05GB available)
- Disk: 58.1% (213.08GB used, 153.91GB free)

### Performance Degradation Detected

- **tool_healthcheck**: {
  "avg_latency_ms": 1083.4368,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **system_control**: {
  "avg_latency_ms": 1013.378,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **code_search**: {
  "avg_latency_ms": 965.5012,
  "threshold_ms": 500.0,
  "severity": "medium"
}

## 2026-06-10 05:52:38

### Tool Profiles

- **agent_coach**: avg 7.25ms, min 6.80ms, max 7.71ms, p95 7.71ms, success 100.0%
- **code_search**: avg 795.09ms, min 700.09ms, max 1002.51ms, p95 1002.51ms, success 100.0%
- **error_radar**: avg 25.22ms, min 24.28ms, max 27.15ms, p95 27.15ms, success 100.0%
- **file_operations**: avg 7.93ms, min 7.32ms, max 9.92ms, p95 9.92ms, success 100.0%
- **file_patch**: avg 20.14ms, min 19.06ms, max 21.21ms, p95 21.21ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 21.86ms, min 19.96ms, max 24.34ms, p95 24.34ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **smart_search**: avg 21.13ms, min 19.46ms, max 23.56ms, p95 23.56ms, success 0.0%
- **system_control**: avg 1015.53ms, min 1013.08ms, max 1019.72ms, p95 1019.72ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1090.76ms, min 1077.78ms, max 1102.80ms, p95 1102.80ms, success 100.0%
- **tool_router**: avg 6.36ms, min 5.62ms, max 8.00ms, p95 8.00ms, success 100.0%
- **workspace_situational_awareness**: avg 68.30ms, min 32.13ms, max 208.71ms, p95 208.71ms, success 100.0%

### System Profile

- CPU: 27.7%
- Memory: 41.4% (6.57GB used, 9.29GB available)
- Disk: 57.4% (210.76GB used, 156.22GB free)

### Performance Degradation Detected

- **code_search**: {
  "avg_latency_ms": 795.0868,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **system_control**: {
  "avg_latency_ms": 1015.5254,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **tool_healthcheck**: {
  "avg_latency_ms": 1090.7628,
  "threshold_ms": 500.0,
  "severity": "high"
}

## 2026-06-10 06:11:17

### Tool Profiles

- **agent_coach**: avg 6.08ms, min 5.62ms, max 6.40ms, p95 6.40ms, success 100.0%
- **code_search**: avg 763.25ms, min 691.85ms, max 894.47ms, p95 894.47ms, success 100.0%
- **error_radar**: avg 22.00ms, min 21.20ms, max 22.99ms, p95 22.99ms, success 100.0%
- **file_operations**: avg 7.40ms, min 6.73ms, max 8.09ms, p95 8.09ms, success 100.0%
- **file_patch**: avg 17.33ms, min 15.40ms, max 19.43ms, p95 19.43ms, success 0.0%
- **privacy**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **project_navigator**: avg 20.80ms, min 18.19ms, max 23.21ms, p95 23.21ms, success 0.0%
- **security_tool**: avg 0.01ms, min 0.01ms, max 0.01ms, p95 0.01ms, success 0.0%
- **smart_search**: avg 19.71ms, min 19.11ms, max 20.48ms, p95 20.48ms, success 0.0%
- **system_control**: avg 1015.43ms, min 1012.42ms, max 1022.50ms, p95 1022.50ms, success 100.0%
- **terminal**: avg 0.00ms, min 0.00ms, max 0.00ms, p95 0.00ms, success 0.0%
- **tool_healthcheck**: avg 1080.96ms, min 1077.32ms, max 1090.67ms, p95 1090.67ms, success 100.0%
- **tool_router**: avg 6.86ms, min 6.02ms, max 9.72ms, p95 9.72ms, success 100.0%
- **workspace_situational_awareness**: avg 719.06ms, min 33.12ms, max 3438.35ms, p95 3438.35ms, success 100.0%

### System Profile

- CPU: 21.3%
- Memory: 37.5% (5.95GB used, 9.90GB available)
- Disk: 57.4% (210.76GB used, 156.22GB free)

### Performance Degradation Detected

- **code_search**: {
  "avg_latency_ms": 763.2472,
  "threshold_ms": 500.0,
  "severity": "medium"
}
- **system_control**: {
  "avg_latency_ms": 1015.4272,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **tool_healthcheck**: {
  "avg_latency_ms": 1080.9568,
  "threshold_ms": 500.0,
  "severity": "high"
}
- **workspace_situational_awareness**: {
  "avg_latency_ms": 719.0598,
  "threshold_ms": 500.0,
  "severity": "medium"
}

## 2026-06-10 09:00:40

- Daily check: True
- Smoke: 4 passed / 0 failed
- Benchmark avg ms: agent_coach 4.822, tool_router 1.754, file_operations 3.264
- Resources: disk_free_gb 154.02, memory_free_gb 8.32
- Maintenance: ana_logs_mb 0.932, pycache_mb 116.299, archive_candidates 0, large_log_candidates 0
- Next: Daily check PASS. Continue normal lab work.

## 2026-06-10 07:45:11

- Compileall: 7.4 s, PASS across `ANA_MAX`.
- OS-4 daemon smoke: 60.3 s, PASS for 2 bounded cycles and 18 total phases.
- Dry-run level reports for OS-8/OS-9/OS-10 now persist on disk, which removed the validation-time artifact gap.

## 2026-06-10 - Memory Layer Metrics

- `memory_consolidation_engine --cycle`: 10.82 ms, PASS, core memory written and bounded history updated.
- `self_consistency_engine --cycle`: 2.87 ms, PASS, 0 contradictions and 0 regressions.
- `self_reasoning_engine --cycle`: 9.62 ms, PASS, memory context summary included in the report.
- `self_evolution_engine --fast-parallel --max-workers 3 --timeout 180`: 36.7 s, PASS, memory snapshot and phase-order hint preserved.
- `os4_daemon --interval-seconds 1 --max-cycles 1`: 50.9 s, PASS, memory summary populated with preferences, patterns, and long-term keys.

## 2026-06-10 - OS-20 Context Bundle Metrics

- `python -m compileall -q ANA_MAX`: PASS.
- `python -m ANA_MAX.context.context_injector`: PASS, RAW-tagged export, `current_os_level=OS-20`.
- `python -m ANA_MAX.self_optimization.personal_ai_studio --dry-run`: PASS, bounded RAW output, `overall_success=true`.
## 2026-06-10 - Final Verification Metrics

- `memory_consolidation_engine --cycle`: 11.4 ms, PASS, `health_score=100`.
- `self_consistency_engine --cycle`: 2.0 ms, PASS, `overall_consistent=true`.
- `context_injector --prompt-only`: 0.3 s, PASS, `current_os_level=OS-20`.
- `personal_ai_studio --dry-run`: 1.0 s, PASS, bounded output preserved.
- `self_evolution_engine --fast-parallel --max-workers 3 --timeout 180`: 19.5 s, PASS, `os8.ready=true`, `os10.ready=true`.

## 2026-06-10 - Memory Cleanup Verification

- Archived one stale temporary test DB into `ANA_MAX/sandbox/memory_cleanup_archive/` and kept active memory files intact.
- Restored `knowledge_graph_history/` and `evolution_strategy_history/` with fresh snapshots so the exported context can keep using bounded history instead of noisy leftovers.
- Re-ran `agent_startup_check.ps1`, `ana_quick_check.ps1`, `compileall`, and `OS20_BASELINE_LOCK.ps1 -RunRuntimeChecks` after the cleanup; all checks stayed green.

## 2026-06-10 - Encoding Sweep Verification

- `scripts/ana_encoding_normalize.py --root . --apply` normalized 3 text files and removed all BOM / non-ASCII findings in the active text scope.
- Follow-up scan reported `finding_count=0` and `changed_count=0`, confirming the remaining active docs and support text are ASCII-only.

## 2026-06-10 - Voice Path ASCII Hardening

- Sanitized the live voice queue and temp voice files to ASCII-only text.
- Updated the voice bridges so future queue reads and System.Speech temp files stay PowerShell-safe.
- Final follow-up scan still reported `finding_count=0` for the active workspace text surface.
