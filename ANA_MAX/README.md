#  ANA MAX - Ultimate Offline-Ready OS Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Ready](https://img.shields.io/badge/Protocol-MCP-green.svg)](https://github.com/microsoft/language-server-protocol)

**ANA MAX** (Advanced Neural Architecture) is a native, offline-capable Windows OS Agent designed to provide AI models with "eyes and hands" on your computer. 

Unlike most coding assistants that are trapped inside the terminal or editor, ANA MAX uses a secure **Model Context Protocol (MCP)** server to expose deep operating system capabilities to any compatible AI (like Cursor, VS Code, Claude Desktop, or Ollama Mistral).

##  Why ANA MAX?
AI models are brilliant at writing code, but they fail when they need to *test* a Windows desktop app, *click* on a UI element, or *hook* into a running process. ANA MAX solves this by offering an arsenal of 45+ highly specialized tools over MCP.

##  Key Features

* ** Native UI Automation (UIA Bridge)**: Directly inspects Windows UI structural trees (via `pywinauto`) to click, type, and interact with elements precisely without relying on slow or inaccurate OCR.
* ** Deep OS Control**: Complete desktop interaction-screenshot capturing, simulated keystrokes, and mouse control.
* ** SQLite-based Long Term Memory**: Automatically learns from past coding errors and stores solutions to prevent repeating mistakes.
* ** Security & Pentesting Ready**: Built-in network diagnostics, hardware scanners, and Windows Deep Sight (powered by Frida) for advanced hooks and process monitoring.
* ** Universal MCP Compatibility**: Connects to any AI environment using standard JSON-RPC HTTP requests on port `8765`.
* ** Offline First**: Designed to run entirely locally with `psutil` and `pywinauto`. Ready to be paired with local LLMs (like Llama 3 or Mistral 120B via Ollama).

##  Architecture

ANA MAX separates the "Brain" from the "Hands".
1. **The Brain (Your AI)**: Runs in your IDE (Cursor, OpenCode) or via Ollama.
2. **The Hands (ANA MAX)**: Runs in the background as an MCP Server (`main.py`) providing tools to the Brain.

See `docs/PROJECT_MAP_AI_GUIDE.md` for the complete architectural map.

## Resource System

ANA MAX includes a lightweight resource system for dashboard-facing UI
resources:

- `resources/texts/` stores localization JSON files for English and Romanian.
- `resources/themes/` stores light and dark theme JSON files.
- `core/resource_loader.py` loads texts, themes, and optional icons with safe
  fallback behavior.

Missing or invalid text files fall back to English, missing or invalid themes
fall back to the light theme, and missing icons return an empty string.

##  Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ana-max.git
   cd ana-max
   ```

2. **Set up the Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and add your API keys (only required if using cloud fallback models).
   ```bash
   cp .env.example .env
   ```

4. **Start the MCP Server:**
   ```bash
   python main.py
   ```
   *The server will start on `127.0.0.1:8765`.*

##  Connecting to your IDE (VS Code / OpenCode)

ANA MAX is out-of-the-box compatible with MCP plugins. Simply point your AI assistant's MCP configuration to `http://127.0.0.1:8765/mcp`. For OpenCode, a bridge plugin is included in `.opencode/plugins/ana-mcp-bridge.js`.

##  Security Warning
ANA MAX operates in "God Mode" and has full control over your Windows environment. **DO NOT** expose port `8765` to the public internet without proper authentication (Bearer tokens).

---
**Built with  and  for the AI revolution.**

## v21 Foundations

v21 foundations add resource-only hooks for theme switching, future dashboard
layout blocks, dev-mode messaging, Resource Inspector, Dashboard v2, and Tool
Health Visualizer placeholders. These hooks do not expose private lab data and
do not add new tool logic.
