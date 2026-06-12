@echo off
setlocal
cd /d "%~dp0..\.."
if not exist "local_llm_env\Scripts\python.exe" (
  echo local_llm_env is missing. Run scripts\local_llm\create_local_llm_env.py --apply first.
  exit /b 1
)
"%CD%\local_llm_env\Scripts\python.exe" "%CD%\scripts\local_llm\start_local_llm.py" --profile os22_core --backend llama_cpp --model-path "local_models\phi3-medium-q5_k_m.gguf" --n-ctx 4096 --n-threads 6 --n-gpu-layers 0 --max-tokens 192 --interactive
endlocal
