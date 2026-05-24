@echo off
setlocal

cd /d "%~dp0"

echo ============================================================
echo ANA MAX local dev launcher
echo ============================================================
echo.
echo This starts:
echo - ANA MAX MCP server on http://127.0.0.1:8765
echo - ANA MAX Bridge UI on http://127.0.0.1:8790
echo.
echo LOCAL DEV MODE uses no API key on 127.0.0.1.
echo Close the two server windows to stop everything.
echo.

if not exist "main.py" (
  echo ERROR: main.py was not found. Run this from the repo root.
  pause
  exit /b 1
)

if not exist "ana-max-bridge\bridge_server.py" (
  echo ERROR: ana-max-bridge\bridge_server.py was not found.
  pause
  exit /b 1
)

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
  ) else (
    echo ERROR: Python was not found on PATH.
    pause
    exit /b 1
  )
)

echo Starting ANA MAX MCP server...
start "ANA MAX MCP Server" cmd /k "cd /d ""%~dp0"" && %PYTHON_CMD% main.py"

echo Waiting for ANA MAX health endpoint...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { Start-Sleep -Seconds 1 } } while ((Get-Date) -lt $deadline); exit 1"
if not %errorlevel%==0 (
  echo ERROR: ANA MAX did not become ready on http://127.0.0.1:8765/health.
  echo Check the ANA MAX MCP Server window for details.
  pause
  exit /b 1
)

echo Starting ANA MAX Bridge...
start "ANA MAX Bridge" cmd /k "cd /d ""%~dp0ana-max-bridge"" && %PYTHON_CMD% bridge_server.py"

echo Waiting for bridge UI...
timeout /t 3 /nobreak >nul

echo Opening bridge UI...
start "" "http://127.0.0.1:8790/"

echo.
echo Done. Bridge UI: http://127.0.0.1:8790/
echo.
pause
