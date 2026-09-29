@echo off
REM Start Mitmproxy Live Analyzer pentru ANA Whitehat Testing

echo ========================================
echo ANA MITM Live Analyzer - Whitehat Testing
echo ========================================
echo.

cd /d C:\Users\billy\Desktop\ana-manus\ANA_MAX

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting Mitmproxy in reverse mode for ANA MCP...
echo Port: 8080
echo Upstream: http://127.0.0.1:8765 (ANA MCP)
echo.
echo Press Ctrl+C to stop capture
echo.

REM Pornește mitmproxy în modul reverse pentru a intercepta traficul ANA
venv\Scripts\python.exe -m mitmproxy --mode reverse --upstream http://127.0.0.1:8765 --listen-port 8080 -s tools\mitmproxy_live_analyzer.py --set console_eventlog_verbosity=info

pause
