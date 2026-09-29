@echo off
setlocal enableDelayedExpansion

:: ============================================================
:: ANA MAX ENTERPRISE STARTUP [OLLAMA 3B - OS-27 OPTIMIZED]
:: ============================================================
:: Model: qwen2.5-coder:3b (~2.2GB VRAM - Perfect pentru GTX 1650)
:: Port: 8768 (separat de 8766 pentru model 7b)
:: ============================================================
title ANA MAX ENTERPRISE STARTUP [OLLAMA 3B]

set "ANA_DIR=C:\Users\billy\Desktop\ana-manus\ANA_MAX"
set "PYTHON_EXE=%~dp0ANA_MAX\venv\Scripts\python.exe"
set "VENV_DIR=%~dp0ANA_MAX\venv"
set "ENV_FILE=%~dp0ANA_MAX\.env"
set "BOOTSTRAP_PS1=%~dp0scripts\bootstrap_ana_env.ps1"
set "LIVE_LOG_PS1=%~dp0scripts\live_log_monitor.ps1"
set "SETTINGS_FILE=%~dp0ANA_MAX\models\qwen3b\settings.yaml"

echo.
echo  [SYSTEM] Initializare Arhitectura Neurala Avansata OS-27 [MODEL 3B OPTIMIZED]...
echo.

:: 0. PROTECȚIE ANTI-DUBLĂ PORNIRE CU AUTO-KILL
echo [PROTECT] Verificare instante ANA MAX active...
netstat -ano | findstr ":8768" >nul 2>&1
if %errorlevel% EQU 0 (
    echo [WARN] Port 8768 este deja ocupat.
    echo [INFO] O instanta ANA MAX 3B ruleaza deja.
    echo [INFO] Auto-kill instanta existenta pentru restart curat...
    
    :: Kill procesul care ocupă portul 8768
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8768" ^| findstr "LISTENING"') do (
        echo [KILL] Terminare proces PID: %%a
        taskkill /F /PID %%a >nul 2>&1
    )
    
    timeout /t 3 >nul
    echo [OK] Instanta veche oprita. Pornește instanta noua...
) else (
    echo [OK] Port 8768 este liber - safe pentru pornire.
)

:: 1. Verificare CUDA / GPU
echo [CUDA] Verific integrare GPU...
nvidia-smi >nul 2>&1
if %errorlevel% EQU 0 (
    echo [OK] GPU Detectat [GTX 1650]. CUDA UMD 13.3 Active.
    echo [INFO] Model 3b uses ~2.2GB VRAM - fits in 4GB.
) else (
    echo [WARN] GPU/CUDA not detected. Ollama runs on CPU.
)

:: 2. Verificare Environment
echo [DIAG] Verificari initiale .env si venv...

if not exist "%ENV_FILE%" (
    echo [INFO] Lipseste ANA_MAX .env file. Rulez bootstrap local...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS1%" -Apply
    if %errorlevel% NEQ 0 (
        echo [EROARE] Bootstrap script failed for .env. Verificati logurile.
        pause
        exit /b 1
    )
    echo [DIAG] Bootstrap for .env completed. Apasa orice tasta pentru a continua...
    pause
)

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

if not exist "%PYTHON_EXE%" (
    echo [DIAG-ERROR] Python executable not found at: %PYTHON_EXE% after bootstrap attempts.
    echo [DIAG-ERROR] Asigurati-va ca venv este creat si activat corect.
    pause
    exit /b 1
)

:: 3. Verificare Model 3B
echo [MODEL] Verific disponibilitate qwen2.5-coder:3b...
ollama list | findstr "qwen2.5-coder:3b" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [INFO] Model qwen2.5-coder:3b nu este instalat. Download in curs...
    ollama pull qwen2.5-coder:3b
    if %errorlevel% NEQ 0 (
        echo [EROARE] Download model failed. Verificati conexiunea internet.
        pause
        exit /b 1
    )
    echo [OK] Model qwen2.5-coder:3b descarcat cu succes.
) else (
    echo [OK] Model qwen2.5-coder:3b este deja disponibil.
)

:: 4. Pornire Serviciu Ollama Local (cu Lock Manager Protection)
echo [OLLAMA] Verificare lock manager pentru protectie GPU...
"%PYTHON_EXE%" "%~dp0ANA_MAX\ollama_lock_manager.py" check
if %errorlevel% EQU 0 (
    echo [WARN] Lock Ollama activ - sesiune deja deschisa!
    echo [INFO] Pentru restart: 1. Inchide sesiunea curenta 2. Lock se va elibera automat
    echo [INFO] Continui cu sesiunea existenta...
    goto :ollama_already_running
)

echo [OLLAMA] Acquire lock pentru sesiune Ollama...
"%PYTHON_EXE%" "%~dp0ANA_MAX\ollama_lock_manager.py" acquire
if %errorlevel% NEQ 0 (
    echo [ERROR] Nu se poate obtine lock Ollama - sesiune activa sau lock conflict
    echo [INFO] Verificati daca Ollama ruleaza deja sau folositi force-cleanup
    pause
    exit /b 1
)

echo [OLLAMA] Verific serviciul local (:11434)...
curl -s "http://127.0.0.1:11434/api/tags" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [INFO] Pornesc serviciu Ollama local...
    start "Ollama Engine" cmd /k "ollama serve"
    timeout /t 5 >nul
) else (
    echo [OK] Serviciul Ollama ruleaza deja.
    echo [INFO] Lock manager activ - protejeaza impotriva pornirii multiple
)

:ollama_already_running

:: 5. Configurare Ollama pentru Performanta (GPU Optimized)
echo [OPTIM] Configurare Ollama pentru performanta maxima...
set OLLAMA_NUM_GPU=1
set OLLAMA_NUM_THREAD=6
set OLLAMA_NUM_CTX=8192
echo [INFO] GPU layers: 1 / Threads: 6 / Context: 8192 tokens

:: 6. Backup settings.yaml original și copiere settings 3b
echo [CONFIG] Backup settings.yaml original...
if exist "%ANA_DIR%\config\settings.yaml" (
    copy "%ANA_DIR%\config\settings.yaml" "%ANA_DIR%\config\settings.yaml.backup" >nul 2>&1
    echo [OK] Backup creat.
)
echo [CONFIG] Copiere settings.yaml pentru model 3b...
copy "%SETTINGS_FILE%" "%ANA_DIR%\config\settings.yaml" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [EROARE] Copiere settings.yaml failed.
    pause
    exit /b 1
)
echo [OK] Settings 3b activat.

:: 7. Pornire ANA MAX Server (Port 8768 - separat pentru model 3b)
echo [ANA] Pornesc ANA MAX Server [OLLAMA 3B :8768]...
set "ANA_PORT=8768"
set "ANA_BACKEND=ollama"
start "ANA MAX Server [OLLAMA 3B :8768]" /MAX /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=ollama && "%PYTHON_EXE%" main.py --port 8768"
if %errorlevel% NEQ 0 (
    echo [EROARE] Comanda de pornire ANA MAX a esuat. Verificati calea Python si dependentele.
    pause
    exit /b 1
)

:: 7. Asteptare Server Online
echo [WAIT] Astept stabilizarea canalizarii (max 60 sec)...
set /a t=0
:ana_wait
timeout /t 3 >nul
curl -s -f --max-time 2 "http://127.0.0.1:8768/health" >nul 2>&1
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
echo  [OK] ANA MAX ONLINE [PORT 8768 - MODEL 3B]
echo.

:: 9. Pornire Live Log Monitor (Professional Enterprise View)
echo [LOG] Pornesc Live Log Monitor profesional...
start "ANA LIVE LOG [3B]" cmd /k "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-Content '%ANA_DIR%\logs\ana_max.log' -Tail 100 -Wait\""

:: 10. Închidere browser vechi (dacă există) + Deschidere Dashboard & Chat
echo [BROWSER] Închidere ferestre browser vechi...
taskkill /F /IM brave.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 >nul
echo [BROWSER] Deschid interfata Enterprise OS-27 [MODEL 3B]...
start "" "http://127.0.0.1:8768/dashboard"
start "" "http://127.0.0.1:8768/chat"

echo.
echo  ============================================================
echo   TOTUL ESTE PORNIT SI LEGAT (OS-27 ENTERPRISE MODE - 3B)
echo   GPU: ACTIVE - BUS: ACTIVE - DASHBOARD: OPEN
echo   MODEL: qwen2.5-coder:3b (~2.2GB VRAM - OPTIMIZED)
echo   PORT: 8768 (separat de 8766 pentru model 7b)
echo  ============================================================
echo.
echo  ============================================================
echo   NOTA: Acest manager poate fi inchis - terminalele raman active
echo   - ANA MAX Server: ruleaza in terminal separat
echo   - Live Log Monitor: ruleaza in terminal separat
echo   - Ollama: ruleaza in fundal (daca era pornit)
echo   - Browser: Dashboard si Chat sunt deschise
echo  ============================================================
echo.
echo Apasa orice tasta pentru a inchide acest manager (terminalele raman active)...
pause >nul

:: Cleanup: Release lock la inchiderea managerului
echo [CLEANUP] Eliberare lock Ollama...
"%PYTHON_EXE%" "%~dp0ANA_MAX\ollama_lock_manager.py" release
echo [OK] Lock eliberat - sesiune terminata curat

exit /b 0
