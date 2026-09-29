# Skill: health-check

## Version
1.0.0

## Context

The health-check skill provides a structured, non-mutating snapshot of ANA MAX OS v2
system health. It is the first skill called in any session startup sequence and serves
as the baseline for all subsequent operations.

**Security classification:** Read-only. Zero mutations. Safe to call at any frequency.

**Compliance:** Every component check is sandboxed — no direct FS mutations, no
subprocess escalation, no network writes.

## Scop

Detect degraded or failed components before they propagate into task failures:

- Verify the ANA tool registry is loaded and reports expected tool count (≥ 50)
- Verify Ollama connectivity and model availability on 127.0.0.1:11434
- Check skill engine registration state (≥ 1 capability registered)
- Sample memory pressure (alert if RAM > 90%)
- Report overall system status: `healthy` | `degraded` | `unhealthy`

Out of scope: performance benchmarking, log rotation, filesystem scanning.
Those are handled by `fs.inspect` and the maintenance scripts.

## Structura directoare

```
ANA_MAX/
├── skills/
│   └── skills/
│       └── health-check/
│           └── SKILL.md          ← this file
├── config/
│   └── skills.yaml               ← capability registration
├── tools/
│   ├── base.py                   ← ToolRegistry
│   └── skill_tool.py             ← ANA tool that exposes this skill
└── core/
    └── backends/
        └── ollama_backend.py     ← Ollama connectivity
```

## Componente OS v2

1. **SkillEngine** (`skills/skill_engine.py`) — dispatches and audits execution
2. **ToolRegistry** (`tools/base.py`) — source of truth for registered tools
3. **OllamaBackend** (`core/backends/ollama_backend.py`) — LLM connectivity
4. **skill_tool** (`tools/skill_tool.py`) — ANA tool interface for agent access

## Discipline OS v2

- **Determinism**: Same inputs → same output structure (status fields never omitted)
- **Observability**: Every component check emits a named status entry + alert list
- **Fail-fast reporting**: First failed component sets `overall_status` to `degraded`
- **Zero mutation**: No writes, no subprocess escalation, no config changes
- **Structured output**: Always returns `SkillResult.to_dict()` schema

## Taskuri pentru implementare

### A. Check Python runtime

Verify Python version ≥ 3.10. Return `{"python": "healthy — 3.x.y"}`.

### B. Check tool registry

Import `tools.base.ToolRegistry`, call `list_tools()`, assert count ≥ 50.
On import failure, return `degraded` with exception string.

### C. Check Ollama connectivity

HTTP GET `$OLLAMA_HOST/api/tags` with 2-second timeout.
Do NOT import any backend module — use `urllib.request` directly to avoid
circular imports. Parse response for model list if reachable.

### D. Check skill engine

Access `SkillEngine.instance()._registry`. Report capability count.
Flag as `degraded` if 0 capabilities registered.

### E. Check memory pressure

Use `psutil.virtual_memory()` if available. Alert if `percent > 90`.
Degrade gracefully if psutil is not installed (report `unknown`).

### F. Compute overall_status

```
unhealthy  → 3+ alerts
degraded   → 1–2 alerts
healthy    → 0 alerts
```

### G. Return structured result

```json
{
  "overall_status": "healthy|degraded|unhealthy",
  "components": {"python": "...", "tool_registry": "...", "ollama": "...", "skill_engine": "...", "memory": "..."},
  "alerts": [],
  "metrics": {"skill_capabilities": 3}
}
```

## Reguli pentru Codex

- NEVER block on network calls longer than 2 seconds — use timeout parameter
- DO NOT import `core.backends.*` inside the handler — use urllib.request for Ollama
- DO NOT write to disk, modify config, or start processes during health check
- If any component raises an unexpected exception, catch it, log it, mark component
  as `"degraded — <exception type>"`, add to alerts, and continue — never re-raise
- Output MUST always include all 5 component keys even if some are `"unknown"`
- Use `logger.info` for healthy components, `logger.warning` for degraded/unknown

## Output asteptat

```json
{
  "status": "success",
  "capability": "health.check",
  "trace_id": "skill.health_check.a1b2c3d4",
  "elapsed_ms": 42.5,
  "data": {
    "overall_status": "healthy",
    "components": {
      "python": "healthy — 3.12.0",
      "tool_registry": "healthy — 89 tools",
      "ollama": "healthy",
      "skill_engine": "healthy — 3 capabilities",
      "memory": "healthy — 54.2% used"
    },
    "alerts": [],
    "metrics": {
      "skill_capabilities": 3
    }
  },
  "error": null,
  "audit": {
    "trace_id": "skill.health_check.a1b2c3d4",
    "capability": "health.check",
    "actor": "agent",
    "timestamp_utc": "2026-08-05T17:00:00+00:00",
    "elapsed_ms": 42.5,
    "call_count": 1
  }
}
```
