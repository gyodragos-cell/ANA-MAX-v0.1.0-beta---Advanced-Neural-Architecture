# ANA MAX MCP - Advanced Neural Architecture

**Windows-first MCP runtime with 64 loaded tools for local agent IDE workflows**

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

- 64 loaded MCP tools in the public release
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
