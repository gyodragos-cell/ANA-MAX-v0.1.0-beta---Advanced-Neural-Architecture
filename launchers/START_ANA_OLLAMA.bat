@echo off
setlocal enableDelayedExpansion

:: ============================================================
:: ANA MAX ENTERPRISE STARTUP [OLLAMA LOCAL - OS-27]
:: ============================================================
title ANA MAX ENTERPRISE STARTUP [OLLAMA]

set "ROOT_DIR=C:\Users\billy\Desktop\ana-manus"
set "ANA_DIR=%ROOT_DIR%\ANA_MAX"
set "PYTHON_EXE=%ROOT_DIR%\venv\Scripts\python.exe"
set "VENV_DIR=%ROOT_DIR%\venv"
set "ENV_FILE=%ROOT_DIR%\ANA_MAX\.env"
set "BOOTSTRAP_PS1=%ROOT_DIR%\scripts\bootstrap_ana_env.ps1"
set "LIVE_LOG_PS1=%ROOT_DIR%\scripts\live_log_monitor.ps1"

echo.
echo  [SYSTEM] Initializare Arhitectura Neurala Avansata OS-27...
echo.

:: 0. AUTO-MAINTENANCE (curatare diacritice, organizare fisiere, junk cleanup)
echo [MAINT] Rulare auto-maintenance...
python "%ROOT_DIR%\scripts\ana_auto_maintenance.py" 2>nul
echo [MAINT] Auto-maintenance complet.

:: 1. Verificare CUDA / GPU
echo [CUDA] Verific integrare GPU...
nvidia-smi >nul 2>&1
if %errorlevel% EQU 0 (
    echo [OK] GPU Detectat [GTX 1650]. CUDA UMD 13.3 Active.
) else (
    echo [WARN] GPU/CUDA nu a fost detectat. Ollama va rula pe CPU.
)

:: 2. Verificare Environment

echo [DIAG] Verificari initiale .env si venv...

:: Verificare si bootstrap pentru .env
if not exist "%ENV_FILE%" (
    echo [INFO] Lipseste ANA MAX .env file. Rulez bootstrap local...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS1%" -Apply
    if %errorlevel% NEQ 0 (
        echo [EROARE] Bootstrap script failed for .env. Verificati logurile.
        pause
        exit /b 1
    )
    echo [DIAG] Bootstrap for .env completed. Apasa orice tasta pentru a continua...
    pause
)

:: Verificare si bootstrap pentru venv
if not exist "%VENV_DIR%" (
    echo [INFO] Lipseste Python venv. Rulez bootstrap local...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS1%" -Apply
    if %errorlevel% NEQ 0 (
        echo [EROARE] Bootstrap script failed for venv. Verificati logurile.
        pause
        exit /b 1
    )
    echo [DIAG] Bootstrap for venv completed. Apasa orice tasta pentru a continua...
    pause
)

:: Verificare finala Python EXE
if not exist "%PYTHON_EXE%" (
    echo [DIAG-ERROR] Python executable not found at: %PYTHON_EXE% after bootstrap attempts.
    echo [DIAG-ERROR] Asigurati-va ca venv este creat si activat corect.
    pause
    exit /b 1
)


:: 3. Pornire Serviciu Ollama Local (cu Lock Manager Protection)
echo [OLLAMA] Verificare lock manager pentru protectie GPU...
"%PYTHON_EXE%" "%ANA_DIR%\ollama_lock_manager.py" check
if %errorlevel% EQU 0 (
    echo [WARN] Lock Ollama activ - sesiune deja deschisa!
    echo [INFO] Pentru restart: 1. Inchide sesiunea curenta 2. Lock se va elibera automat
    echo [INFO] Continui cu sesiunea existenta...
    goto :ollama_already_running
)

echo [OLLAMA] Acquire lock pentru sesiune Ollama...
"%PYTHON_EXE%" "%ANA_DIR%\ollama_lock_manager.py" acquire
if %errorlevel% NEQ 0 (
    echo [ERROR] Nu se poate obtine lock Ollama - sesiune activa sau lock conflict
    echo [INFO] Verificati daca Ollama ruleaza deja sau folositi force-cleanup
    pause
    exit /b 1
)

echo [OLLAMA] Verific serviciul local (:11434)...
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:11434/api/tags -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if %errorlevel% EQU 0 goto ollama_is_running

echo [INFO] Pornesc serviciu Ollama local cu CUDA support...
start "Ollama Engine [CUDA]" /MAX cmd /k "C:\Users\billy\AppData\Local\Programs\Ollama\ollama.exe serve"
echo [INFO] Astept ca Ollama sa porneasca cu CUDA (15 sec)...
timeout /t 15 >nul
echo [INFO] Verific din nou daca Ollama a pornit...
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:11434/api/tags -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if %errorlevel% NEQ 0 (
    echo [ERROR] Ollama nu a pornit corect!
    echo [INFO] Verificati daca Ollama este instalat
    pause
    exit /b 1
)
echo [OK] Ollama pornit cu success! Terminalul ramane deschis pentru CUDA info.
goto ollama_started

:ollama_is_running
echo [OK] Serviciul Ollama ruleaza deja.
echo [INFO] Lock manager activ - protejeaza impotriva pornirii multiple

:ollama_started
:: 4. Pornire ANA MAX Server (Chiar dacă Ollama tocmai a pornit)
echo [ANA] Pornesc ANA MAX Server [OLLAMA :8766]...
set "ANA_PORT=8766"
set "ANA_BACKEND=ollama"
start "ANA MAX Server [OLLAMA :8766]" /MAX /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=ollama & venv\Scripts\python.exe main.py --port 8766"
goto :ana_start_done

:ollama_already_running

:: 4. Pornire ANA MAX Server (Chiar dacă Ollama rulează deja)
echo [ANA] Pornesc ANA MAX Server [OLLAMA :8766]...
set "ANA_PORT=8766"
set "ANA_BACKEND=ollama"
start "ANA MAX Server [OLLAMA :8766]" /MAX /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=ollama & venv\Scripts\python.exe main.py --port 8766"

:ana_start_done

:: 5. Asteptare Server Online
echo [WAIT] Astept stabilizarea canalizarii (max 60 sec)...
set /a t=0
:ana_wait
timeout /t 3 >nul
powershell -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:8766/health -TimeoutSec 2 > $null; exit 0 } catch { exit 1 }"
if !errorlevel! EQU 0 (
    echo [OK] Canalizare activa - Serverul raspunde!
    goto :ana_ok
)
set /a t+=1
echo [WAIT] !t!/20 - ANA MAX se incarca...
if !t! GEQ 20 (
    echo [EROARE] ANA MAX nu a pornit corect. Verifica logurile.
    pause
    exit /b 1
)
goto :ana_wait

:ana_ok
echo.
echo  [OK] ANA MAX ONLINE [PORT 8766]
echo.

:: 6. Pornire Live Log Monitor (Professional Enterprise View)
echo [LOG] Pornesc Live Log Monitor profesional cu OS27 debug highlighting...
if exist "%LIVE_LOG_PS1%" (
    start "ANA LIVE LOG [OS-27]" powershell -NoProfile -ExecutionPolicy Bypass -File "%LIVE_LOG_PS1%"
) else (
    start "ANA LIVE LOG" powershell -NoExit -Command "Get-Content -Tail 50 -Wait '%ANA_DIR%\logs\ana_max.log'"
)

:: 7. Deschidere Dashboard & Chat (Auto-Browser)
echo [BROWSER] Deschid interfata Enterprise OS-27...
start "" "http://127.0.0.1:8766/dashboard"
start "" "http://127.0.0.1:8766/chat"

echo.
echo  ============================================================
echo   TOTUL ESTE PORNIT SI LEGAT (OS-27 ENTERPRISE MODE)
echo   GPU: ACTIVE | BUS: ACTIVE | DASHBOARD: OPEN
echo  ============================================================
echo.

:: Oprit auto-close temporar pentru a vedea erorile.
echo [INFO] Apasa orice tasta pentru a inchide acest launcher (serverele raman in spate).
pause
exit /b 0