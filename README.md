# ANA MAX OS-27 — AI Operating System & Universal MCP Tool Layer

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![MCP Ready](https://img.shields.io/badge/Protocol-MCP%20stdio%20%2B%20HTTP-green.svg)](https://modelcontextprotocol.io/)
[![Tools: 121+](https://img.shields.io/badge/Tools-121%2B-orange.svg)](#tools)
[![Frida: 17.11.0](https://img.shields.io/badge/Frida-17.11.0-red.svg)](https://frida.re/)
[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)](#)

**ANA is not an AI. ANA is an OS for AI.**

*The physical interface between an AI mind and the real local world.*

</div>

---

## What is ANA MAX OS-27?

ANA MAX OS-27 is a **native Windows AI Operating System** — not a chatbot, not a wrapper. It is the execution layer that sits between any AI model (Claude, GPT-4, Qwen, Llama) and the real machine.

When your AI needs to *see the screen*, *click a button*, *intercept network traffic*, *inject into a process*, or *remember something semantically* — it calls ANA. ANA executes. The AI stays in the realm of reasoning.

```
┌─────────────────────────────────────────────────┐
│              AI MODEL (The Mind)                │
│    Claude / Qwen / GPT-4 — Reasoning, Planning  │
└──────────────────┬──────────────────────────────┘
                   │ MCP stdio / HTTP (port 8765)
┌──────────────────▼──────────────────────────────┐
│              ANA OS-27 (The Body)               │
│  EYES:    OmniSense → VLM → screen understanding│
│  HANDS:   Terminal, Desktop Control, Browser    │
│  MEMORY:  ChromaDB MemoryCortex (semantic, <50ms)│
│  INTEL:   DLL injection, memory patching, MITM  │
│  SWARM:   Task routing → local/remote nodes     │
└──────────────────┬──────────────────────────────┘
                   │
       Windows 11 x64 + GTX 1650 (local machine)
```

---

## Key Capabilities

### 👁️ Eyes — Real Screen Vision
- **Desktop Capture** — screenshot pipeline with perceptual hash delta detection
- **OmniSense Vision Daemon** — background polling (5–10s), OCR runs only on screen change
- **OCR Tool** — PaddleOCR local + Tesseract fallback for iframes, canvas, modals
- **VLM Engine** — full image understanding for complex UI analysis
- **Windows Recall** — episodic screen memory indexed in ChromaDB (RAG-ready)

### 🖐️ Hands — Real Execution
- **Windows UIA Bridge** — Microsoft UI Automation tree inspection, element click/type
- **Desktop Control** — mouse, keyboard, process launch
- **Browser Control** — Playwright-based (CDP A11y tree), no fragile XPath/CSS selectors
- **Terminal Monitor** — PowerShell/bash process monitoring, error detection, command capture
- **File Operations** — validated read/write/patch with integrity checks

### 🧠 Memory — Durable Context
- **Memory Cortex** — ChromaDB semantic vector store, `<50ms` recall, episodic + long-term
- **Context Engine** — automatic activity classification (browsing, coding, debugging)
- **Workspace Situational Awareness** — active app, UIA quality, error signals, next-step hint
- **Session Checkpoints** — REM-sleep style consolidation of session knowledge

### 🔬 Enterprise System Intelligence
- **DLL Injection Tool** — Frida v17.11.0, inject/eject/hook/unhook DLL exports at runtime
- **Memory Patching Tool** — read/write process memory, NOP instructions, JMP hooks, pattern scan
- **Process Security Tool** — hollowing detection, doppelgänging scan, anti-debug detection, baseline anomaly monitoring (241 process baseline)
- **Network Protocol Tool** — packet capture, protocol decoding, MITM detection, traffic tampering analysis (397 connections monitored, 7 interfaces)
- **Windows Deep Sight** — psutil God View: process tree, network map, top CPU/RAM, security scan

### 🌐 Web & Automation
- **Ultrafast Web Executor v4** — CDP accessibility tree navigation, OCR fallback, self-healing (invalid element state bypass), exponential backoff `[0.5, 1.0, 2.0, 4.0, 8.0]s`
- **Web Scraper** — multi-URL batch, CSS selector extraction
- **Web Search** — DuckDuckGo anonymous, regional support
- **Browser Pack** — session management, tab control, network intercept, DOM snapshot

### ⚡ Orchestration & Recovery
- **Universal Task Orchestrator** — platform-agnostic, natural language task planning, retry + verify, works with any MCP registry
- **Auto Recovery** — 5 built-in strategies (network, timeout, file, permission, import), automatic or manual, full recovery history
- **Error Radar** — real-time error detection from logs, severity classification, fix recommendation
- **Live Tool Healer** — auto-fix broken tools without server restart
- **Swarm Router** — distribute heavy tasks to local/remote nodes over WiFi

---

## Architecture: MCP Bridge Mode (Antigravity IDE)

ANA OS-27 runs as an **MCP stdio server** that Antigravity IDE loads automatically when the `ana-manus` workspace is open. No Ollama required — minimal CPU/VRAM footprint.

```
Antigravity MCP Bridge (stdio)
  └─ mcp/os27_mcp_server.py
       ├─ 28 OS27 system tools (telemetry, watchdog, cortex, omnisense, self-heal)
       └─ HTTP bridge → http://127.0.0.1:8765/execute  (121+ tools)
```

**Starting:**
```
Double-click: "Antigravity MCP Bridge.lnk" on Desktop
→ "[OK] ANA MAX HTTP Server online (port 8765)"
→ Antigravity IDE has: EYES + HANDS + MEMORY + WEB + SWARM (no Ollama)
```

---

## Architecture: Full Mode (Devin / Windsurf / Cursor / Claude Desktop)

```
Double-click: "Start_ANA_MAX_MCP_For_Devin.bat" on Desktop
Menu: 1=Start | 2=Stop | 3=Restart | 4=Check Status
MCP endpoint: http://127.0.0.1:8766/mcp
```

**Supported AI Platforms:**

| Platform | Status | Config |
|----------|--------|--------|
| Antigravity IDE | ✅ Ready | MCP stdio, auto-loaded |
| Devin | ✅ Configured | Universal MCP config |
| Windsurf | ✅ Configured | Same as Devin |
| Cursor | ✅ Manual setup | `http://127.0.0.1:8766/mcp` |
| Claude Desktop | ✅ Compatible | Standard MCP HTTP |

---

## Tool Count & Performance

| Category | Tools | Status |
|----------|-------|--------|
| Desktop & Vision | 12 | ✅ Production |
| Browser & Web | 9 | ✅ Production |
| Memory & Context | 8 | ✅ Production |
| Enterprise System Intelligence | 15 | ✅ Production |
| Terminal & Files | 10 | ✅ Production |
| Network & Security | 8 | ✅ Production |
| Orchestration & Recovery | 7 | ✅ Production |
| AI Core & Session | 12 | ✅ Production |
| Tool Brain Modules | 5 | ✅ Production |
| Utilities | 35+ | ✅ Production |
| **Total** | **121+** | **95.7% test success rate** |

**Measured performance (post-repair, September 2026):**

| Tool | Before | After |
|------|--------|-------|
| Memory Cortex | timeout >10s | **0.000s** |
| Context Engine | timeout >10s | **<1s** |
| Tool Healthcheck | timeout >10s | **<1s** |
| Clipboard Manager | 4.8s | **2.055s** |
| All major tools | — | **<100ms** |

**Devin workflow validation: 10/10 tests, 100% success rate.**

---

## Why ANA MAX vs Standard AI Tooling

| Capability | Standard AI Coding Agent | ANA MAX OS-27 |
|------------|--------------------------|---------------|
| See the screen | ❌ | ✅ VLM + OCR |
| Click UI elements | ❌ | ✅ UIA Bridge |
| DLL Injection | ❌ | ✅ Frida v17.11.0 |
| Memory Patching at Runtime | ❌ | ✅ |
| Process Hollowing Detection | ❌ | ✅ |
| MITM Traffic Detection | ❌ | ✅ |
| Semantic Long-term Memory | ❌ | ✅ ChromaDB |
| Auto Error Detection from Logs | ❌ | ✅ Error Radar |
| Self-healing Broken Tools | ❌ | ✅ |
| Works with ANY AI model | ❌ Vendor-locked | ✅ MCP universal |
| Compensates 7B model limits | ❌ | ✅ 80% compensation |

---

## Quick Start

### Antigravity MCP Bridge (minimal resources, no Ollama)

```
1. Double-click "Antigravity MCP Bridge.lnk" on Desktop
2. Wait for: [OK] ANA MAX HTTP Server online (port 8765)
3. Open Antigravity IDE → workspace: C:\Users\billy\Desktop\ana-manus
4. MCP loads automatically. Done.
```

### Full Mode (with local AI)

```powershell
# Start ANA MAX server
cd ANA_MAX
.\venv\Scripts\activate
python main.py
# HTTP MCP server: http://127.0.0.1:8765
```

### Manual HTTP API call

```python
import urllib.request, json

data = {
    "tool": "browser_control",
    "args": {
        "operation": "open",
        "url": "https://github.com",
        "visible": True,
        "wait_seconds": 5
    }
}
body = json.dumps(data).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8765/execute",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as r:
    print(r.read().decode())
```

---

## Project Structure

```
ana-manus/
├── README.md                           ← This file
├── ANA_MAX/
│   ├── main.py                         ← HTTP MCP server (port 8765)
│   ├── tools/                          ← 173 tool modules
│   │   ├── browser_control.py          ← Playwright CDP A11y
│   │   ├── desktop_capture.py          ← Screen vision
│   │   ├── memory_cortex.py            ← ChromaDB semantic memory
│   │   ├── dll_injection.py            ← Frida DLL injection
│   │   ├── memory_patching.py          ← Process memory patching
│   │   ├── process_security.py         ← Hollowing/doppelgänging
│   │   ├── network_protocol.py         ← MITM/traffic analysis
│   │   ├── terminal_monitor.py         ← Terminal process monitor
│   │   ├── universal_task_orchestrator.py
│   │   ├── auto_recovery.py
│   │   └── [...173 total]
│   ├── core/
│   │   └── omnisense.py                ← Vision daemon (delta OCR)
│   ├── mcp/
│   │   └── os27_mcp_server.py          ← MCP stdio (28 OS27 tools)
│   ├── CHANGELOG.md
│   └── docs/
│       ├── ANA_MEMORY.md               ← Full session history
│       └── [architecture docs]
├── mcp/
│   └── os27_mcp_server.py
├── docs/
│   ├── ANA_MEMORY.md
│   ├── QUICK_INTEGRATION_GUIDE.md
│   └── ANA_MAX_MCP_SETUP_README.md
└── .agents/
    └── GEMINI.md                       ← Antigravity agent config
```

---

## Security

ANA MAX runs in **God Mode** — full local system access by design.

- **DO NOT** expose ports `8765` / `8766` to the public internet
- All execution is local — no cloud, no telemetry, no external APIs required
- Enterprise tools (DLL injection, memory patching) require elevated permissions for full native access
- Safe mode validation active by default — no execution without explicit tool call
- Designed for: security research, RE, malware analysis, Android pentest via Frida + ADB + Nox Player

---

## Tech Stack

| Component | Version / Detail |
|-----------|-----------------|
| Python | 3.12 |
| Frida | 17.11.0 |
| Playwright | CDP A11y mode |
| ChromaDB | local vector DB |
| PaddleOCR | local |
| Tesseract | `C:/Program Files/Tesseract-OCR/` |
| psutil | process + network monitoring |
| pywinauto | UIA Bridge |
| Ollama (optional) | qwen2.5-coder:7b @ 127.0.0.1:11434 |
| GPU | GTX 1650 (4GB VRAM) |
| OS | Windows 11 x64 |

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 — DLL & Memory | ✅ Complete | Frida-based injection + memory patching |
| Phase 2 — Process Security | ✅ Complete | Hollowing, doppelgänging, anti-debug |
| Phase 3 — Network Intel | ✅ Complete | MITM detection, packet analysis |
| Phase 4 — Kernel Hooks | 🔮 Long-term | Windows driver development |
| Continual Learning | 🔮 Planned | LoRA fine-tuning pipeline (peft + transformers) |
| Swarm Node Secondary | 🔮 Planned | WiFi-distributed VLM processing to other devices |

---

## Session History

All architectural decisions, implementations, repairs and test results:

- [`docs/ANA_MEMORY.md`](docs/ANA_MEMORY.md) — Operational memory (full)
- [`ANA_MAX/docs/ANA_MEMORY.md`](ANA_MAX/docs/ANA_MEMORY.md) — Tool-level session logs (12k+ lines)
- [`ANA_MAX/CHANGELOG.md`](ANA_MAX/CHANGELOG.md) — Version changelog

---

<div align="center">

**Built offline. Runs local. God Mode.**

*ANA MAX OS-27 — Zero blindness. Zero hallucinations about system state. Eyes and hands for AI.*

</div>
