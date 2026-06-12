@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=lab"

set "PY_MAIN=python"
set "PY_LLM=local_llm_env\Scripts\python.exe"
set "MODEL=local_models\phi3-medium-q5_k_m.gguf"
set "CHAT_SCRIPT=scripts\os22\start_os22_agent.bat"
set "LOG_SCRIPT=scripts\os22\tail_os22_logs.ps1"
set "AUDIT_SCRIPT=scripts\os22\os22_launch_audit.py"

if /I "%MODE%"=="--help" goto :help
if /I "%MODE%"=="help" goto :help
if /I "%MODE%"=="--check" goto :check
if /I "%MODE%"=="check" goto :check
if /I "%MODE%"=="--chat-only" goto :chat_only
if /I "%MODE%"=="chat" goto :chat_only
if /I "%MODE%"=="--logs-only" goto :logs_only
if /I "%MODE%"=="logs" goto :logs_only
if /I "%MODE%"=="--audit" goto :audit
if /I "%MODE%"=="audit" goto :audit
if /I "%MODE%"=="--audit-tests" goto :audit_tests
if /I "%MODE%"=="audit-tests" goto :audit_tests
if /I "%MODE%"=="--legacy-server" goto :legacy_server
if /I "%MODE%"=="legacy-server" goto :legacy_server
if /I "%MODE%"=="lab" goto :lab

echo [ERROR] Unknown mode "%MODE%".
goto :help_fail

:help
echo.
echo ANA MAX OS22 LAB CHAT launcher
echo.
echo Usage:
echo   start_os22_lab_chat.bat lab          Start checks, live logs, and chat
echo   start_os22_lab_chat.bat chat         Start only the chat window
echo   start_os22_lab_chat.bat logs         Start only the live log window
echo   start_os22_lab_chat.bat check        Validate files and launch audit
echo   start_os22_lab_chat.bat audit        Run OS-22 launch audit
echo   start_os22_lab_chat.bat audit-tests  Run OS-22 launch audit with focused tests
echo   start_os22_lab_chat.bat legacy-server Start optional legacy server plus chat
echo.
echo Desktop shortcut default mode: lab
exit /b 0

:help_fail
call :help
exit /b 2

:check
call :precheck
exit /b %errorlevel%

:audit
call :validate_files
if errorlevel 1 exit /b 1
echo [INFO] Running OS-22 launch audit...
%PY_MAIN% "%AUDIT_SCRIPT%" --write-report
exit /b %errorlevel%

:audit_tests
call :validate_files
if errorlevel 1 exit /b 1
echo [INFO] Running OS-22 launch audit with focused tests...
%PY_MAIN% "%AUDIT_SCRIPT%" --write-report --run-tests
exit /b %errorlevel%

:lab
call :precheck
if errorlevel 1 (
  echo [FAIL] OS-22 lab precheck failed.
  pause
  exit /b 1
)

echo [OK] OS-22 lab precheck passed.
echo [INFO] Starting OS/tools readiness window...
start "ANA MAX LAB CHECKS - OS AND TOOLS" cmd /k "cd /d ""%ROOT%"" && call scripts\auto_load_ana.bat os20 && call scripts\auto_load_ana.bat tools && echo. && echo OS/tools checks are ready. Use the separate OS22 chat window for conversation."

timeout /t 2 /nobreak >nul

call :start_logs_window
timeout /t 1 /nobreak >nul
call :start_chat_window

echo.
echo Started:
echo - ANA MAX LAB CHECKS - OS AND TOOLS
echo - ANA MAX OS22 LIVE LOG
echo - ANA MAX OS22 CHAT ONLY
echo.
echo Keep the chat window open. This launcher can be closed.
exit /b 0

:legacy_server
call :precheck
if errorlevel 1 (
  echo [FAIL] OS-22 lab precheck failed.
  pause
  exit /b 1
)
start "ANA MAX LEGACY RUNTIME - OPTIONAL" cmd /k "cd /d ""%ROOT%"" && call scripts\auto_load_ana.bat all"
timeout /t 2 /nobreak >nul
call :start_logs_window
timeout /t 1 /nobreak >nul
call :start_chat_window
exit /b 0

:chat_only
call :precheck
if errorlevel 1 (
  echo [FAIL] OS-22 chat precheck failed.
  pause
  exit /b 1
)
call :start_chat_window
exit /b 0

:logs_only
call :validate_files
if errorlevel 1 exit /b 1
call :start_logs_window
exit /b 0

:start_logs_window
echo [INFO] Starting OS22 live log window...
start "ANA MAX OS22 LIVE LOG" powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%LOG_SCRIPT%" -Root "%ROOT%"
exit /b 0

:start_chat_window
echo [INFO] Starting clean chat window...
start "ANA MAX OS22 CHAT ONLY" cmd /k "cd /d ""%ROOT%"" && call ""%CHAT_SCRIPT%"""
exit /b 0

:precheck
call :validate_files
if errorlevel 1 exit /b 1
echo [INFO] Running OS-22 launch audit...
%PY_MAIN% "%AUDIT_SCRIPT%" --write-report >nul
if errorlevel 1 (
  echo [FAIL] Launch audit failed. Check ANA_MAX\memory\os22_launch_audit_report.json
  exit /b 1
)
echo [OK] Launch audit passed.
exit /b 0

:validate_files
if not exist "%PY_LLM%" (
  echo [FAIL] Missing %PY_LLM%
  exit /b 1
)
if not exist "%MODEL%" (
  echo [FAIL] Missing %MODEL%
  exit /b 1
)
if not exist "%AUDIT_SCRIPT%" (
  echo [FAIL] Missing %AUDIT_SCRIPT%
  exit /b 1
)
if not exist "%CHAT_SCRIPT%" (
  echo [FAIL] Missing %CHAT_SCRIPT%
  exit /b 1
)
if not exist "%LOG_SCRIPT%" (
  echo [FAIL] Missing %LOG_SCRIPT%
  exit /b 1
)
echo [OK] Required OS-22 files present.
exit /b 0
