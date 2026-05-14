# ANA MAX - Installation Guide

## Prerequisites

### 1. Python 3.9+ (REQUIRED)
Download from: https://www.python.org/downloads/

**IMPORTANT:** Check "Add Python to PATH" during installation!

### 2. Microsoft Visual C++ Build Tools (REQUIRED for Frida)
Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

Install "Desktop development with C++" workload.

### 3. Android Debug Bridge - ADB (OPTIONAL - for Android tools)
Download from: https://developer.android.com/studio/releases/platform-tools

Add to PATH or place in system32.

---

## Installation Steps

### Step 1: Install Python Dependencies

Open PowerShell in ANA_MAX folder:

`powershell
pip install -r requirements.txt
`

**If you get errors with Frida:**
`powershell
# Install Visual C++ Build Tools first
# Then retry:
pip install frida
`

### Step 2: Install Frida Server (for Android tools - OPTIONAL)

If you want to use Android instrumentation:

1. Connect your Android device
2. Download frida-server: https://github.com/frida/frida/releases
3. Push to device:
`ash
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server"
adb shell "/data/local/tmp/frida-server &"
`

### Step 3: Configure Environment

`powershell
# Copy example config
copy .env.example .env

# Edit .env with your API keys
notepad .env
`

### Step 4: Start ANA MAX

`powershell
python main.py
`

You should see:
`
42 tool-uri incarcate.
MCP Server: http://127.0.0.1:8765
`

### Step 5: Connect MCP Client

In your MCP-compatible client (VS Code with Cline/RooCode):
- Server URL: http://127.0.0.1:8765
- Protocol: HTTP MCP

---

## Troubleshooting

### Error: "frida not found"
- Install Visual C++ Build Tools
- Re-run: pip install frida

### Error: "pywinauto import failed"
- Run: pip install pywinauto

### Error: "ADB not found"
- Download ADB from Android SDK
- Add to system PATH

### Calculator automation not working
- Make sure Calculator app is open
- Try: python -c "import pywinauto; print('OK')"

---

## System Requirements

- **OS:** Windows 10/11 (64-bit)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 500MB free space
- **Python:** 3.9 or higher

---

## What's Included in Trial

### ✅ Free Features (42 tools):
- Code editing & search
- Web scraping & browser control
- UI Automation (Calculator, Notepad, etc.)
- System monitoring
- Git operations
- Network diagnostics
- Security auditing
- Terminal execution
- File operations

### ❌ Premium Features (5 tools - requires license):
- Desktop Capture (AI screenshots)
- Live Desktop Viewer (real-time streaming)
- Desktop Control (full desktop automation)
- Windows Insight (advanced system monitoring)
- Windows Deep Sight (God View system analysis)

To unlock premium features, contact: YOUR_EMAIL@example.com

---

## Need Help?

- GitHub Issues: https://github.com/YOUR_USERNAME/ana-max/issues
- Documentation: docs/ folder
- Video Demo: teste tooluri.mp4
