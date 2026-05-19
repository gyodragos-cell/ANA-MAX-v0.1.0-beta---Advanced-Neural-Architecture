# ANA MAX

ANA MAX is a Windows-first AI agent runtime with MCP access to local tools:
files, code search, system checks, desktop vision, UI automation, memory, and
AI-core orchestration.

This repository is the clean public release. It must stay public-safe,
repeatable, and boring in the best possible way.

## Quick Start

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MCP_API_KEY = "change-me"
python main.py
```

ANA MAX starts on `http://127.0.0.1:8765` by default.

MCP auth is enabled by default. Send:

```text
Authorization: Bearer change-me
```

Example MCP request:

```powershell
curl -X POST http://127.0.0.1:8765/mcp `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer change-me" `
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Verification

Before handing off changes, run:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected baseline:

- `python main.py --test`: `2 PASS / 0 FAIL`
- `python main.py --list-tools`: 63 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

## Tool Model

Core tool behavior is owned by `tools/base.py`.

New tools must:

- inherit from `tools.base.Tool`;
- implement `get_definition()` and `execute()`;
- be registered from `main.py`;
- be importable from this clean repo;
- have docs only when the code and tests exist.

## Premium Gate

`desktop_capture` is free Vision AI.

These tools are premium-gated at runtime:

- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

Premium checks happen in `ToolRegistry.execute()`, so the gate applies through
CLI, HTTP, and MCP.

## Windows And PowerShell Text Rule

All commands, expected terminal output, log examples, and setup snippets in
public docs must be ASCII-only. Do not use Romanian diacritics, smart quotes,
emoji, or mojibake in shell-facing text.

Good:

```text
2 PASS / 0 FAIL
63 loaded tools
Authorization: Bearer change-me
```

Bad:

```text
mojibake text
non-ascii shell output
```

This is deliberate. Cheap agents and Windows consoles often stumble on encoded
text. Public docs should be simple enough that weak agents cannot misread them.

## Public Release Hygiene

Do not add private workspace notes, local IDE setup files, local shortcuts,
private tokens, logs, databases, or screenshots.

If a feature is experimental, keep it private until code, tests, docs, and
release hygiene are all present.

When behavior changes, update code, docs, `.env.example`, tests, and release
counts together. Users should never need private notes to know how the public
release works.

## License

MIT. Use automated desktop control only on machines you own or are allowed to
operate.
