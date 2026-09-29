@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

echo.
echo ============================================
echo  ANA MAX Auto Load
echo  Mode: %MODE%
echo ============================================
echo.

if /I "%MODE%"=="os20" goto :os20
if /I "%MODE%"=="tools" goto :tools
if /I "%MODE%"=="all" goto :all

echo [INFO] Unknown mode "%MODE%". Use os20, tools, or all.
exit /b 1

:all
echo [INFO] Running OS-20 baseline lock with runtime checks...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OS20_BASELINE_LOCK.ps1" -RunRuntimeChecks
if errorlevel 1 exit /b 1

echo [INFO] Running agent startup check...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0agent_startup_check.ps1"
if errorlevel 1 exit /b 1

echo [INFO] Starting ANA MAX...
call "%~dp0..\START_ANA.bat"
exit /b %errorlevel%

:os20
echo [INFO] Running OS-20 baseline lock with runtime checks...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OS20_BASELINE_LOCK.ps1" -RunRuntimeChecks
exit /b %errorlevel%

:tools
echo [INFO] Running agent startup check...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0agent_startup_check.ps1"
if errorlevel 1 exit /b 1

echo [INFO] Running ANA quick check...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ana_quick_check.ps1" -Iterations 1
exit /b %errorlevel%
