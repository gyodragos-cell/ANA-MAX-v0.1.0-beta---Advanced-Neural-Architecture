# START_ANA_OLLAMA.bat Startup Flow Analysis
**Generated:** 2026-08-18 02:30 UTC  
**Purpose:** Trace complete startup sequence and connections to OS27 Hyper++ work

---

## Startup Sequence Overview

```
START_ANA_OLLAMA.bat
├─ 1. Auto-Maintenance (ana_auto_maintenance.py)
├─ 2. GPU/CUDA Check
├─ 3. Environment Verification (.env, venv)
├─ 4. Ollama Lock Manager (ollama_lock_manager.py)
├─ 5. Ollama Service Start (:11434)
├─ 6. ANA MAX Server Start (main.py --port 8766)
├─ 7. Live Log Monitor (live_log_monitor.ps1)
└─ 8. Browser Open (dashboard, chat)
```

---

## Component Details

### 1. Auto-Maintenance (ana_auto_maintenance.py)
**Location:** `scripts/ana_auto_maintenance.py`  
**Purpose:** Clean and organize workspace before startup

**Actions:**
- Clean diacritics from .py/.md/.json files
- Move stray test/analyze scripts to sandbox
- Clean .bak/.old/.tmp files
- Verify enterprise structure (AGENTS.md, docs/ROADMAP.md, docs/ANA_MEMORY.md, etc.)
- Log to `logs/auto_maintenance.log`

**Connection to OS27 Hyper++:** 
- Ensures clean workspace for OS27 Hyper++ diagnostic tools
- Verifies structure integrity before system checks

---

### 2. GPU/CUDA Check
**Purpose:** Detect GTX 1650 GPU and CUDA support

**Connection to OS27 Hyper++:**
- GPU detection influences Ollama model selection
- CUDA support affects qwen2.5-coder:7b performance

---

### 3. Environment Verification
**Scripts:** `scripts/bootstrap_ana_env.ps1`  
**Purpose:** Verify .env and venv exist, bootstrap if missing

**Connection to OS27 Hyper++:**
- Ensures Python environment is ready for OS27 Hyper++ tools
- Validates config files for system integrity checks

---

### 4. Ollama Lock Manager
**Location:** `ANA_MAX/ollama_lock_manager.py`  
**Purpose:** Prevent multiple Ollama instances, protect GPU

**Connection to OS27 Hyper++:**
- Prevents resource conflicts during OS27 Hyper++ diagnostics
- Ensures stable backend for AI operations

---

### 5. Ollama Service Start
**Command:** `ollama.exe serve`  
**Port:** 11434  
**Model:** qwen2.5-coder:7b (primary)

**Connection to OS27 Hyper++:**
- Primary AI backend for OS27 Hyper++ operations
- Provides inference for tool routing and decision making

---

### 6. ANA MAX Server Start (main.py)
**Location:** `ANA_MAX/main.py`  
**Port:** 8766  
**Backend:** ollama (set via ANA_BACKEND env var)

**Startup Flow:**

#### 6.1 Configuration Loading
- Load `config/settings.yaml`
- Load `.env` file
- Configure logging (ana_max.log, 15MB max, 5 backups)

#### 6.2 Runtime Agent Building
- Build ANAAgent with backend (ollama)
- Attach memory cortex (core.memory.get_memory())
- Configure session ID and workspace root

#### 6.3 Tool Registration (_register_all_tools)
**Total Tools Registered:** 104 tools

**Tool Categories:**

**A. Core Tools (28 tools)**
- ana_context_tool, files, code, web, system
- tool_healthcheck, conversation_learning_tool
- session_log_miner_tool, session_checkpoint_tool
- session_rem_sleep_tool, session_audit_tool
- session_lifecycle_tool, memory_tool, privacy
- network_tool, security_tool, qa_tool
- smart_search_tool, debugger_tool
- codebase_understanding_tool, browser_control
- terminal_tool, file_patch_tool
- project_navigator_tool, error_radar_tool
- tool_router_tool, code_context_pack_tool
- graph_context_pack_tool, input_api_probe_tool
- binary_map_tool, todo_tool, edit_tool
- system_optimization_tool

**Connection to OS27 Hyper++:**
- All modernized with OS27 Hyper++ telemetry, health, memory, context
- P0/P1 tools fully modernized (15/15)
- SystemIntegrityCheckTool integrated in orchestrator (not in main.py registry)

**B. Optional Tools (11 tools)**
- autonomous_tool, task_tool, science_tool
- web_ai_bridge, engineer_platform_tool
- advanced_swarm_tool, advanced_scanner
- mitm_analyzer_tool, network_pentest_tool
- hardware_scanner_tool
- verdent_tools (5 classes: BashExecTool, GlobSearchTool, GrepContentTool, GrepFileTool, WebFetchTool)

**C. Mobile Tools (5 tools)**
- adb_tool, frida_automation, apk_analyzer
- code_search, web_scraper

**D. Desktop Control Tools (13 tools)**
- desktop_capture, live_desktop_viewer, desktop_control_tool
- windows_insight_tool, windows_uia_bridge
- window_manager, ocr_tool, uia_click_tool, uia_type_tool
- foreground_ui_snapshot, workspace_situational_awareness
- vision_region_capture_tool, vision_find_element_tool

**Connection to OS27 Hyper++:**
- All modernized with OS27 Hyper++ telemetry
- Critical for vision/UI awareness (P0 tools)

**E. Healing Tools (2 tools)**
- live_tool_healer, agent_coach_tool

**Connection to OS27 Hyper++:**
- agent_coach_tool modernized with OS27 Hyper++ telemetry
- Critical for loop detection and guidance (P0 tool)

**F. Voice Tools (1 tool)**
- edge_tts_voice

**G. Advanced Tools (2 tools)**
- vector_memory_tool, swarm_tool

**H. UI-TARS Tools (3 tools)**
- vision_fallback_tool, remote_control_tool, event_stream_tool

**I. AI Core Adapters (10 tools)**
**Location:** `tools/tool_adapters.py`  
**Classes:** ANA_ADAPTER_CLASSES

1. **ContextEngineAdapter** - context_engine
   - Observes active windows, clipboard, processes
   - Classifies activity, predicts intentions
   - **Connection to OS27 Hyper++:** AI Core component, telemetry tracking

2. **ProactiveInterruptAdapter** - proactive_interrupt
   - 5 active detectors: STUCK, SEQUENCE, CLIPBOARD INTENT, REPEAT, CONTEXT SHIFT
   - **Connection to OS27 Hyper++:** AI Core component, telemetry tracking

3. **SelfEvolvingToolAdapter** - self_evolving_tool
   - Auto-fix, auto-improve, auto-install
   - **Connection to OS27 Hyper++:** AI Core component, telemetry tracking

4. **MemoryCortexAdapter** - memory_cortex
   - 4 types of memory (episodic, knowledge, task, vector)
   - **Connection to OS27 Hyper++:** AI Core component, telemetry tracking

5. **OrchestratorAdapter** - orchestrator
   - Task planning, tool routing, execution
   - **Connection to OS27 Hyper++:** AI Core component, SystemIntegrityCheckTool integration

6. **ContextBridgeAdapter** - context_bridge
   - Bridges context between components
   - **Connection to OS27 Hyper++:** AI Core component

7. **WindowManagerAdapter** - window_manager
   - Window management and control
   - **Connection to OS27 Hyper++:** AI Core component

8. **ClipboardManagerAdapter** - clipboard_manager
   - Clipboard operations
   - **Connection to OS27 Hyper++:** AI Core component

9. **WatchdogAdapter** - watchdog
   - Workspace monitoring, file changes
   - **Connection to OS27 Hyper++:** AI Core component

10. **NativeTelemetryAdapter** - native_telemetry
    - System telemetry collection
    - **Connection to OS27 Hyper++:** AI Core component

**J. V19 Diagnostics Tools (3 tools)**
- ana_runtime_inspector, tool_contract_validator, schema_diff

**K. V20 Foundation Tools (6 tools)**
- ana_health_check, baseline_update_suggester
- docs_generator, ana_patch_suggester
- runtime_guard, autonomy_dashboard

**L. Graph Routing Tools (3 tools)**
- GraphToolRouterTool, GraphMetricsTool, GraphStatsTool
- **Connection to OS27 Hyper++:** Tool graph initialization

**M. Unlimited-OCR Tools (3 tools)**
- UnlimitedOCRTool, UnlimitedOCRHealthTool, UnlimitedOCRStartTool
- **Connection to OS27 Hyper++:** P1 tool modernized

**N. System Inspector Tools (2 tools)**
- SystemInspectorTool, SystemRepairTool
- **Connection to OS27 Hyper++:** System diagnostics

**O. Project Reader Tools (3 tools)**
- ProjectReaderTool, ProjectAnalyzerTool, ProjectSearchTool

#### 6.4 Tool Graph Initialization
- Initialize default graph-based tool routing
- Configure common workflows
- **Connection to OS27 Hyper++:** Tool graph analysis in diagnostic report

#### 6.5 MCP Server Start
- Start Flask app on port 8766
- Expose all registered tools via MCP protocol
- Enable CORS for local HTML demos
- Serve dashboard and chat interfaces

**Connection to OS27 Hyper++:**
- MCP server exposes OS27 Hyper++ modernized tools
- SystemIntegrityCheckTool available via MCP (through orchestrator)

---

### 7. Live Log Monitor
**Location:** `scripts/live_log_monitor.ps1`  
**Purpose:** Real-time log monitoring with OS27 debug highlighting

**Features:**
- Monitors `logs/ana_max.log`
- Highlights OS27-DEBUG, OS27-ALERT (red)
- Highlights OLLAMA-LOG, qwen, ollama (cyan)
- Highlights ERROR, EROARE, FAIL (red)
- Highlights WARNING, WARN (yellow)
- Highlights SUCCESS, OK, INFO (green)
- Highlights ACTION, DECISION, THOUGHT (magenta)

**Connection to OS27 Hyper++:**
- Provides real-time visibility into OS27 Hyper++ operations
- Highlights OS27-specific debug messages

---

### 8. Browser Open
**URLs:**
- http://127.0.0.1:8766/dashboard
- http://127.0.0.1:8766/chat

**Connection to OS27 Hyper++:**
- Dashboard displays OS27 Hyper++ telemetry and health
- Chat interface for interacting with OS27 Hyper++ tools

---

## OS27 Hyper++ Integration Points

### Direct Integration
1. **SystemIntegrityCheckTool** - Integrated in `tools/ana_orchestrator.py`
   - Startup trigger in constructor
   - Critical task trigger in _plan()
   - Manual trigger in _detect_file_analysis_need()
   - **Note:** Not registered in main.py (uses orchestrator registry)

2. **Tool Brain Modules** - Created in `tools/`
   - tool_priority_map.py - Tool priority classification
   - tool_health_dashboard.py - Health scoring and dashboard
   - tool_auto_discovery.py - Auto-discovery of tools
   - tool_smoke_test.py - Smoke test runner
   - tool_auto_fix.py - Auto-fix engine

3. **AI Core Adapters** - Registered in main.py via tool_adapters.py
   - ContextEngineAdapter, ProactiveInterruptAdapter
   - SelfEvolvingToolAdapter, MemoryCortexAdapter
   - OrchestratorAdapter, ContextBridgeAdapter
   - WindowManagerAdapter, ClipboardManagerAdapter
   - WatchdogAdapter, NativeTelemetryAdapter

### Indirect Integration
1. **P0/P1 Tools Modernized** - All 15 critical tools have OS27 Hyper++ features
   - Telemetry tracking (operation_count, success_count, failure_count, etc.)
   - Health monitoring (healthy/degraded/broken/unknown)
   - MemoryCortex integration
   - ContextEngine integration
   - SelfEvolvingTool integration

2. **Tool Graph** - Initialized in main.py
   - Nodes: 104 tools
   - Edges: Common workflows
   - **Connection to OS27 Hyper++:** Tool graph analysis in diagnostic report

3. **Logging** - OS27-specific highlighting in live_log_monitor.ps1
   - OS27-DEBUG, OS27-ALERT messages highlighted
   - Real-time visibility into OS27 operations

---

## Missing Connections

### SystemIntegrityCheckTool
- **Status:** Integrated in orchestrator, NOT in main.py registry
- **Impact:** Not exposed via MCP server directly
- **Workaround:** Available through orchestrator tool

### AI Core Import Failures
- **ContextEngine:** Import error in context_engine.py
- **SelfEvolvingTool:** Module import error
- **ProactiveInterrupt:** Module import error
- **Impact:** AI Core adapters may fail to load
- **Status:** Identified in OS27 Hyper++ LIVE SYSTEM REPORT

### Tool Registry Gap
- **46 tools** discovered but not in _CLASS_TO_MODULE
- **Impact:** Not loaded by main.py
- **Status:** Identified in OS27 Hyper++ LIVE SYSTEM REPORT

---

## Recommendations

### Immediate Actions
1. **Fix AI Core Import Failures**
   - Debug ContextEngine import error
   - Fix SelfEvolvingTool module import
   - Fix ProactiveInterrupt module import

2. **Register Missing Tools**
   - Add 46 missing tools to _CLASS_TO_MODULE
   - Update main.py to load them

3. **SystemIntegrityCheckTool MCP Exposure**
   - Consider adding to main.py registry for direct MCP access
   - Or document orchestrator-based access pattern

### Long-term Actions
1. **Startup Integration**
   - Add OS27 Hyper++ smoke test to startup sequence
   - Add health dashboard generation to startup
   - Add system integrity check to startup

2. **Monitoring Integration**
   - Integrate OS27 Hyper++ telemetry into live_log_monitor.ps1
   - Add OS27-specific dashboard widgets
   - Add OS27 health indicators to main dashboard

---

## Summary

**Startup Flow:** 8 sequential steps  
**Total Tools Loaded:** 104 tools  
**OS27 Hyper++ Integration:** Direct (3), Indirect (15 tools + tool graph + logging)  
**Critical Gaps:** AI Core import failures, 46 unregistered tools, SystemIntegrityCheckTool MCP exposure

**Connection to OS27 Hyper++ Work:**
- ✅ Tool Brain modules created and functional
- ✅ P0/P1 tools modernized with OS27 Hyper++ features
- ✅ SystemIntegrityCheckTool integrated in orchestrator
- ✅ AI Core adapters registered (may fail due to import issues)
- ⚠️ AI Core import failures need fixing
- ⚠️ 46 tools not registered in main.py
- ⚠️ SystemIntegrityCheckTool not exposed via MCP directly

**Next Steps:**
1. Fix AI Core import failures
2. Register 46 missing tools
3. Consider SystemIntegrityCheckTool MCP exposure
4. Add OS27 Hyper++ checks to startup sequence
