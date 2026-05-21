@echo off
setlocal

cd /d "%~dp0"

echo ============================================================
echo ANA MAX local website preview
echo ============================================================
echo.
echo Keep this window open while previewing the site.
echo.
echo Open:
echo http://127.0.0.1:8090/
echo.
echo Press Ctrl+C in this window to stop the server.
echo.

py -3 -m http.server 8090 --bind 127.0.0.1

echo.
echo Server stopped.
pause
