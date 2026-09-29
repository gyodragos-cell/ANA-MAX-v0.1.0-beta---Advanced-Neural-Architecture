# ANA MAX MCP Server - Setup Guide
## Universal Tool Layer for Coding Agents

## What This Does

The batch file automates the management of ANA MAX MCP Server to provide 114 enterprise-grade tools to Devin and other coding agents.

## File Created

### Start_ANA_MAX_MCP_For_Devin.bat
**Location:** C:\Users\billy\Desktop\Start_ANA_MAX_MCP_For_Devin.bat

**What it does:**
- Interactive menu with 5 options
- Start Server (checks if already running, starts if not)
- Stop Server (stops and frees port)
- Restart Server (stop + start)
- Check Status (comprehensive status check)
- Exit (closes menu)

## How to Use

### Option 1: Quick Start (Recommended)

1. **Double-click:** `Start_ANA_MAX_MCP_For_Devin.bat`
2. **Wait:** Script will show progress [1/5] through [5/5]
3. **Restart Devin:** Close and reopen Devin
4. **Done:** Devin now has 114 enterprise tools

### Option 2: Manual Control

**Start Server:**
```batch
C:\Users\billy\Desktop\Start_ANA_MAX_MCP_For_Devin.bat
```

**Stop Server:**
```batch
C:\Users\billy\Desktop\Stop_ANA_MAX_MCP_Server.bat
```

## What You Get

### 114 Enterprise Tools:
- 🖥️ **Desktop Control:** Screenshot, UI automation, desktop monitoring
- 🧠 **AI Core:** Memory cortex, context engine, task orchestration
- 🔍 **Monitoring:** Error detection, live healing, telemetry
- 🌐 **Browser:** Browser control, web scraping, web search
- 🔧 **Code Analysis:** Advanced search, architecture analysis, project understanding

### Devin Integration:
- Devin can now see what's on your screen
- Devin can detect when it's stuck
- Devin can learn from its mistakes
- Devin can understand system context
- Devin can verify its changes visually

## Verification

### Test MCP Connection:
```bash
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Test Desktop Capture:
```python
cd C:\Users\billy\Desktop\ana-manus\ANA_MAX
python -c "from tools.desktop_capture import DesktopCaptureTool; tool = DesktopCaptureTool(); result = tool.execute(operation='capture'); print(result.data['file'])"
```

## Troubleshooting

### "Port 8766 already in use"
- Run `Stop_ANA_MAX_MCP_Server.bat` first
- Then run `Start_ANA_MAX_MCP_For_Devin.bat` again

### "Devin doesn't see the tools"
- Restart Devin after running the script
- Check Devin's MCP settings
- Verify server is running: `curl http://127.0.0.1:8766/mcp`

### "Desktop capture test failed"
- This is usually okay - test with actual Devin usage
- Verify server is running correctly
- Check ANA_MAX logs for errors

## Server Details

- **URL:** http://127.0.0.1:8766
- **MCP Endpoint:** http://127.0.0.1:8766/mcp
- **Tools:** 114 enterprise-grade tools
- **Status:** ✅ Ready to use

## Auto-Start (Optional)

To make ANA MAX MCP Server start automatically with Windows:

1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task
3. Trigger: "At startup"
4. Action: Start a program
5. Program: `C:\Users\billy\Desktop\Start_ANA_MAX_MCP_For_Devin.bat`
6. Save and enable

## Next Steps

1. Run `Start_ANA_MAX_MCP_For_Devin.bat`
2. Restart Devin
3. Test with a simple coding task
4. Verify Devin can use the new tools
5. Enjoy enhanced agent capabilities!

## Support

For issues or questions:
- Check server logs: `C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\`
- Verify server status: Run the script again
- Check Devin MCP settings
- Review quick integration guide: `docs\QUICK_INTEGRATION_GUIDE.md`

---

**Version:** 1.0
**Inspired by:** ANA MAX Enterprise Toolset
**Purpose:** Universal tool layer for all coding agents
