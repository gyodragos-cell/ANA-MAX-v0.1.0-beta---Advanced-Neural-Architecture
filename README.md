# ANA MAX – Windows‑only Autonomous Agent

<div align="center">

# 🤖 ANA MAX – Advanced Neural Architecture

### Windows AI Agent with 42 MCP Tools

**See it in action!** 🎬 [Watch Demo Video](demo_ana_max.mp4) (186 MB)

> 📥 **How to watch:** Click the video file above → Click "Download" → Play locally
> 
> The demo shows ANA MAX controlling Windows Calculator, automating UI tasks, and using MCP tools in real-time.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010/11-lightgrey.svg)](#quickstart-windows)

</div>

---

##  What is ANA MAX?

ANA MAX is a **self‑contained, offline AI‑agent** that runs on Windows and can **control the OS natively**.  It uses:
- **pywinauto / UIAutomation** for pixel‑perfect UI interaction (no OCR).  
- **MCP (Model Context Protocol)** – a lightweight HTTP‑JSON‑RPC bridge that any AI (OpenCode, Cursor, Claude, Ollama, etc.) can call.
- **SQLite‑based memory** for persistent learning across sessions.
- **A set of well‑documented tools** (`windows_uia_bridge`, `desktop_capture`, `security_tool`, …) exposed as `ana_<tool>` via the MCP server.

It is designed to be **fully offline** – no internet calls are required once the required model files are downloaded locally (e.g. Mistral‑120B via Ollama).  The agent is ideal for:
- Automated UI testing.
- Personal productivity assistants that can click, type and read windows.
- Secure, on‑premise AI workflows where data never leaves the machine.

##  Works With Popular AI Tools

ANA MAX integrates seamlessly with:
- **Qoder** - AI-powered IDE with MCP support
- **Cursor** - The AI-first code editor
- **Windsurf** - Agentic IDE for developers
- **Antigravity** - AI coding assistant
- **OpenCode** - Built-in MCP bridge
- **Ollama** - Local LLMs for offline use
- **Any MCP-compatible client**

## 💡 Similar Projects

If you're interested in AI automation, also check out:
- **[AdalFlow](https://github.com/SylphAI-Inc/AdalFlow)** - LLM application framework
- **[Qoder AI](https://qoder.com)** - AI-powered development environment
- **[Cursor](https://cursor.sh)** - AI-first code editor
- **[Windsurf](https://windsurf.com)** - Agentic IDE

## Why Windows only?
All low‑level interactions (UIA, window handles, DPI‑aware screenshots) rely on the Windows API, which gives us deterministic, fast, and secure control of the desktop.  The current code base has been thoroughly tested on Windows 10/11.

---

## Quick‑Start (Windows)

1. **Prerequisites**
   - Python 3.11 (or newer) installed and added to PATH.
   - `git` installed.
   - (Optional) **Ollama** with a local LLM (e.g. `mistral:latest`).  The agent works without an LLM, but most AI‑driven tools need a model.

2. **Clone the repository**
   ```powershell
   git clone https://github.com/<your‑username>/ANA_MAX.git
   cd ANA_MAX
   ```

3. **Create a virtual environment and install dependencies**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # PowerShell
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Copy the template:
     ```powershell
     copy .env.example .env
     ```
   - Edit `.env` and fill in ONLY the keys you need (OpenCode, OpenRouter, etc.).  **Never commit this file** – it is ignored by `.gitignore`.

5. **Start the MCP server**
   ```powershell
   python mcp_server.py   # runs on http://127.0.0.1:8765
   ```
   You’ll see a log line:
   > `ANA MCP Bridge initialized with 11 core OS‑level tools`.

6. **Call a tool** (example – open Notepad):
   ```powershell
   curl -X POST http://127.0.0.1:8765/mcp \
        -H "Content-Type: application/json" \
        -d '{"method":"call_tool","params":{"tool":"windows_uia_bridge","args":{"action":"click","target":"Notepad"}}}'
   ```
   The tool will launch Notepad and focus the window.

7. **Use with an AI frontend**
   - **OpenCode** (already bundled in `./.opencode/plugins/ana-mcp-bridge.js`).  Open OpenCode, set the MCP URL to `http://127.0.0.1:8765`, and you can type commands like `"Open Notepad"`.
   - **Cursor / VS Code Extension** – later you can create a small VS Code extension that forwards editor commands to the MCP server.

---

## Available Tools (Windows‑only)
| Tool | Description |
|------|-------------|
| `windows_uia_bridge` | Structured UI Automation – find windows by title, click, type, read text. |
| `desktop_capture` | Fast screenshot of the whole desktop (returns image path). |
| `security_tool` | Simple local file/secret scanner (no network). |
| `network_tool` | Ping, port‑scan, DNS‑lookup. |
| `task_tool` | Schedule a Python task inside the agent. |
| `terminal_tool` | Run a command in a persistent PowerShell session. |
| `qa_tool` | Generate test cases or edge‑cases for a given function. |
| `windows_deep_sight` | Advanced memory inspection (experimental, not included in the clean release). |

> **Tip:** Run `python -m tools.tool_healthcheck` to list all tools that are currently loaded.

## Premium Tools (License Required)

- `desktop_capture` – high‑resolution screenshot of the entire desktop. Requires a Pro license.
- `live_desktop_viewer` – real‑time streaming of the desktop for remote monitoring.
- `desktop_control_tool` – full desktop automation (mouse, keyboard, window management) under a licensed edition.
- `windows_insight_tool` – advanced system insight and diagnostics, premium feature.
- `windows_deep_sight` – “God‑view” system monitoring and event streaming (experimental).

These tools are **disabled in the trial/clean release** and are not loaded by default (see `main.py` where they are commented out). A short demo video (`teste tooluri.mp4`) showcases what the premium suite can do.

---

## Contributing
We keep the repo **lean**.  Before opening a pull request:
1. Make sure your code passes the built‑in `smoke_test_runner.py` suite.
2. Add any new external dependency to `requirements.txt`.
3. Update this README with the new tool’s description.

---

## 💝 Support This Project

ANA MAX is a **free, open-source project** built with passion by a solo developer! If this tool helps you, consider supporting its development:

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/GitHub_Sponsors-Support-blue?style=for-the-badge&logo=github)](https://github.com/sponsors/gyodragos-cell)
[![PayPal](https://img.shields.io/badge/PayPal-Send_to_oana__alicia347__yahoo.com-blue?style=for-the-badge&logo=paypal)](https://paypal.me/oana_alicia347)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-Support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/oana_alicia347)

</div>

**Why your support matters:**
- 🖥️ **Help me upgrade my PC** – Better hardware = faster development = more features
- 🔧 **Fund new tools** – Your donations enable new capabilities and integrations
- 🌍 **Keep ANA MAX free** – Support ensures this stays open-source for everyone
- ❤️ **Fuel independent development** – Your contribution keeps the project alive

**PayPal:** Send donations to `oana_alicia347@yahoo.com`

*Every donation, no matter how small, makes a huge difference!* 

---

## License & Disclaimer
ANA MAX is released under the **MIT License**.  It is provided **as‑is** – the author is not liable for any damage caused by automated UI actions.  Use it responsibly and only on machines you own or have permission to control.

---

## Contact
- **Email:** gyodragos@gmail.com
- **GitHub:** https://github.com/gyodragos-cell
- **Security Issues:** See [SECURITY.md](SECURITY.md)

---

*Happy Coding!*
