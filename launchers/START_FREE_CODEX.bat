@echo off
setlocal enableDelayedExpansion

title FREE LOCAL CODEX (Powered by ANA Proxy)

set "ROOT_DIR=C:\Users\billy\Desktop\ana-manus"
set "PYTHON_EXE=%ROOT_DIR%\venv\Scripts\python.exe"

echo ============================================================
echo   FREE LOCAL CODEX LAUNCHER
echo ============================================================
echo.

:: 1. Verificam Ollama
echo [1] Verificare serviciu Ollama (Creierul local)...
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:11434/api/tags -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if %errorlevel% NEQ 0 (
    echo [ERROR] Ollama nu este pornit!
    echo [INFO] Pornesc Ollama in fundal...
    start "Ollama Engine" /MIN cmd /k "C:\Users\billy\AppData\Local\Programs\Ollama\ollama.exe serve"
    timeout /t 5 >nul
) else (
    echo [OK] Ollama este online.
)

:: 2. Pornim Proxy-ul de traducere (invizibil, in fundal)
echo [2] Pornire ANA Translator Proxy (Port 8081)...
start "ANA Codex Proxy" /MIN "%PYTHON_EXE%" "%ROOT_DIR%\codeq\codex_translator_proxy.py"

:: Asiguram pip install colorama
"%PYTHON_EXE%" -m pip install colorama >nul 2>&1

:: 3. Lansam Terminalul Interactiv
echo [3] Lansare interfata de chat...
timeout /t 2 >nul
cls

"%PYTHON_EXE%" "%ROOT_DIR%\codeq\codex_terminal.py"

:: La inchiderea terminalului, curatam proxy-ul din fundal
echo.
echo [!] Inchidere proxy in fundal...
taskkill /FI "WINDOWTITLE eq ANA Codex Proxy*" /F /T >nul 2>&1
echo [OK] O zi buna!
pause
exit /b 0
