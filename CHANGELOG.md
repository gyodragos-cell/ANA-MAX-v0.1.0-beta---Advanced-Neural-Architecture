# ANA MAX - Change Log

## v0.2.0-beta (2026-05-15) - Free Vision Features (Screenshot + OCR)

### 🎯 Major Release - Vision AI Now FREE!

#### Free Vision Features
- ✅ **desktop_capture** moved from Premium to FREE
- ✅ **OCR enabled** - PaddleOCR now included in requirements.txt
- ✅ **Vision AI** - AI can now see and read text from screens

#### Tool Count Changes
- **43 Free Tools** (was 42) - desktop_capture now free
- **4 Premium Tools** (was 5) - only streaming/control remain premium
- **9 AI Core Modules** - unchanged

#### Files Modified
- `main.py` - desktop_capture uncommented and enabled
- `requirements.txt` - PaddleOCR dependencies uncommented
- `index.html` - statistics updated (43 Free, 4 Premium)
- `vscode_extension/package.json` - version 0.2.0, description updated
- `vscode_extension/README.md` - features and tool counts updated

### 📦 Extension Updates
- Version bumped to 0.2.0
- Description updated to highlight Vision AI
- README updated with new free features
- New .vsix package: `advanced-neural-architecture-0.2.0.vsix`

---

## v0.1.1-beta (2026-05-15) - License System & Professional Packaging

### 🎯 New Features

#### Professional Packaging
- ✅ **`pyproject.toml`** created for modern Python packaging
  - Standard `pip install -e .` support
  - Proper dependency management with optional extras (ocr, voice, dev)
  - Entry points: `ana-max` and `ana-max-server` commands
  - Integrated tooling: pytest, black, ruff, mypy configuration

#### License Management System
- ✅ **`core/license_manager.py`** - Complete licensing system
  - Encrypted license storage using Fernet (AES-128)
  - HMAC-SHA256 signature verification
  - Machine ID binding for security
  - Automatic expiration checking
  - Premium tool access control

#### License Activation Tools
- ✅ **`activate_license.py`** - Simple license activation script
  ```bash
  python activate_license.py --key YOUR_LICENSE_KEY
  ```

- ✅ **`generate_license.py`** - License generation for distributors
  ```bash
  python generate_license.py --email user@example.com --days 30
  ```

#### Security Validation
- ✅ Premium tool protection integrated in `main.py`:
  - `/execute` endpoint checks license before tool execution
  - `/mcp` tools/call method validates premium access
  - New `license.status` MCP method for checking license info
  - `/health` and `/tools` endpoints show license status

#### Test Suite
- ✅ **`tests/`** directory with comprehensive tests:
  - `test_license_manager.py` - 12 tests for licensing system
  - `test_tool_registry.py` - Tests for tool registry and basic tools

#### Documentation
- ✅ **`docs/LICENSING.md`** - Complete licensing guide
  - How to activate a Pro license
  - License types and features
  - Troubleshooting guide
  - API reference for developers

### 🔧 Code Modifications

#### main.py Updates
- Added `check_premium_access()` validation before tool execution
- Enhanced `_list_tools()` to show license status and premium indicators
- Updated `/health` endpoint to include license information
- Updated `/tools` endpoint to show premium/available status
- Added `license.status` MCP method
- Integrated license_manager module

### 📦 New Files Added
```
ANA_MAX_GitHub_Release/
├── pyproject.toml           # Professional Python packaging
├── activate_license.py      # License activation script
├── generate_license.py      # License generation script
├── core/
│   └── license_manager.py   # License management system
├── tests/
│   ├── __init__.py
│   ├── test_license_manager.py
│   └── test_tool_registry.py
└── docs/
    └── LICENSING.md         # Licensing documentation
```

---

## v0.1.0-beta (2026-05-14) - Initial GitHub Release

### 🎯 Release Preparation

#### Folder Cleanup
- ✅ Created `ANA_MAX_GitHub_Release/` from source `ana_dev/`
- ✅ Removed development artifacts:
  - `archives/` (sandbox, research, keys)
  - `backups/`
  - `logs/` (runtime logs)
  - `memory/` (database files: ana_brain.db, ana_engineer_brain.db, etc.)
  - `browser_snapshots/`
  - `screenshots/`
  - `generated_bots/`
  - `data/events.db`
  - `.opencode/`
  - `.launcher_state.json`
  - `__pycache__/` (all instances)
  - `node_modules/` (from plugins/)
  - `docs/nemotron/` (internal documentation)
  - `docs/PLAN_VIITOR_OCHI_ANA_MAX.md`
  - `docs/PROJECT_MAP_AI_GUIDE.md`
  - `docs/AI_RULES.md`
  - `docs/apikey.txt`

#### Essential Files Created
- ✅ `.env.example` - API key template
- ✅ `INSTALL_GUIDE.md` - Complete installation guide with:
  - Python 3.9+ requirements
  - Visual C++ Build Tools (for Frida)
  - ADB setup (optional)
  - Step-by-step installation
  - Troubleshooting section
  - System requirements
- ✅ `install.bat` - Automated 5-step Windows installer:
  1. Python version check
  2. Visual C++ Build Tools verification
  3. Pip dependencies installation
  4. ADB check (optional)
  5. .env file creation
- ✅ `LICENSE` - MIT License
- ✅ `requirements.txt` - All Python dependencies including:
  - flask, requests, pydantic (core)
  - pywinauto, psutil (desktop automation)
  - selenium, beautifulsoup4 (web)
  - frida, cryptography (security)
  - watchdog, chardet (code intelligence)
  - pyyaml, colorama, Pillow (utilities)

### 🔧 Code Modifications

#### Trial Version - Premium Tool Gating
Modified `main.py` to disable premium tools in trial version:

**Disabled Premium Tools (4):**
- `live_desktop_viewer` - Real-time desktop streaming
- `desktop_control` - Full desktop automation
- `windows_insight` - Advanced system monitoring
- `windows_deep_sight` - "God View" system analysis

**Active Free Tools (43):**
- All code tools (edit, search, understanding)
- Web tools (browser, scraper, search)
- System tools (terminal, control, optimization)
- Security tools (audit, pentest, network)
- UI Automation (`windows_uia_bridge` - Calculator demo)
- Vision AI (`desktop_capture` - screenshot capture)
- Git operations
- File operations
- And more...

**Code Changes in main.py:**
```python
# Line 185-192: Desktop tools - Trial version
desktop_tools = [
    ("tools.desktop_capture", "DesktopCaptureTool"),          # FREE - Vision AI enabled
    # ("tools.live_desktop_viewer", "LiveDesktopViewerTool"), # PREMIUM
    # ("tools.desktop_control_tool", "DesktopControlTool"),   # PREMIUM
    # ("tools.windows_insight_tool", "WindowsInsightTool"),   # PREMIUM
    ("tools.windows_uia_bridge", "WindowsUiaBridgeTool"),     # FREE
]

# Line 230-238: Windows Deep Sight - Premium
# tool_class = _load_tool_class("tools.windows_deep_sight", "WindowsDeepSightTool")  # PREMIUM
print(f"  [!] windows_deep_sight - PREMIUM FEATURE (disabled in trial)")
```

#### Bug Fix: windows_uia_bridge.py
Fixed click_element to use `invoke()` instead of `click_input()` for UWP apps (Calculator):
- **Problem:** `click_input()` closed UWP apps
- **Solution:** Use `invoke()` for UWP, fallback to `click_input()` for Win32
- **File:** `tools/windows_uia_bridge.py` lines 204-214

### 🎬 Demo Content
- ✅ `teste tooluri.mp4` (177.7 MB) - Calculator automation demo
  - AI controls Calculator via MCP tools
  - Performs calculations without writing code
  - Shows structural UI reading (50 elements detected)
  - Calculations: 5×5=25, 100÷4=25, 999×9=8991, 7×8=56

### 🧪 Testing Results

**All Tests Passed:**
1. ✅ Server startup - 42 tools loaded
2. ✅ MCP server responds - 42 tools available
3. ✅ UI Automation works - 50 Calculator elements
4. ✅ Calculator automation - 7×8=56 successful
5. ✅ Premium tools disabled - 0 premium tools active

**Server Output:**
```
42 tool-uri incarcate.
MCP Server: http://127.0.0.1:8765
ANA MAX running on http://127.0.0.1:8765
```

### 📦 Final Release Structure

```
ANA_MAX_GitHub_Release/
├── .env.example
├── .gitignore
├── install.bat
├── INSTALL_GUIDE.md
├── launcher.py
├── LICENSE
├── main.py
├── README.md
├── requirements.txt
├── teste tooluri.mp4
│
├── config/
│   ├── authorized_targets.json
│   ├── settings.yaml
│   └── plugins/__init__.py
│
├── core/
│   ├── agent.py
│   ├── mcp_server.py
│   ├── config.py
│   ├── backends/ (10 backend adapters)
│   ├── testing/
│   └── ... (40+ core files)
│
├── tools/
│   ├── base.py
│   ├── windows_uia_bridge.py
│   ├── code.py
│   ├── web.py
│   ├── files.py
│   └── ... (47 total tools)
│
├── plugins/
│   ├── __init__.py
│   ├── backup_plugin.py
│   ├── browser_plugin.py
│   ├── git_plugin.py
│   └── examples/
│
└── docs/
    ├── README.md
    └── requirements.txt
```

### 🚀 Launch Preparation

**Desktop Shortcut Created:**
- Name: `Qoder - ANA MAX MCP`
- Location: Desktop
- Target: `python main.py` in `ANA_MAX_GitHub_Release/`
- Purpose: Quick start MCP server before chatting with Qoder

**MCP Server Protocol:**
- URL: `http://127.0.0.1:8765`
- Method: POST
- Content-Type: `application/json`
- Example: `{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}`

### 📋 Installation Instructions

1. **Install Python 3.9+** from https://python.org
2. **Install Visual C++ Build Tools** (for Frida)
3. **Run `install.bat`** or `pip install -r requirements.txt`
4. **Copy `.env.example` to `.env`** and add API keys
5. **Start server:** `python main.py`
6. **Connect MCP client** to `http://127.0.0.1:8765`

### 💡 Trial vs Pro Strategy

**Trial (Free):**
- 43 functional tools
- Code editing & search
- Web automation
- UI Automation (Calculator, Notepad)
- System monitoring
- Git operations
- Security auditing

**Pro (License Required):**
- Desktop Capture (AI screenshots)
- Live Desktop Viewer (real-time streaming)
- Desktop Control (full automation)
- Windows Insight (advanced monitoring)
- Windows Deep Sight (God View)

To unlock: Uncomment lines in `main.py` and restart server.

---

## Development Notes

**Source Repository:** `C:\Users\billy\Desktop\ana_dev\ANA_MAX\`
**Release Folder:** `C:\Users\billy\Desktop\ANA_MAX_GitHub_Release\`
**Release Date:** May 14, 2026
**Status:** Beta Release - Ready for GitHub Upload

**Key Achievement:**
First AI agent that can SEE and CONTROL Windows applications natively through MCP protocol with 47 tools, structural UI reading (like HTML DOM for Windows apps), and offline-capable architecture.

---

*Last Updated: 2026-05-14 11:30 AM*
