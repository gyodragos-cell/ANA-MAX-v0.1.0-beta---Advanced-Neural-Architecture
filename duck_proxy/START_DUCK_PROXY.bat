@echo off
:: ANA MAX - DUCK PROXY + AGENT LOOP v7.0
:: Duck.ai = Brain (LLM gratuit) | ANA OS27 = Tools (84 tools locale)

title ANA_DUCK_AGENT_v7
cls

set "PYTHON_EXE=C:\Users\billy\Desktop\ana-manus\ANA_MAX\venv\Scripts\python.exe"
set "PROXY_SCRIPT=C:\Users\billy\Desktop\ana-manus\duck_proxy\duck_proxy_server.py"
set "AGENT_SCRIPT=C:\Users\billy\Desktop\ana-manus\duck_proxy\ana_agent_loop.py"
set "ANA_MAIN=C:\Users\billy\Desktop\ana-manus\ANA_MAX\main.py"
set "ANA_LOG=C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"

echo ======================================================
echo   DUCK.AI BRAIN + ANA OS27 TOOLS = AGENT COMPLET
echo ======================================================
echo.

echo [*] Verificare fisiere...
if not exist "%PYTHON_EXE%" ( echo [!] EROARE: Python lipsa la %PYTHON_EXE% & pause & exit )
if not exist "%PROXY_SCRIPT%" ( echo [!] EROARE: Proxy lipsa la %PROXY_SCRIPT% & pause & exit )
if not exist "%AGENT_SCRIPT%" ( echo [!] EROARE: Agent loop lipsa la %AGENT_SCRIPT% & pause & exit )

echo [*] Inchid procese vechi...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ANA_DUCK*" /T >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ANA_SERVER*" /T >nul 2>&1
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe' AND CommandLine LIKE '%%chrome_profile%%'\" | Invoke-CimMethod -MethodName Terminate" >nul 2>&1

echo.
echo [1/3] Pornesc PROXY Duck.ai (Chrome REAL + Profil Persistent)...
echo       Prima rulare: Chrome se deschide vizibil.
echo       Daca apare challenge, rezolva-l manual.
echo.
start "ANA_DUCK_PROXY_v7" /MIN cmd /k ""%PYTHON_EXE%" "%PROXY_SCRIPT%" 11434"

echo [*] Astept 20 secunde pentru Chrome + Duck.ai...
timeout /t 20 /nobreak >nul

echo [2/3] Verificare proxy health...
powershell -Command "try { $r = Invoke-RestMethod http://127.0.0.1:11434/health -TimeoutSec 5; Write-Host '[OK] Proxy ready:' $r.status } catch { Write-Host '[!] Proxy nu raspunde inca - asteapta si reincearca' }"

echo.
echo ======================================================
echo   Ce vrei sa faci?
echo   1) AGENT LOOP (Duck.ai + Tools - scrie cod pe disc)
echo   2) PROXY ONLY (porneste doar proxy-ul)
echo   3) FULL STACK  (proxy + ANA server + browser UI)
echo ======================================================
echo.
choice /C 123 /M "Alege"

if errorlevel 3 goto FULLSTACK
if errorlevel 2 goto PROXYONLY
if errorlevel 1 goto AGENTLOOP

:AGENTLOOP
echo.
echo [3/3] Pornesc AGENT LOOP (Duck.ai brain + ANA tools)...
echo       Scrie ce vrei sa construiasca si Duck.ai + ANA executa!
echo.
"%PYTHON_EXE%" "%AGENT_SCRIPT%"
pause
goto END

:PROXYONLY
echo.
echo [OK] Proxy activ pe http://127.0.0.1:11434
echo      POST /api/chat  |  GET /health  |  GET /api/tags
echo.
pause
goto END

:FULLSTACK
echo [3/3] Pornesc ANA SERVER + Browser UI...
start "ANA_SERVER" /MIN cmd /k "set ANA_BACKEND=ollama && set ANA_OLLAMA_PORT=11434 && "%PYTHON_EXE%" "%ANA_MAIN%" --port 8766"
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8766/chat"
echo.
echo [SUCCESS] Totul lansat!
echo  - Proxy Duck.ai: http://127.0.0.1:11434
echo  - ANA Server:    http://127.0.0.1:8766
echo.
pause
goto END

:END

