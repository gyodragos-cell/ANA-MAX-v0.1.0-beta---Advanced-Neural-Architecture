# Quick Integration Guide - ANA MAX MCP Server
## Universal Tool Layer - Ready to Use Right Now

## Current Status: READY TO USE ✅

**ANA MAX MCP Server:** Running on http://127.0.0.1:8766
**Tools Available:** 114 enterprise-grade tools
**Status:** Fully functional and tested

## Immediate Integration Options

### Option 1: Test MCP Connection (Verify It Works)

**Test with curl:**
```bash
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**Expected Result:** JSON with tool list

### Option 2: Devin Integration (Universal MCP)

**Config File Location:** `C:\Users\billy\Desktop\ana-manus\.agents\mcp_config.json`

**Current Config:**
```json
{
  "mcpServers": {
    "anamax": {
      "type": "http",
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

**This is ALREADY CONFIGURED for Devin!**

### Option 3: Windsurf/Cursor Integration

**For Windsurf:**
```json
{
  "mcpServers": {
    "anamax": {
      "type": "http",
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

**For Cursor:**
- Settings → MCP → Add Server
- Name: `anamax`
- Type: HTTP
- URL: `http://127.0.0.1:8766/mcp`

### Option 4: Claude Code Integration

**Config File:** `C:\Users\billy\.claude\settings.json`

**Add to existing config:**
```json
{
  "mcpServers": {
    "anamax": {
      "type": "http",
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

## Testing the Integration

### Test Desktop Capture (Verify Vision Works)

**Test command:**
```python
from tools.desktop_capture import DesktopCaptureTool
tool = DesktopCaptureTool()
result = tool.execute(operation='capture')
print(f"Screenshot saved to: {result.data['file']}")
```

**Expected:** Screenshot saved to ANA_MAX/screenshots/

### Test Context Engine (Verify Intelligence Works)

**Test command:**
```python
from tools.context_engine import ContextEngine
engine = ContextEngine()
context = engine.get_context_snapshot()
print(f"Active windows: {len(context.get('windows', []))}")
```

**Expected:** Current system state snapshot

### Test Error Radar (Verify Self-Detection Works)

**Test command:**
```python
from tools.error_radar import ErrorRadar
radar = ErrorRadar()
errors = radar.scan_recent_logs(hours=1)
print(f"Found {len(errors)} potential issues")
```

**Expected:** Error analysis report

## Available Tool Categories

### 🖥️ Desktop Control (14 tools)
- `desktop_capture` - Screenshot with telemetry
- `live_desktop_viewer` - Live streaming
- `windows_uia_bridge` - UI automation
- `uia_click` / `uia_type` - Desktop interaction
- `ocr_tool` - Screen text extraction
- etc.

### 🧠 AI Core (12 tools)
- `context_engine` - Advanced context
- `memory_cortex` - Persistent memory
- `ana_orchestrator` - Task planning
- `continual_learning` - Learning system
- etc.

### 🔍 Monitoring (10 tools)
- `error_radar` - Error detection
- `live_tool_healer` - Real-time diagnosis
- `agent_coach` - Telemetry feedback
- etc.

### 🌐 Browser & Web (5 tools)
- `browser_control` - Browser automation
- `web_search` - Web search
- `web_fetch` - Page fetching
- `web_scraper` - Web scraping
- etc.

### 🔧 Code Analysis (15+ tools)
- `code_search` - Advanced code search
- `codebase_understanding` - Architecture analysis
- `project_analyzer` - Pattern detection
- etc.

## Next Steps

### For Testing:
1. Test MCP connection with curl
2. Test specific tools (desktop_capture, context_engine)
3. Verify tool responses and performance

### For Integration:
1. Add MCP config to target platform
2. Restart the platform
3. Verify tools appear in tool list
4. Test a simple workflow

### For Deployment:
1. Set up ANA MAX as Windows service
2. Configure auto-start on boot
3. Document for end-users
4. Create installation scripts

## Troubleshooting

### Server Not Running:
```bash
cd C:\Users\billy\Desktop\ana-manus\ANA_MAX
python main.py --port 8766
```

### Port Already in Use:
```bash
python main.py --port 8767
```

### Connection Refused:
- Check firewall settings
- Verify server is running
- Test with curl first

## Quick Reference

**Server URL:** http://127.0.0.1:8766
**MCP Endpoint:** http://127.0.0.1:8766/mcp
**Tools Count:** 114
**Status:** ✅ Ready to Use

**Bottom Line:** The universal tool layer is ALREADY RUNNING. Just integrate it with your platform! 🚀
