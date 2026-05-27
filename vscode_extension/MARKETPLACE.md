# ANA MAX Marketplace Upload Notes

Use this checklist before publishing or updating the VS Code Marketplace
extension.

## Current Package

- Extension id: `d4d8176a-bb85-66ef-93dd-a58bc9ddfdad.ana-antigravity-chat`
- Display name: `ANA MAX - Hybrid AI Cockpit`
- Version: `1.0.9`
- Publisher in `package.json`: `d4d8176a-bb85-66ef-93dd-a58bc9ddfdad`
- Marketplace package built by VSCE:
  `vscode_extension\ana-antigravity-chat-1.0.9.vsix`
- Local/operator install package also available at:
  `ANA_MAX\ana-antigravity-hybrid-1.0.9.vsix`

## Upload Checklist

1. Open Visual Studio Marketplace publisher management:
   `https://marketplace.visualstudio.com/manage`
2. Select the publisher that matches `publisher` in `package.json`.
   For this package it must be `d4d8176a-bb85-66ef-93dd-a58bc9ddfdad`.
3. If the selected publisher has another name, update `vscode_extension/package.json`
   before packaging.
4. Upload `vscode_extension\ana-antigravity-chat-1.0.9.vsix`.
5. Confirm the marketplace page shows:
   - icon: ANA MAX icon;
   - display name: `ANA MAX - Hybrid AI Cockpit`;
   - author/credit: Dragos / gyodragos-cell with Codex;
   - repository and homepage links;
   - README sections: Quick Start, MCP Client Config, Safety Model;
   - preview flag enabled.

## Build Commands

From the repository root:

```powershell
node --check vscode_extension\extension.js
python -m json.tool vscode_extension\package.json
python ANA_MAX\dev_artifacts\scripts\package_cockpit_vsix.py
```

From `vscode_extension`:

```powershell
npx.cmd --yes @vscode/vsce ls
npx.cmd --yes @vscode/vsce package --no-dependencies
```

## Notes

- Do not upload old `ana-antigravity-1.0.x.vsix` files.
- Do not publish local logs, screenshots, private memory, `.env`, tokens, or
  machine-specific paths.
- Keep the marketplace copy practical: ANA MAX is a local-first MCP cockpit for
  AI coding agents, not a cloud service.
