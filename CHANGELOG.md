# Changelog

## Current Clean Release

- Restored a clean public release boundary: private integration setup notes are
  not part of this repository.
- Added runtime premium gating in `ToolRegistry.execute()` so premium tools are
  blocked no matter whether they are called from CLI, HTTP, or MCP.
- Enabled MCP authentication by default in `main.py`; set `ANA_MCP_KEY` or
  `MCP_API_KEY` before calling tool endpoints.
- Added release-safe backing modules for `window_manager` and
  `clipboard_manager` so AI Core adapters are no longer phantom tools.
- Added `edge_tts_voice` as a release-safe voice tool. It registers cleanly and
  reports disabled if local TTS dependencies are unavailable.
- Updated agent rules and project map to require fact-based edits, no private
  workspace paths, and no documentation for missing tools.
- Added a release sync rule so code, docs, `.env.example`, tests, and release
  counts stay aligned when behavior changes.
- Added regression tests for runtime premium blocking and adapter backing
  modules.
- Documented `MCP_API_KEY` in `.env.example`.
- Rewrote the WorkGraph architecture note as ASCII-only guidance focused on
  observation-first agents, tool quality over tool count, and task-based Frida
  usage.
- Added `workspace_situational_awareness`, an observation-only WorkGraph tool
  that returns compact workspace JSON before an agent acts.
- Hardened `workspace_situational_awareness` after bug hunt: file paths now
  resolve to their parent repo, loose AI parameters fall back safely, and local
  absolute repo paths are not exposed in the snapshot.
- Repaired `index.html` for the public website: removed mojibake/emoji, aligned
  tool counts with the release baseline, documented MCP auth, and added it to
  release hygiene tests.

## Verification Baseline

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:
- Quick test: `3 PASS / 0 FAIL`
- Tool list: 64 loaded tools
- Unit tests: all tests passing
