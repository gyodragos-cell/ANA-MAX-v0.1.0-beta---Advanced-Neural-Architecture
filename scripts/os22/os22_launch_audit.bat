@echo off
setlocal

cd /d "%~dp0\..\.."

echo Running ANA_MAX OS-22 launch audit...
python scripts\os22\os22_launch_audit.py --write-report

echo.
echo Report: ANA_MAX\memory\os22_launch_audit_report.json
pause
