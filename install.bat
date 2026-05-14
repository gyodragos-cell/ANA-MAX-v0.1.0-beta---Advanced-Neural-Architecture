@echo off
echo ====================================================
echo    ANA MAX - Windows AI Agent Installer
echo ====================================================
echo.

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.9+ from https://python.org
    echo IMPORTANT: Check "Add Python to PATH" during install
    pause
    exit /b 1
)
echo OK: Python installed
echo.

echo [2/5] Checking Visual C++ Build Tools (for Frida)...
if exist "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe" (
    echo OK: Visual Studio found
) else (
    echo WARNING: Visual C++ Build Tools not found
    echo Frida may fail to install without it.
    echo Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo Install "Desktop development with C++" workload
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
)
echo.

echo [3/5] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    echo.
    echo Common issues:
    echo 1. Frida needs Visual C++ Build Tools
    echo 2. Run as Administrator if permission denied
    echo 3. Check Python version (need 3.9+)
    echo.
    pause
    exit /b 1
)
echo OK: Dependencies installed
echo.

echo [4/5] Checking ADB (optional - for Android tools)...
adb version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: ADB not found (optional)
    echo Android tools will be disabled
    echo Download from: https://developer.android.com/studio/releases/platform-tools
) else (
    echo OK: ADB found
)
echo.

echo [5/5] Creating .env file...
if not exist .env (
    copy .env.example .env
    echo OK: .env file created
    echo IMPORTANT: Edit .env with your API keys!
) else (
    echo OK: .env file already exists
)
echo.

echo ====================================================
echo    Installation Complete!
echo ====================================================
echo.
echo To start ANA MAX:
echo   python main.py
echo.
echo Then connect your MCP client to:
echo   http://127.0.0.1:8765
echo.
echo For detailed instructions, see: INSTALL_GUIDE.md
echo.
pause
