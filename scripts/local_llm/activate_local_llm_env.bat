@echo off
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set ROOT=%%~fI
if exist "%ROOT%\.env.local_llm" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env.local_llm") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)
if not exist "%ROOT%\local_llm_env\Scripts\activate.bat" (
  echo local_llm_env is missing. Run: python scripts\local_llm\create_local_llm_env.py --apply
  exit /b 1
)
call "%ROOT%\local_llm_env\Scripts\activate.bat"
echo ANA local LLM env activated.
