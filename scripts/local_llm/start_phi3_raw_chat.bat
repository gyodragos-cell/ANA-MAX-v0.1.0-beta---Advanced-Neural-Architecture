@echo off
setlocal
cd /d "%~dp0\..\.."
"%CD%\local_llm_env\Scripts\python.exe" "%CD%\scripts\local_llm\start_phi3_raw_chat.py" --profile raw --temperature 0.45 --max-tokens 192 %*
endlocal
