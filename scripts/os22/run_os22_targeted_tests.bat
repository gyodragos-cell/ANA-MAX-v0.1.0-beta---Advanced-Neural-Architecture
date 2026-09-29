@echo off
setlocal
cd /d "%~dp0..\.."
echo [OS22] Running targeted tests with visible output...
python -m pytest tests/test_start_local_llm_agent.py tests/test_local_brain_agent_tool_bridge.py tests/test_prompt_profiles.py tests/test_senior_engineer_mode.py -vv -s --maxfail=1
echo.
echo [OS22] Done. Exit code: %errorlevel%
pause
exit /b %errorlevel%