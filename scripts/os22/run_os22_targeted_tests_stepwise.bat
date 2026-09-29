@echo off
setlocal
cd /d "%~dp0..\.."

echo [OS22] Stepwise targeted tests (visible output, per file)
echo.

echo [1/4] tests/test_start_local_llm_agent.py
python -m pytest tests/test_start_local_llm_agent.py -vv -s --maxfail=1
if errorlevel 1 goto :fail

echo.
echo [2/4] tests/test_local_brain_agent_tool_bridge.py
python -m pytest tests/test_local_brain_agent_tool_bridge.py -vv -s --maxfail=1
if errorlevel 1 goto :fail

echo.
echo [3/4] tests/test_prompt_profiles.py
python -m pytest tests/test_prompt_profiles.py -vv -s --maxfail=1
if errorlevel 1 goto :fail

echo.
echo [4/4] tests/test_senior_engineer_mode.py
python -m pytest tests/test_senior_engineer_mode.py -vv -s --maxfail=1
if errorlevel 1 goto :fail

echo.
echo [OS22] ALL STEPWISE TESTS PASSED
echo [OS22] Exit code: 0
pause
exit /b 0

:fail
echo.
echo [OS22] FAILED at current step. Exit code: %errorlevel%
echo [OS22] Stop point is the last [x/4] shown above.
pause
exit /b %errorlevel%