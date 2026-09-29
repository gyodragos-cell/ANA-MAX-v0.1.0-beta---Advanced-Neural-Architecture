@echo off
setlocal enabledelayedexpansion
title ANA MAX - Pornire FAKE OLLAMA (Duck.ai Proxy)
cd /d "%~dp0"

set "PYTHON=%~dp0..\venv\Scripts\python.exe"

echo.
echo  ============================================
echo   ANA MAX - Pornire DUCK.AI PROXY SERVER
echo  ============================================
echo.

echo [INFO] Inchidem instanta reala de Ollama (daca ruleaza) pentru a elibera portul 11434...
taskkill /F /IM ollama.exe >nul 2>&1
ping -n 2 127.0.0.1 >nul

echo [INFO] Pornesc Fake Ollama (Duck Proxy) pe portul 11434...
start "FAKE OLLAMA [DUCK.AI]" /MAX "%PYTHON%" duck_proxy_server.py 11434
echo [INFO] Asteptam pornirea proxy-ului...
ping -n 3 127.0.0.1 >nul

echo [INFO] Pornesc ANA MAX Server (care se va lega la proxy-ul nostru fara sa stie ca nu e Ollama)...
set "ANA_BACKEND=ollama"
set "ANA_OLLAMA_PORT=11434"
start "ANA MAX Server [OLLAMA :8766]" /MAX /D "%~dp0.." "%PYTHON%" main.py --port 8766
ping -n 3 127.0.0.1 >nul

echo [INFO] Pornesc ANA Live Log in terminal vizibil...
start "Live Log ANA" /MAX powershell -NoExit -Command "Get-Content -Tail 20 -Wait '%~dp0..\logs\ana_max.log'"

echo.
echo  ============================================
echo   SISTEMUL A PORNIT CU SUCCES!
echo   Chat:   http://127.0.0.1:8766/chat
echo   Dash:   http://127.0.0.1:8766/dashboard
echo   Proxy:  Fake Ollama ruleaza pe portul 11434
echo  ============================================
echo.

echo [INFO] Deschid browser-ul cu chat-ul...
start "" "http://127.0.0.1:8766/chat"
start "" "http://127.0.0.1:8766/dashboard"

echo Poti inchide aceasta fereastra. Scripturile ruleaza in terminalele lor verzi.
pause >nul
