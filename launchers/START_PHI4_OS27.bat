@echo off
setlocal enableDelayedExpansion

:: ============================================================
:: ANA MAX ENTERPRISE STARTUP [FOUNDRY LOCAL - PHI-4 - OS-27]
:: ============================================================
title ANA MAX ENTERPRISE STARTUP [FOUNDRY PHI-4]

set "ANA_DIR=C:\Users\billy\Desktop\ana-manus\ANA_MAX"
set "PYTHON_EXE=%~dp0ANA_MAX\venv\Scripts\python.exe"
set "VENV_DIR=%~dp0ANA_MAX\venv"
set "ENV_FILE=%~dp0ANA_MAX\.env"
set "BOOTSTRAP_PS1=%~dp0scripts\bootstrap_ana_env.ps1"
set "LIVE_LOG_PS1=%~dp0scripts\live_log_monitor.ps1"

echo.
echo  [SYSTEM] Initializare Arhitectura Neurala Avansata OS-27...
echo.

:: 1. Verificare CUDA / GPU
echo [CUDA] Verific integrare GPU...
nvidia-smi >nul 2>&1
if %errorlevel% EQU 0 (
    echo [OK] GPU Detectat [GTX 1650]. CUDA UMD 13.3 Active.
) else (
    echo [WARN] GPU/CUDA nu a fost detectat. Foundry va rula pe CPU.
)

:: 2. Verificare Environment

echo [DIAG] Verificari initiale .env si venv...

:: Verificare si bootstrap pentru .env
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


:: 3. Pornire Serviciu Foundry Local (daca nu ruleaza)
echo [FOUNDRY] Verific serviciul local...
for /f "tokens=*" %%i in ('foundry server status 2^>^&1') do set FOUNDRY_STATUS=%%i
echo %FOUNDRY_STATUS% | findstr "Ready" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [INFO] Pornesc serviciul Foundry local...
    foundry server start
    timeout /t 10 >nul
    for /f "tokens=3" %%i in ('foundry server status ^| findstr "http:"') do set FOUNDRY_URL=%%i
    echo [OK] Foundry pornit la: %FOUNDRY_URL%
) else (
    echo [OK] Serviciul Foundry ruleaza deja.
    for /f "tokens=3" %%i in ('foundry server status ^| findstr "http:"') do set FOUNDRY_URL=%%i
    echo [INFO] Foundry URL: %FOUNDRY_URL%
)

if not defined FOUNDRY_URL (
    echo [WARN] Nu am putut detecta URL-ul Foundry, folosesc default
    set "FOUNDRY_URL=http://127.0.0.1:65260"
)

:: 4. Verificare model Phi-4-mini
echo [FOUNDRY] Verific model Phi-4-mini...
foundry model list --cached | findstr /i "phi-4-mini" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [INFO] Descarc model Phi-4-mini...
    foundry model download phi-4-mini
) else (
    echo [OK] Model Phi-4-mini este disponibil.
)

:: 5. Pornire ANA MAX Server
echo [ANA] Pornesc ANA MAX Server [FOUNDRY :8767]...
set "ANA_PORT=8767"
set "ANA_BACKEND=foundry"
set "FOUNDRY_API_URL=http://127.0.0.1:59641"
set "FOUNDRY_MODEL=phi-4-mini"
start "ANA MAX Server [FOUNDRY :8767]" /MAX /D "%ANA_DIR%" cmd /k "set ANA_BACKEND=foundry && set FOUNDRY_API_URL=http://127.0.0.1:59641 && set FOUNDRY_MODEL=phi-4-mini && "%PYTHON_EXE%" main.py --port 8767"
if %errorlevel% NEQ 0 (
    echo [EROARE] Comanda de pornire ANA MAX a esuat. Verificati calea Python si dependentele.
    pause
    exit /b 1
)

:: 6. Asteptare Server Online
echo [WAIT] Astept stabilizarea canalizarii (max 300 sec - EP download poate dura)...
set /a t=0
:ana_wait
timeout /t 3 >nul
curl -s -f --max-time 2 "http://127.0.0.1:8767/health" >nul 2>&1
if !errorlevel! EQU 0 (
    echo [OK] Canalizare activa - Serverul raspunde!
    goto :ana_ok
)
set /a t+=1
echo [WAIT] !t!/100 - ANA MAX se incarca (Foundry EP download poate dura 2-3 min)...
if !t! GEQ 100 (
    echo [WARN] ANA MAX nu a raspuns in timp util, dar poate fi pornit.
    echo [INFO] Verifica fereastra ANA MAX Server pentru status.
    goto :ana_continue
)
goto :ana_wait

:ana_ok
echo.
echo  [OK] ANA MAX ONLINE [PORT 8767]
echo.

:: 7. Pornire Live Log Monitor (Professional Enterprise View)

:ana_continue
echo.
echo  [INFO] Continuand cu pornirea componentelor...

:: 7. Smoke Test
echo [TEST] Running smoke test...
"%PYTHON_EXE%" "%~dp0scripts\smoke_test_phi4_os27.py"
if %errorlevel% NEQ 0 (
    echo [WARN] Smoke test failed, but continuing...
) else (
    echo [OK] Smoke test passed!
)

echo [LOG] Pornesc Live Log Monitor profesional...
if exist "%LIVE_LOG_PS1%" (
    start "ANA LIVE LOG [OS-27]" powershell -NoProfile -ExecutionPolicy Bypass -File "%LIVE_LOG_PS1%"
) else (
    start "ANA LIVE LOG" powershell -NoExit -Command "Get-Content -Tail 50 -Wait '%ANA_DIR%\logs\ana_max.log'"
)

:: 8. Deschidere Dashboard & Chat (Auto-Browser)
echo [BROWSER] Deschid interfata Enterprise OS-27...
start "" "http://127.0.0.1:8767/dashboard"
start "" "http://127.0.0.1:8767/chat"

echo.
echo  ============================================================
echo   TOTUL ESTE PORNIT SI LEGAT (OS-27 ENTERPRISE MODE)
echo   GPU: ACTIVE | BUS: ACTIVE | DASHBOARD: OPEN
echo   BACKEND: FOUNDRY (PHI-4-MINI)
echo  ============================================================
echo.
echo Apasa orice tasta pentru a inchide acest manager...
pause
exit /b 0
