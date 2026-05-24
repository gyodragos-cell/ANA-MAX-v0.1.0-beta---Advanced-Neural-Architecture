# ANA MAX MCP - Advanced Neural Architecture

**Windows-first MCP runtime with 80 loaded tools for local agent IDE workflows**

Use ANA MAX from VS Code as a local tool layer for AI coding agents: desktop
awareness, code and git tools, terminal context, OCR, authorized runtime
instrumentation, and verification.

## Quick Start

1. Install Python 3.9+ from https://python.org
2. Download the ANA MAX repository ZIP from GitHub, or clone it with Git.
3. Open the ANA MAX folder in VS Code.
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `ANA MAX: Start MCP Server`
6. Use tools: `ANA MAX: Call Tool`

## MCP Auth Settings

The public release requires MCP authentication. The extension uses these VS Code
settings:

```json
{
  "anaMax.mcpApiKey": "change-me",
  "anaMax.mcpHost": "127.0.0.1",
  "anaMax.mcpPort": 8765
}
```

When you start the server from VS Code, `anaMax.mcpApiKey` is passed as
`MCP_API_KEY`. Tool calls from the extension send:

```text
Authorization: Bearer change-me
```

VS Code 1.121+ sets `VSCODE_AGENT` for terminal commands launched by an agent.
ANA MAX detects it automatically and keeps startup output compact for agent
sessions. Manual runs keep the normal output.

## Install From VSIX

If the extension is not installed yet, install the included VSIX from the repo
root:

```powershell
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

Or use VS Code:

```text
Extensions -> ... -> Install from VSIX
```

Select:

```text
vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

For users who do not know Git yet, use the ZIP download path documented in
`docs/USER_EXTENSION_INSTALL_AND_ETHICS.md`.

## Features

<!-- # PATCH_START v20_final -->
- 80 loaded MCP tools in the public release
<!-- # PATCH_END v20_final -->
- Local-first observe -> decide -> act -> verify workflow
- Vision AI: screenshot capture and OCR
- Windows UI inspection and desktop context
- Code, git, terminal, and workspace tools
- Authorized Frida/runtime diagnostics when static inspection is not enough
- Optional Pro license for deep desktop control tools

## Requirements

- Python 3.9 or higher
- Windows 10/11
- Visual C++ Build Tools for Frida
- PaddleOCR when OCR workflows are used

## Free vs Pro

Free:

- `desktop_capture`
- OCR and foreground UI inspection
- code editing and search
- web and browser tools
- system, git, terminal, and network diagnostics
- security auditing

Premium-gated:

- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

## Agent IDE Workflow

Recommended flow:

```text
tools/list -> observe workspace -> choose smallest useful tool -> act -> verify
```

ANA MAX is not meant to be a blind automation pile. Use the observation tools
before write or control tools, and run verification before handoff.

## Ethical Use

ANA MAX is for white-hat, authorized red-team, QA, education, debugging, and
repair work. Use it only on systems you own or are allowed to test. It is not a
black-hat hacking kit.

## Links

- GitHub: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
- Documentation: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture#readme
- Issues: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/issues

## Contact

- Primary Email: gyodragos@gmail.com
- Alternative Email: oana_alicia347@yahoo.com
- GitHub: https://github.com/gyodragos-cell

## Support This Project

ANA MAX is a free, open-source project built with passion. If this tool helps
you, consider supporting its development:

- GitHub Sponsors: https://github.com/sponsors/gyodragos-cell
- PayPal: https://paypal.me/oana_alicia347
- Buy Me a Coffee: https://www.buymeacoffee.com/gyodragosw

Every contribution helps fund development hardware, feature work, tool
stabilization, and independent open-source development.

## License

MIT

