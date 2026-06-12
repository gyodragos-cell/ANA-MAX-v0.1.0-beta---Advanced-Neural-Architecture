@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set "MODE=%~1"
if "%MODE%"=="" set "MODE=fast"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "LOG_DIR=ANA_MAX\logs"
set "LOG_FILE=%LOG_DIR%\evolution_%STAMP%.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo ============================================
echo  ANA MAX Evolution Maintenance
echo  Mode: %MODE%
echo  Log: %LOG_FILE%
echo ============================================
echo.

if /I "%MODE%"=="--check" goto :check
if /I "%MODE%"=="check" goto :check
if /I "%MODE%"=="fast" goto :fast
if /I "%MODE%"=="cycle" goto :cycle
if /I "%MODE%"=="os5" goto :os5
if /I "%MODE%"=="audit" goto :audit

echo [ERROR] Unknown mode "%MODE%".
echo Usage:
echo   run_evolution_maintenance.bat check
echo   run_evolution_maintenance.bat fast
echo   run_evolution_maintenance.bat cycle
echo   run_evolution_maintenance.bat os5
echo   run_evolution_maintenance.bat audit
exit /b 2

:check
echo [CHECK] Project root: %CD%
echo [CHECK] Python:
python --version
echo [CHECK] Evolution engine:
python -m ANA_MAX.self_optimization.self_evolution_engine --help >nul
if errorlevel 1 goto :fail
echo [CHECK] OK. No maintenance actions were executed.
exit /b 0

:preflight
echo [INFO] Running agent startup check...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\agent_startup_check.ps1" 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail

echo [INFO] Running ANA quick check...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\ana_quick_check.ps1" -Iterations 1 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
exit /b 0

:fast
call :preflight
if errorlevel 1 goto :fail
echo [INFO] Running fast-parallel self evolution...
python -m ANA_MAX.self_optimization.self_evolution_engine --fast-parallel --max-workers 3 --timeout 180 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
goto :postaudit

:cycle
call :preflight
if errorlevel 1 goto :fail
echo [INFO] Running sequential self evolution cycle...
python -m ANA_MAX.self_optimization.self_evolution_engine --cycle 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
goto :postaudit

:os5
call :preflight
if errorlevel 1 goto :fail
echo [INFO] Running fast-parallel self evolution with OS-5 layer...
python -m ANA_MAX.self_optimization.self_evolution_engine --fast-parallel --os5 --max-workers 3 --timeout 180 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
goto :postaudit

:audit
echo [INFO] Running OS-22 launch audit only...
python scripts\os22\os22_launch_audit.py --write-report --run-tests 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
goto :success

:postaudit
echo [INFO] Running OS-22 launch audit...
python scripts\os22\os22_launch_audit.py --write-report --run-tests 1>>"%LOG_FILE%" 2>>&1
if errorlevel 1 goto :fail
goto :success

:success
echo.
echo [OK] Evolution maintenance completed.
echo [OK] Log: %CD%\%LOG_FILE%
echo [OK] Report: %CD%\ANA_MAX\memory\os22_launch_audit_report.json
exit /b 0

:fail
echo.
echo [FAILED] Evolution maintenance failed.
echo [FAILED] Check log: %CD%\%LOG_FILE%
exit /b 1
