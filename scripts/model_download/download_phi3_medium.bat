@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

set "MODEL_DIR=local_models"
set "MODEL_FILE=%MODEL_DIR%\phi3-medium-q5_k_m.gguf"
set "MODEL_URL=https://huggingface.co/microsoft/Phi-3-medium-4k-instruct-gguf/resolve/main/Phi-3-medium-4k-instruct-q5_k_m.gguf"
set "MIN_SIZE=9000000000"

if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"

echo ============================================================
echo Phi-3 Medium GGUF Q5_K_M download/verify
echo Target: %MODEL_FILE%
echo ============================================================

if exist "%MODEL_FILE%" (
  echo [INFO] Model already exists. Skipping download.
) else (
  echo [INFO] Downloading Phi-3 Medium GGUF Q5_K_M...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%MODEL_URL%' -OutFile '%MODEL_FILE%'"
  if errorlevel 1 (
    echo [ERROR] Download failed.
    exit /b 1
  )
)

for %%A in ("%MODEL_FILE%") do set "MODEL_SIZE=%%~zA"
echo [INFO] Size: !MODEL_SIZE! bytes
powershell -NoProfile -ExecutionPolicy Bypass -Command "if ([int64]'!MODEL_SIZE!' -lt [int64]'%MIN_SIZE%') { exit 1 }"
if errorlevel 1 (
  echo [ERROR] File size is too small.
  exit /b 1
)

echo [INFO] Computing SHA256...
for /f "tokens=1" %%H in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -Algorithm SHA256 -Path '%MODEL_FILE%').Hash.ToLower()"') do set "MODEL_SHA256=%%H"
echo [INFO] SHA256: !MODEL_SHA256!

if not "%PHI3_MEDIUM_SHA256%"=="" (
  if /I not "!MODEL_SHA256!"=="%PHI3_MEDIUM_SHA256%" (
    echo [ERROR] SHA256 mismatch.
    exit /b 1
  )
  echo [INFO] SHA256 matches PHI3_MEDIUM_SHA256.
) else (
  echo [INFO] No PHI3_MEDIUM_SHA256 provided; recorded SHA256 above.
)

echo SUCCESS
exit /b 0
