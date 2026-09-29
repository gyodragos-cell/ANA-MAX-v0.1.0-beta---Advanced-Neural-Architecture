@echo off
setlocal
cd /d "%~dp0..\.."

set "LOG=ANA_MAX\logs\os22_stepwise_tests.log"
if not exist "ANA_MAX\logs" mkdir "ANA_MAX\logs"

echo [OS22] Stepwise targeted tests (no pause) > "%LOG%"
echo Started: %date% %time% >> "%LOG%"
echo. >> "%LOG%"

echo [1/4] tests/test_start_local_llm_agent.py
echo [1/4] tests/test_start_local_llm_agent.py >> "%LOG%"
python -m pytest tests/test_start_local_llm_agent.py -vv -s --maxfail=1 >> "%LOG%" 2>&1
if errorlevel 1 goto :fail

echo [2/4] tests/test_local_brain_agent_tool_bridge.py
echo [2/4] tests/test_local_brain_agent_tool_bridge.py >> "%LOG%"
python -m pytest tests/test_local_brain_agent_tool_bridge.py -vv -s --maxfail=1 >> "%LOG%" 2>&1
if errorlevel 1 goto :fail

echo [3/4] tests/test_prompt_profiles.py
echo [3/4] tests/test_prompt_profiles.py >> "%LOG%"
python -m pytest tests/test_prompt_profiles.py -vv -s --maxfail=1 >> "%LOG%" 2>&1
if errorlevel 1 goto :fail

echo [4/4] tests/test_senior_engineer_mode.py
echo [4/4] tests/test_senior_engineer_mode.py >> "%LOG%"
python -m pytest tests/test_senior_engineer_mode.py -vv -s --maxfail=1 >> "%LOG%" 2>&1
if errorlevel 1 goto :fail

echo [OS22] ALL STEPWISE TESTS PASSED
echo [OS22] ALL STEPWISE TESTS PASSED >> "%LOG%"
echo Finished: %date% %time% >> "%LOG%"
exit /b 0

:fail
echo [OS22] FAILED at current step. Exit code: %errorlevel%
echo [OS22] FAILED at current step. Exit code: %errorlevel% >> "%LOG%"
echo Finished: %date% %time% >> "%LOG%"
exit /b %errorlevel%