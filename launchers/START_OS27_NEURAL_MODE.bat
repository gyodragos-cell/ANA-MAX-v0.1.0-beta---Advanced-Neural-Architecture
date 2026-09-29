@echo off
setlocal enableDelayedExpansion
title OS27 HYPER++ - NEURAL MODE [Guardian Active]
color 0A

set "ANA_DIR=C:\Users\billy\Desktop\ana-manus"
set "WD_SCRIPT=%ANA_DIR%\scripts\neural_guardian_watchdog.ps1"
set "LOG_DIR=%ANA_DIR%\logs"
set "ANOMALY_LOG=%LOG_DIR%\guardian_anomaly.log"

echo.
echo  ============================================================
echo   OS27 HYPER++ ^| NEURAL MODE ^| Guardian Active
echo  ============================================================
echo.

:: Asigura logs dir
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Verifica watchdog PS1
if not exist "%WD_SCRIPT%" (
    echo [EROARE] Lipseste: %WD_SCRIPT%
    pause
    exit /b 1
)

:: Porneste DOAR Guardian Watchdog - el gestioneaza MCP intern
echo [NEURAL] Pornesc Guardian Watchdog (el porneste si MCP automat)...
start "OS27 Guardian [Neural Mode]" powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%WD_SCRIPT%"

echo.
echo  Guardian pornit. Aceasta fereastra se inchide automat.
timeout /t 3 >nul
exit /b 0
