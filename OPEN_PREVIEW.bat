@echo off
setlocal

cd /d "%~dp0"

echo Opening ANA MAX website preview...
echo.
echo If the browser shows a local file path, that is OK for private preview.
echo Public sharing must use GitHub Pages.
echo.

start "" "%~dp0index.html"
