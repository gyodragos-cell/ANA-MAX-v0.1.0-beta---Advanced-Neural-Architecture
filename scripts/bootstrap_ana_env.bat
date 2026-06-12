@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_ana_env.ps1" %*
exit /b %errorlevel%

