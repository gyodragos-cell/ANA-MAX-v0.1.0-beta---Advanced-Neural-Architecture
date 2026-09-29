@echo off
setlocal enableDelayedExpansion

:: ============================================================
::  ANTIGRAVITY MCP BRIDGE — ANA OS-27
::  Porneste DOAR bridge-ul MCP pentru Antigravity.
::  Fara Ollama, fara GPU, consum minim de resurse.
::
::  CAND SA FOLOSESTI ASTA:
::    - Vrei sa lucrezi cu Antigravity (IDE) si sa ai acces
::      la toolurile ANA (screen, files, terminal, memory etc.)
::    - NU ai nevoie de Qwen / Ollama local
::    - Vrei sa economisesti VRAM si CPU
::
::  CE PORNESTE:
::    1. ANA MAX HTTP Server (port 8765) — tooluri & API
::    2. MCP stdio bridge — Antigravity il porneste automat
::       cand deschizi IDE-ul cu workspace ana-manus
::
::  CE NU PORNESTE:
::    - Ollama (niciun model AI local)
::    - Dashboard GPU
::    - Live Log Monitor
:: ============================================================

title ANA OS-27 — Antigravity MCP Bridge [NO OLLAMA]

set "ANA_DIR=C:\Users\billy\Desktop\ana-manus\ANA_MAX"
set "PYTHON_EXE=C:\Users\billy\Desktop\ana-manus\ANA_MAX\venv\Scripts\python.exe"
set "PORT=8765"

echo.
echo  ┌─────────────────────────────────────────────────────┐
echo  │   ANA OS-27 — ANTIGRAVITY MCP BRIDGE               │
echo  │   Pornire FARA Ollama. Resurse minime.             │
echo  │                                                     │
echo  │   Antigravity va avea: Ochi + Maini (no AI local)  │
echo  └─────────────────────────────────────────────────────┘
echo.

:: Verifica Python
if not exist "%PYTHON_EXE%" (
    echo [EROARE] Python venv negasit la: %PYTHON_EXE%
    echo [INFO] Rulati START_ANA_OLLAMA.bat o data pentru setup initial.
    pause
    exit /b 1
)
echo [OK] Python venv gasit.

:: Verifica daca serverul deja ruleaza
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:%PORT%/health -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if !errorlevel! EQU 0 (
    echo [OK] ANA MAX Server deja pornit pe portul %PORT%.
    goto :server_ok
)

:: Porneste ANA MAX Server FARA backend Ollama
echo [ANA] Pornesc ANA MAX Server pe portul %PORT% (fara Ollama)...
start "ANA OS-27 MCP Bridge [:%PORT%]" /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=none & set ANA_MCP_MODE=1 & venv\Scripts\python.exe main.py --port %PORT%"

:: Asteapta server online
echo [WAIT] Astept serverul MCP (max 30 sec)...
set /a t=0
:wait_loop
timeout /t 2 >nul
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:%PORT%/health -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if !errorlevel! EQU 0 goto :server_ok
set /a t+=1
echo [WAIT] !t!/15...
if !t! GEQ 15 (
    echo.
    echo [WARN] Serverul nu a raspuns in timp util.
    echo [INFO] MCP stdio bridge functioneaza ORICUM — Antigravity il porneste direct.
    echo [INFO] Toolurile de baza (files, terminal, memory, screen) sunt disponibile.
    goto :mcp_note
)
goto :wait_loop

:server_ok
echo.
echo  [OK] ANA MAX HTTP Server online (port %PORT%)
echo.

:mcp_note
echo  ┌─────────────────────────────────────────────────────┐
echo  │  ANTIGRAVITY ARE ACUM ACCES LA:                    │
echo  │                                                     │
echo  │  OCHI   → desktop_capture, screen_grid, VLM       │
echo  │  MAINI  → terminal_tool, files, desktop_control   │
echo  │  MEMORIE→ memory_cortex (ChromaDB semantic)        │
echo  │  WEB    → ana_ultrafast_web_executor_v4            │
echo  │  SWARM  → swarm_tool (router noduri locale)        │
echo  │                                                     │
echo  │  MCP stdio: Antigravity il porneste AUTOMAT        │
echo  │  cand deschizi workspace-ul ana-manus in IDE.      │
echo  │                                                     │
echo  │  Ollama: OPRIT (economisesti VRAM + CPU)           │
echo  └─────────────────────────────────────────────────────┘
echo.
echo [INFO] Poti inchide aceasta fereastra.
echo [INFO] ANA OS-27 MCP ramane activ in spate.
echo.
pause
exit /b 0
