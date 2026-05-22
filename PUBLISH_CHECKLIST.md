# GitHub And Marketplace Publish Checklist

This file is ASCII-only and public-safe. Do not add private workspace paths,
tokens, local shortcuts, screenshots with private content, or unpublished lab
notes.

Canonical public repository:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

## Pre-Release Verification

- [ ] `python -m compileall -q main.py core tools vscode_extension`
- [ ] `python main.py --test` reports `3 PASS / 0 FAIL`
- [ ] `python main.py --list-tools` reports `64 loaded tools`
- [ ] `python -m unittest discover -s tests -v` passes
- [ ] `.env` and `.license` are not tracked
- [ ] `.env.example` contains placeholders only
- [ ] No API keys, local database files, logs, or private memory stores are in
      the release
- [ ] Public docs use the canonical repository URL
- [ ] Large videos are hosted externally and linked from docs/site pages

## GitHub Release

- [ ] Tag: `v0.1.0-beta`
- [ ] Title: `ANA MAX v0.1.0-beta - Clean Public Release`
- [ ] Description mentions the current public baseline:

```text
64 loaded tools
4 premium-gated desktop control tools
9 AI Core adapters
MCP auth enabled by default
desktop_capture is free Vision AI
```

- [ ] Attach only public-safe release artifacts
- [ ] Do not attach private lab archives or local data

## VS Code Extension

Before packaging:

- [ ] `vscode_extension/package.json` has repository, homepage, and bugs links
      pointing to the canonical public repository
- [ ] `anaMax.mcpApiKey`, `anaMax.mcpHost`, and `anaMax.mcpPort` are documented
- [ ] `vscode_extension/src/extension.js` sends the Bearer token for tool calls
- [ ] `ANA MAX: Open Documentation` opens the canonical public repository

Package:

```powershell
cd vscode_extension
npm.cmd run package
```

Or use the safe helper from the repository root:

```powershell
.\scripts\publish_vscode_extension.ps1
.\scripts\publish_vscode_extension.ps1 -Publish
```

Verify the VSIX:

```powershell
python -m zipfile -l .\advanced-neural-architecture-0.2.0.vsix
```

## Documentation

- [ ] `README.md`
- [ ] `SETUP_AND_RUN.md`
- [ ] `INSTALL_GUIDE.md`
- [ ] `docs/PROJECT_MAP_AI_GUIDE.md`
- [ ] `docs/USER_EXTENSION_INSTALL_AND_ETHICS.md`
- [ ] `docs/AI_COLLABORATION_AND_TOOLS.md`
- [ ] `CHANGELOG.md`
- [ ] `assets/VIDEO_MAP.md`

## Agent Handoff

Tell AI agents to:

```text
read docs/PROJECT_MAP_AI_GUIDE.md
use the canonical public repository URL
set MCP_API_KEY
start main.py
run tools/list
run the verification commands
report failures plainly
```

Do not tell agents to use private lab folders, old repo aliases, missing tools,
or hidden setup files.
