@echo off
:: ============================================================
:: Restore Settings Original (7B) după folosirea modelului 3B
:: ============================================================
set "ANA_DIR=C:\Users\billy\Desktop\ana-manus\ANA_MAX"

echo [RESTORE] Restaurare settings.yaml original (7B)...
if exist "%ANA_DIR%\config\settings.yaml.backup" (
    copy "%ANA_DIR%\config\settings.yaml.backup" "%ANA_DIR%\config\settings.yaml" >nul 2>&1
    echo [OK] Settings original restaurat.
    del "%ANA_DIR%\config\settings.yaml.backup" >nul 2>&1
) else (
    echo [WARN] Nu există backup settings.yaml.backup.
)
pause
