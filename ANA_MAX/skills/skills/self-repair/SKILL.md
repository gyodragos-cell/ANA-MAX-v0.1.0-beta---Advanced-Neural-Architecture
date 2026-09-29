# Skill: self-repair

## Version
1.0.0

## Context

The self-repair skill enables ANA MAX OS v2 to diagnose runtime errors and apply
targeted patches with rollback capability. It is the only mutating skill in the
standard registry and is therefore **rate-limited to 3 repair sequences per session**.

**Security classification:** Mutating. Rate-limited. Requires explicit `target` and
`error_pattern` in payload. All patches are logged with SHA-256 checksums for audit.

**White-hat boundary:** This skill does NOT perform autonomous code execution.
It produces a structured `tool_chain` that the agent executes step-by-step,
with explicit verification at each stage. The engine itself never calls `eval()`
or `exec()`.

## Scop

Provide a structured, auditable repair workflow for:

- Python import errors (missing modules, wrong paths)
- Config validation failures (malformed YAML/JSON)
- Tool registration errors (tools that fail smoke tests)
- Backend connectivity regressions (Ollama, MCP bridge)

Out of scope: OS-level repairs, security patch application, database migrations.

## Structura directoare

```
ANA_MAX/
├── skills/
│   └── skills/
│       └── self-repair/
│           └── SKILL.md          ← this file
├── tools/
│   ├── error_radar_tool.py       ← error pattern scanning
│   ├── file_patch_tool.py        ← atomic patch application + rollback
│   └── smoke_test_runner.py      ← post-repair verification
├── logs/
│   └── *.log                     ← error scan source
└── backups/
    └── patches/                  ← rollback snapshots (auto-created)
```

## Componente OS v2

1. **SkillEngine** (`skills/skill_engine.py`) — rate-limit enforcement, audit
2. **error_radar_tool** (`tools/error_radar_tool.py`) — error pattern detection
3. **file_patch_tool** (`tools/file_patch_tool.py`) — atomic patch + rollback
4. **smoke_test_runner** (`tools/smoke_test_runner.py`) — post-repair verification
5. **session_checkpoint_tool** (`tools/session_checkpoint_tool.py`) — state snapshot before patch

## Discipline OS v2

- **Atomicity**: Every patch creates a backup before mutation; rollback is always possible
- **Verification-first**: `smoke_test_runner` MUST succeed before repair is marked complete
- **Rate limiting**: Max 3 repair sequences per session (enforced by SkillEngine)
- **Audit trail**: Each repair logged with trace_id, target file, patch checksum, timestamp
- **Fail-safe**: On smoke test failure after patch, automatic rollback is triggered
- **No blind mutation**: `error_radar_tool` scan MUST precede any `file_patch_tool` call

## Taskuri pentru implementare

### A. Pre-flight check

Before returning tool_chain, verify:
- `target` payload field is a valid file path (not empty, not a directory)
- `error_pattern` is a non-empty string
- Rate limit not exceeded (`_CALL_COUNTS.get("self.repair", 0) < 3`)

### B. Error diagnosis

Return `tool_chain[0]`:
```json
{"tool": "error_radar_tool", "action": "scan", "args": {"pattern": "<error_pattern>", "target": "<target>"}}
```
Agent executes this first. If scan returns 0 matches, repair is unnecessary — stop.

### C. Session checkpoint

Return `tool_chain[1]`:
```json
{"tool": "session_checkpoint_tool", "action": "save", "args": {"label": "pre_repair_<trace_id>"}}
```
Creates a named restore point before any mutation.

### D. Patch application

Return `tool_chain[2]`:
```json
{"tool": "file_patch_tool", "action": "apply", "args": {"target": "<target>", "backup": true}}
```
`backup: true` is mandatory — ensures rollback snapshot exists.

### E. Verification

Return `tool_chain[3]`:
```json
{"tool": "smoke_test_runner", "action": "run", "args": {"target": "<target>"}}
```
If smoke test fails → trigger rollback (tool_chain[4]).

### F. Rollback (conditional)

Return `tool_chain[4]`:
```json
{"tool": "file_patch_tool", "action": "rollback", "args": {"target": "<target>"}}
```
Only executed if step E fails.

## Reguli pentru Codex

- NEVER proceed to patch application without a completed error scan (step B)
- NEVER skip the session checkpoint (step C) — it enables safe rollback
- `backup: true` is NOT optional in file_patch_tool — enforce it unconditionally
- If rate limit is reached, return a clear `rate_limited` status — do NOT suggest workarounds
- All repair operations MUST reference the `trace_id` for audit correlation
- Do NOT attempt to repair files in `ANA_MAX/venv/` — those are managed by pip
- Do NOT attempt to repair `ANA_MAX/config/settings.yaml` without explicit operator approval
- Log each step outcome to session log with timestamp and patch checksum

## Output asteptat

```json
{
  "status": "success",
  "capability": "self.repair",
  "trace_id": "skill.self_repair.a1b2c3d4",
  "elapsed_ms": 8.3,
  "data": {
    "repair_context": {
      "target": "ANA_MAX/tools/some_tool.py",
      "error_pattern": "ImportError: No module named 'xyz'",
      "strategy": "analyze → patch → verify → rollback_if_failed"
    },
    "tool_chain": [
      {"tool": "error_radar_tool",        "action": "scan",     "args": {"pattern": "ImportError"}},
      {"tool": "session_checkpoint_tool", "action": "save",     "args": {"label": "pre_repair_a1b2c3d4"}},
      {"tool": "file_patch_tool",         "action": "apply",    "args": {"target": "ANA_MAX/tools/some_tool.py", "backup": true}},
      {"tool": "smoke_test_runner",       "action": "run",      "args": {"target": "ANA_MAX/tools/some_tool.py"}},
      {"tool": "file_patch_tool",         "action": "rollback", "args": {"target": "ANA_MAX/tools/some_tool.py"}}
    ],
    "rollback_supported": true,
    "max_patches_this_session": 3,
    "patches_used_this_session": 1
  },
  "error": null,
  "audit": {
    "trace_id": "skill.self_repair.a1b2c3d4",
    "capability": "self.repair",
    "actor": "agent",
    "timestamp_utc": "2026-08-05T17:00:00+00:00",
    "elapsed_ms": 8.3,
    "call_count": 1
  }
}
```
