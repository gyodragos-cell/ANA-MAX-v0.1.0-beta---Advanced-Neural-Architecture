@echo off
setlocal
cd /d "%~dp0..\.."

if not exist "local_llm_env\Scripts\python.exe" (
  echo local_llm_env is missing. Run scripts\local_llm\create_local_llm_env.py --apply first.
  exit /b 1
)

echo Rebuilding ANA MAX local LLM stack...
"%CD%\local_llm_env\Scripts\python.exe" "%CD%\scripts\local_llm\install_ollm_backend.py" --apply
if errorlevel 1 exit /b 1

"%CD%\local_llm_env\Scripts\python.exe" "%CD%\scripts\local_llm\validate_local_llm_setup.py"
if errorlevel 1 exit /b 1

"%CD%\local_llm_env\Scripts\python.exe" "%CD%\scripts\local_llm\test_local_brain.py" --infer
if errorlevel 1 exit /b 1

endlocal
