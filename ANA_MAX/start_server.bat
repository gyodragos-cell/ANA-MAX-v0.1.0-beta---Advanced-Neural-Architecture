@echo off
rem Start ANA_MAX services (Ollama + MCP server)

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

set OLLAMA_GPU=1
set OLLAMA_DEBUG=1

echo Pornesc Ollama...
start "Ollama Server" cmd /k "C:\Users\billy\AppData\Local\Programs\Ollama\ollama.exe serve"

echo Pornesc MCP Server...
start "MCP Server" cmd /k "python -c ""import main; main._start_mcp_server('127.0.0.1', 8765)"""

echo Serviciile au fost lansate in ferestre separate.
pause
