# Skill: fs-inspect

## Version
1.0.0

## Context

The fs-inspect skill provides comprehensive, read-only analysis of any directory
tree accessible to the ANA MAX process. It is used for workspace audits, duplicate
detection, dependency mapping, and pre-repair reconnaissance.

**Security classification:** Read-only. No writes, no subprocess calls.
Access is bounded by OS file permissions — the skill does NOT escalate privileges.

**Performance note:** Large trees (> 50,000 files) may take 10–30 seconds.
The scan is depth-first, synchronous. For very large trees use `large_file_reader`
for targeted inspection instead.

## Scop

- Count files, directories, and total size in a target path (recursive)
- Classify files by extension with frequency ranking (top 20)
- Flag large files (> 1 MB) for cleanup review
- Support scoped inspection via `max_depth` payload parameter
- Return structured JSON suitable for dashboard rendering or agent decision-making

Out of scope: content analysis, duplicate hashing, permission auditing.
Those require dedicated tools (`security_tool`, `code_search`).

## Structura directoare

```
ANA_MAX/
├── skills/
│   └── skills/
│       └── fs-inspect/
│           └── SKILL.md          ← this file
├── tools/
│   ├── files.py                  ← file_operations tool (FS primitives)
│   └── large_file_reader.py      ← chunked reading for large files
└── config/
    └── skills.yaml               ← capability registration
```

## Componente OS v2

1. **SkillEngine** (`skills/skill_engine.py`) — dispatch, audit, result wrapping
2. **Path.rglob** — built-in Python stdlib; no external tool dependency for basic scan
3. **file_operations** (`tools/files.py`) — used for targeted reads after scan
4. **large_file_reader** (`tools/large_file_reader.py`) — chunked access for flagged files

## Discipline OS v2

- **Read-only**: No `open(path, "w")`, no `os.remove()`, no `shutil.*` mutations
- **Determinism**: Same directory → same output structure (empty lists, not missing keys)
- **Bounded execution**: `max_depth` parameter prevents runaway recursion on deep trees
- **Permission graceful degradation**: `PermissionError` on any subtree → logged, skipped, not raised
- **Structured output**: All keys present even if values are empty/zero

## Taskuri pentru implementare

### A. Parse and validate payload

Extract from payload:
- `path` (str, required) — target directory or file path
- `max_depth` (int, optional, default: unlimited) — maximum recursion depth
- `include_hidden` (bool, optional, default: false) — include dotfiles/hidden dirs

Reject if `path` is empty or resolves outside allowed workspace.

### B. Resolve and validate target path

```python
target = Path(payload["path"]).resolve()
if not target.exists():
    return {"error": f"Path does not exist: {target}"}
```

### C. Recursive scan

Use `Path.rglob("*")` with optional depth check. For each item:
- `item.is_dir()` → increment `dir_count`
- `item.is_file()` → increment `file_count`, add `item.stat().st_size` to `total_size`
- Track extension frequency in `file_types: Dict[str, int]`
- Flag if `size > 1_000_000` bytes → append to `large_files`

Catch `PermissionError` per item, log warning, continue scan.

### D. Sort and truncate output

- `file_types`: top 20 by frequency, descending
- `large_files`: top 10 by size, descending, include relative path + size_bytes

### E. Return structured result

All keys must be present. No optional/nullable keys in output schema.

## Reguli pentru Codex

- NEVER use `os.walk` with shell=True — use `Path.rglob()` only
- NEVER read file contents during scan — only metadata (stat)
- `PermissionError` on any item → log as warning, skip item, do NOT raise
- `max_depth` MUST be respected: compare `len(item.relative_to(target).parts)` to limit
- Hidden files/dirs (names starting with `.`) are excluded by default unless `include_hidden=true`
- Output `path` field MUST be the resolved absolute path string
- `large_files` entries MUST use relative paths (relative to `path`)
- If target is a single file (not a directory), return single-file stat directly

## Output asteptat

```json
{
  "status": "success",
  "capability": "fs.inspect",
  "trace_id": "skill.fs_inspect.a1b2c3d4",
  "elapsed_ms": 1240.5,
  "data": {
    "path": "C:/Users/billy/Desktop/ana-manus/ANA_MAX",
    "file_count": 847,
    "directory_count": 92,
    "total_size_bytes": 158432100,
    "file_types": {
      ".py": 312,
      ".json": 95,
      ".md": 44,
      ".yaml": 12,
      ".txt": 8
    },
    "large_files": [
      {"path": "main.py", "size_bytes": 75121},
      {"path": "tools/context_bridge.py", "size_bytes": 39629}
    ]
  },
  "error": null,
  "audit": {
    "trace_id": "skill.fs_inspect.a1b2c3d4",
    "capability": "fs.inspect",
    "actor": "agent",
    "timestamp_utc": "2026-08-05T17:00:00+00:00",
    "elapsed_ms": 1240.5,
    "call_count": 1
  }
}
```
