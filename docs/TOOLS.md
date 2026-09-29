# ANA MAX Tools Reference

## Overview

ANA MAX includes 90+ production-ready tools organized into functional categories. This document provides a comprehensive reference for all available tools.

## Tool Categories

### Agent Core/Orchestration (7 tools)

**agent_coach**
- Description: Provides coaching and guidance for agent behavior
- Parameters: action, context, history
- Risk Level: Low

**ana_orchestrator**
- Description: Orchestrates ANA MAX OS v2 components
- Parameters: capability, payload, trace_id
- Risk Level: Low

**autonomous_engine**
- Description: Autonomous decision-making engine
- Parameters: goal, constraints, context
- Risk Level: Medium

**autonomous_brain**
- Description: Brain component for autonomous agents
- Parameters: input, mode, config
- Risk Level: Medium

**bot_factory**
- Description: Factory for creating bot instances
- Parameters: bot_type, config, parameters
- Risk Level: Low

**multi_agent_system**
- Description: Manages multiple agents working together
- Parameters: agents, task, coordination
- Risk Level: Medium

**swarm**
- Description: Swarm intelligence for distributed tasks
- Parameters: agents, task, strategy
- Risk Level: Medium

### Code/File/Dev (17 tools)

**bash_exec**
- Description: Execute bash commands
- Parameters: command, cwd, timeout
- Risk Level: High (shell execution)

**code_search**
- Description: Search codebase for patterns
- Parameters: pattern, file_types, case_sensitive
- Risk Level: Low

**edit**
- Description: Edit files with precise operations
- Parameters: file_path, operation, content
- Risk Level: Medium (file modification)

**file_operations**
- Description: Perform file system operations
- Parameters: operation, path, content
- Risk Level: Medium (file system access)

**git_operations**
- Description: Execute git commands
- Parameters: operation, repository, parameters
- Risk Level: Medium (git operations)

**multi_file_editor**
- Description: Edit multiple files simultaneously
- Parameters: files, operations, sync
- Risk Level: Medium

**surgical_edit**
- Description: Precise surgical edits to code
- Parameters: file, target, replacement
- Risk Level: Medium

**codebase_understanding**
- Description: Analyze codebase structure
- Parameters: path, depth, analysis_type
- Risk Level: Low

**smart_search**
- Description: Intelligent code search
- Parameters: query, context, filters
- Risk Level: Low

**git_checkpoint**
- Description: Create git checkpoints
- Parameters: message, tags, push
- Risk Level: Low

**session_lifecycle**
- Description: Manage session lifecycle
- Parameters: action, session_id, data
- Risk Level: Low

**repair_controller**
- Description: Control repair operations
- Parameters: target, repair_type, options
- Risk Level: Medium

**resource_loader**
- Description: Load resources dynamically
- Parameters: resource_type, path, options
- Risk Level: Low

**observer**
- Description: Observe system state
- Parameters: target, events, filters
- Risk Level: Low

**predictor**
- Description: Predict system behavior
- Parameters: target, context, model
- Risk Level: Low

**reliability**
- Description: Assess system reliability
- Parameters: target, metrics, threshold
- Risk Level: Low

### Desktop/UI/Vision (18 tools)

**browser_control**
- Description: Control web browser
- Parameters: action, url, selector
- Risk Level: Medium (browser automation)

**desktop_capture**
- Description: Capture desktop screenshots
- Parameters: region, format, quality
- Risk Level: Low

**ocr_tool**
- Description: OCR text extraction
- Parameters: image, language, options
- Risk Level: Low

**uia_click**
- Description: Click UI elements via UI Automation
- Parameters: element, offset, modifiers
- Risk Level: Medium (UI automation)

**uia_type**
- Description: Type text via UI Automation
- Parameters: element, text, options
- Risk Level: Medium (UI automation)

**windows_uia_bridge**
- Description: Bridge to Windows UI Automation
- Parameters: action, element, parameters
- Risk Level: Medium (UI automation)

**foreground_ui_snapshot**
- Description: Snapshot foreground UI
- Parameters: window, region, format
- Risk Level: Low

**frida_automation**
- Description: Frida-based automation
- Parameters: target, script, options
- Risk Level: High (runtime instrumentation)

**windows_deep_sight**
- Description: Deep Windows system inspection
- Parameters: target, depth, filters
- Risk Level: Medium (system inspection)

**windows_insight_tool**
- Description: Windows system insights
- Parameters: target, metric, options
- Risk Level: Low

**live_desktop_viewer**
- Description: Live desktop viewing
- Parameters: region, fps, quality
- Risk Level: Low

**desktop_control_tool**
- Description: Control desktop remotely
- Parameters: action, parameters, options
- Risk Level: High (desktop control)

**edge_tts_voice**
- Description: Text-to-speech using Edge TTS
- Parameters: text, voice, options
- Risk Level: Low

**vision_fallback_tool**
- Description: Fallback for vision operations
- Parameters: image, operation, options
- Risk Level: Low

**vision_find_element**
- Description: Find UI elements via vision
- Parameters: image, pattern, options
- Risk Level: Low

**vision_region_capture**
- Description: Capture specific regions
- Parameters: region, format, options
- Risk Level: Low

**window_manager**
- Description: Manage windows
- Parameters: action, window, options
- Risk Level: Medium (window management)

### Memory/Session (13 tools)

**ana_memory**
- Description: ANA persistent memory
- Parameters: action, key, value
- Risk Level: Low

**memory_tool**
- Description: Generic memory operations
- Parameters: action, key, value
- Risk Level: Low

**memory_cortex**
- Description: Advanced memory cortex
- Parameters: action, data, options
- Risk Level: Low

**conversation_learning**
- Description: Learn from conversations
- Parameters: conversation, context, options
- Risk Level: Low

**vector_memory**
- Description: Vector-based memory
- Parameters: action, vector, metadata
- Risk Level: Low

**session_checkpoint**
- Description: Create session checkpoints
- Parameters: session_id, data, tags
- Risk Level: Low

**session_rem_sleep**
- Description: Remote sleep for sessions
- Parameters: session_id, duration, options
- Risk Level: Low

**session_log_miner_tool**
- Description: Mine session logs
- Parameters: session, filters, analysis
- Risk Level: Low

**session_lifecycle**
- Description: Manage session lifecycle
- Parameters: action, session_id, data
- Risk Level: Low

**conversation_audit_latest**
- Description: Audit latest conversations
- Parameters: filters, limit, options
- Risk Level: Low

**last_creative_response**
- Description: Last creative response
- Parameters: context, options
- Risk Level: Low

**session_manifest**
- Description: Session manifest
- Parameters: session_id, details, options
- Risk Level: Low

### Runtime/Process/Sensors (10 tools)

**frida_instrument**
- Description: Frida instrumentation
- Parameters: target, script, options
- Risk Level: High (runtime instrumentation)

**system_control**
- Description: System control operations
- Parameters: action, target, options
- Risk Level: High (system control)

**watchdog**
- Description: System watchdog
- Parameters: target, action, options
- Risk Level: Medium (system monitoring)

**terminal_tool**
- Description: Terminal operations
- Parameters: command, cwd, options
- Risk Level: High (shell execution)

**debugger_tool**
- Description: Debugger operations
- Parameters: action, target, options
- Risk Level: Medium (debugging)

**hardware_scanner_tool**
- Description: Scan hardware
- Parameters: target, depth, options
- Risk Level: Low

**system_optimization_tool**
- Description: Optimize system
- Parameters: action, target, options
- Risk Level: Medium (system modification)

**live_debug_console**
- Description: Live debug console
- Parameters: action, target, options
- Risk Level: Medium (debugging)

**event_stream_tool**
- Description: Stream events
- Parameters: target, filters, options
- Risk Level: Low

**ana_runtime_inspector**
- Description: Inspect ANA runtime
- Parameters: target, depth, options
- Risk Level: Low

### Security/Mobile/Network (7 tools)

**security_tool**
- Description: Security operations
- Parameters: action, target, options
- Risk Level: Medium (security operations)

**adb_tool**
- Description: Android Debug Bridge
- Parameters: action, device, options
- Risk Level: Medium (device control)

**advanced_scanner**
- Description: Advanced scanning
- Parameters: target, depth, options
- Risk Level: Medium (scanning)

**mitm_analyzer_tool**
- Description: MITM analysis
- Parameters: capture, analysis, options
- Risk Level: High (network interception)

**network_pentest_tool**
- Description: Network penetration testing
- Parameters: target, tests, options
- Risk Level: High (penetration testing)

**network_tool**
- Description: Network operations
- Parameters: action, target, options
- Risk Level: Medium (network operations)

**apk_analyzer**
- Description: APK analysis
- Parameters: apk, analysis, options
- Risk Level: Low (static analysis)

### Web/Voice/Remote (9 tools)

**web**
- Description: Web operations
- Parameters: action, url, options
- Risk Level: Low (web requests)

**web_search**
- Description: Web search
- Parameters: query, engine, options
- Risk Level: Low

**web_scraper**
- Description: Web scraping
- Parameters: url, selectors, options
- Risk Level: Low

**web_ai_bridge**
- Description: Bridge to web AI services
- Parameters: service, query, options
- Risk Level: Low

**edge_tts_voice**
- Description: Edge TTS voice
- Parameters: text, voice, options
- Risk Level: Low

**text_to_speech**
- Description: Text to speech
- Parameters: text, voice, options
- Risk Level: Low

**voice_commentary**
- Description: Voice commentary
- Parameters: text, voice, options
- Risk Level: Low

**remote_control**
- Description: Remote control
- Parameters: action, target, options
- Risk Level: High (remote control)

**swarm_tool**
- Description: Swarm operations
- Parameters: action, swarm, options
- Risk Level: Medium

### Other Tools (22 tools)

**qa_tool**
- Description: QA operations
- Parameters: action, target, options
- Risk Level: Low

**todo_tool**
- Description: Todo list management
- Parameters: action, task, options
- Risk Level: Low

**file_patch_tool**
- Description: Patch files
- Parameters: file, patch, options
- Risk Level: Medium (file modification)

**error_radar_tool**
- Description: Error radar
- Parameters: target, filters, options
- Risk Level: Low

**tool_router_tool**
- Description: Tool routing
- Parameters: capability, context, options
- Risk Level: Low

**project_navigator_tool**
- Description: Navigate projects
- Parameters: project, path, options
- Risk Level: Low

**workspace_situational_awareness**
- Description: Workspace awareness
- Parameters: workspace, depth, options
- Risk Level: Low

**science_tool**
- Description: Scientific operations
- Parameters: operation, data, options
- Risk Level: Low

**autonomous_tool**
- Description: Autonomous operations
- Parameters: action, goal, options
- Risk Level: Medium

**clipboard_manager**
- Description: Clipboard management
- Parameters: action, content, options
- Risk Level: Low

**smoke_test_runner**
- Description: Run smoke tests
- Parameters: tests, environment, options
- Risk Level: Low

**tool_healthcheck**
- Description: Tool health check
- Parameters: tools, depth, options
- Risk Level: Low

**live_tool_healer**
- Description: Heal broken tools
- Parameters: tools, strategy, options
- Risk Level: Medium

**context_engine**
- Description: Context engine
- Parameters: action, context, options
- Risk Level: Low

**advanced_scanner**
- Description: Advanced scanning
- Parameters: target, depth, options
- Risk Level: Medium

**browser_runtime**
- Description: Browser runtime
- Parameters: action, options, config
- Risk Level: Low

**jupyter_sandbox**
- Description: Jupyter sandbox
- Parameters: notebook, options, config
- Risk Level: Medium

**dashboard**
- Description: Dashboard operations
- Parameters: action, data, options
- Risk Level: Low

**lab**
- Description: Lab operations
- Parameters: action, experiment, options
- Risk Level: Low

**license_manager**
- Description: License management
- Parameters: action, license, options
- Risk Level: Low

**mcp_server**
- Description: MCP server operations
- Parameters: action, config, options
- Risk Level: Low

## Tool Safety Levels

**Low Risk:**
- Read-only operations
- Local file operations
- Analysis and inspection
- Memory operations

**Medium Risk:**
- File modifications
- UI automation
- System inspection
- Network operations

**High Risk:**
- Shell execution
- System control
- Runtime instrumentation
- Remote control
- Network interception

## Tool Usage Guidelines

### Safe Tools (Low Risk)

Can be used without special precautions:
- code_search
- file_operations (read-only)
- memory_tool
- web_search
- ocr_tool

### Caution Required (Medium Risk)

Use with caution:
- edit (file modifications)
- git_operations
- browser_control
- uia_click
- uia_type

### Dangerous Tools (High Risk)

Require explicit approval:
- bash_exec (shell execution)
- frida_automation (runtime instrumentation)
- system_control (system control)
- mitm_analyzer_tool (network interception)
- remote_control (remote control)

## Tool Registration

All tools are automatically registered in the MCP server via the tool catalogue in `ANA_MAX/mcp_stdio.py`.

To add a new tool:
1. Create tool class in `ANA_MAX/tools/`
2. Add to tool catalogue in `ANA_MAX/mcp_stdio.py`
3. Add unit tests
4. Add integration tests

## Tool Parameters

Each tool has its own parameter set defined in its `get_definition()` method. Common parameters include:

- **action**: The operation to perform
- **target**: The target of the operation
- **options**: Additional options
- **config**: Configuration object
- **context**: Execution context

## Tool Error Handling

All tools return a `ToolResult` object with:
- `is_success`: Boolean indicating success
- `data`: Result data
- `message`: Human-readable message
- `error`: Error details if failed

## Tool Performance

Most tools are optimized for performance:
- Lazy loading of dependencies
- Efficient data structures
- Caching where appropriate
- Timeout handling

## Tool Security

All tools implement security measures:
- Input validation
- Path sanitization
- Command injection prevention
- Resource limits
- Error message sanitization

## Tool Testing

Each tool should have:
- Unit tests for core functionality
- Integration tests for tool interactions
- Error handling tests
- Security validation tests

## Tool Documentation

Each tool should document:
- Purpose and use cases
- Parameters and their types
- Return values
- Error conditions
- Security considerations
- Performance characteristics
