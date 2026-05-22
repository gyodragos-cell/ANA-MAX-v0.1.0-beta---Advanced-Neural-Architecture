# ANA MAX Extension Publishing Guide

This guide is for packaging the public VS Code extension. Keep it public-safe:
no tokens, no private paths, no local screenshots, and no private lab notes.

## Current Baseline

```text
version: 0.2.0
extension: advanced-neural-architecture
public repo: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
tool count: 64 loaded tools
premium-gated tools: 4
desktop_capture: free Vision AI
```

## Before Packaging

- [ ] `package.json` has the correct `publisher`.
- [ ] `repository`, `homepage`, and `bugs` point to the canonical public repo.
- [ ] `src/extension.js` sends the MCP Bearer token.
- [ ] `ANA MAX: Open Documentation` opens the canonical public repo.
- [ ] `README.md` explains installation and MCP settings.
- [ ] `node --check src/extension.js` passes.

## Package

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1`:

```powershell
cd vscode_extension
npm.cmd run package
```

Expected output:

```text
advanced-neural-architecture-0.2.0.vsix
```

## Automated Helper

From the repository root, the safe helper packages and verifies the VSIX:

```powershell
.\scripts\publish_vscode_extension.ps1
```

Install the generated VSIX locally:

```powershell
.\scripts\publish_vscode_extension.ps1 -InstallLocal
```

Publish only when you are ready:

```powershell
.\scripts\publish_vscode_extension.ps1 -Publish
```

The helper does not store tokens. Use `vsce login` first, or set `VSCE_PAT`
only in the current shell when publishing.

If publishing fails with `Personal Access Token verification has failed`, open:

```text
https://marketplace.visualstudio.com/manage/publishers/
```

Create or select the correct publisher, generate a new Marketplace PAT for that
publisher, then run:

```powershell
vsce login <publisher-id>
.\scripts\publish_vscode_extension.ps1 -Publish
```

## Verify The VSIX

```powershell
python -m zipfile -l .\advanced-neural-architecture-0.2.0.vsix
```

Optional link check:

```powershell
python -c "import zipfile; z=zipfile.ZipFile('advanced-neural-architecture-0.2.0.vsix'); print('ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture' in z.read('extension/package.json').decode('utf-8'))"
```

## Publish

Marketplace publishing requires a publisher account and PAT. Do not commit the
PAT.

```powershell
vsce login your-publisher-id
vsce publish
```

Or publish an already-built VSIX:

```powershell
vsce publish --packagePath advanced-neural-architecture-0.2.0.vsix
```

## Support Links

- GitHub Issues:
  `https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/issues`
- Main setup guide: `..\SETUP_AND_RUN.md`
- User install guide: `..\docs\USER_EXTENSION_INSTALL_AND_ETHICS.md`
