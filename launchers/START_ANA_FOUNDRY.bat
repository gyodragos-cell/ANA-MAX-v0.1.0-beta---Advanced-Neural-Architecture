@echo off
title ANA MAX [FOUNDRY LOCAL MODE]
set "ANA_DIR=%~dp0ANA_MAX"
set "PYTHON_EXE=%~dp0ANA_MAX\venv\Scripts\python.exe"
set "FOUNDRY_MODEL=qwen3.5-4b"

echo [SYSTEM] Pornire ANA OS-27 via Foundry Local...
echo [MODEL] Model activ: %FOUNDRY_MODEL%

:: Pornire Live Log in background
start "ANA LIVE LOG" powershell.exe -ExecutionPolicy Bypass -File "%~dp0scripts\live_log.ps1"

:: Pornire Server cu backend-ul Foundry fortat. ANA_AUTO_CONFIRM=1 este
:: limitat la acest launcher local, astfel incat actiunile cerute explicit de
:: utilizator (creare fisiere/directoare, deschidere browser) nu se blocheaza
:: pe un dialog de confirmare invizibil.
start "ANA MAX [FOUNDRY]" /MAX /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=foundry && set ANA_AUTO_CONFIRM=1 && set FOUNDRY_MODEL=%FOUNDRY_MODEL% && "%PYTHON_EXE%" main.py --port 8766"

timeout /t 5
start "" "http://127.0.0.1:8766/chat"
exit
