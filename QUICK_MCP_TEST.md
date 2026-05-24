# Quick MCP Testing Guide

Use this guide to test a running ANA MAX MCP server from PowerShell.

Public repository:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

Start the server first:

```powershell
$env:MCP_API_KEY = "change-me"
python main.py
```

Server:

```text
http://127.0.0.1:8765
```

## Health Check

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing -ErrorAction Stop |
  Select-Object -ExpandProperty Content |
  ConvertFrom-Json
```

Expected:

```text
status is online
tools_count is 71
```

## List Tools

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8765/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer change-me" } `
  -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' `
  -UseBasicParsing |
  Select-Object -ExpandProperty Content |
  ConvertFrom-Json
```

## Execute A Tool

```powershell
$body = @{
    tool = "file_operations"
    params = @{
        operation = "list"
        path = "."
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8765/execute" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer change-me" } `
  -Body $body `
  -UseBasicParsing |
  Select-Object -ExpandProperty Content |
  ConvertFrom-Json
```

## Quick Script

Save as `test-mcp.ps1`:

```powershell
param(
    [string]$Url = "http://127.0.0.1:8765",
    [string]$Token = "change-me"
)

Write-Host "Testing ANA MAX MCP Server at $Url"

try {
    Write-Host "[1/3] Health check"
    $health = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -ErrorAction Stop
    $healthData = $health.Content | ConvertFrom-Json
    Write-Host "OK: $($healthData.tools_count) tools"

    Write-Host "[2/3] file_operations"
    $fileBody = @{tool="file_operations"; params=@{operation="list"; path="."}} | ConvertTo-Json
    $fileResp = Invoke-WebRequest -Uri "$Url/execute" -Method POST -ContentType "application/json" -Headers @{ Authorization = "Bearer $Token" } -Body $fileBody -UseBasicParsing
    $fileData = $fileResp.Content | ConvertFrom-Json
    Write-Host "OK: $($fileData.message)"

    Write-Host "[3/3] system_control"
    $sysBody = @{tool="system_control"; params=@{operation="vitals"}} | ConvertTo-Json
    $sysResp = Invoke-WebRequest -Uri "$Url/execute" -Method POST -ContentType "application/json" -Headers @{ Authorization = "Bearer $Token" } -Body $sysBody -UseBasicParsing
    $sysData = $sysResp.Content | ConvertFrom-Json
    Write-Host "OK: $($sysData.message)"

    Write-Host "All quick MCP checks passed"
} catch {
    Write-Host "ERROR: $_"
    exit 1
}
```

Run:

```powershell
.\test-mcp.ps1
```

## Troubleshooting

- Connection refused: make sure `python main.py` is still running.
- Unauthorized: make sure `Authorization: Bearer change-me` matches
  `MCP_API_KEY`.
- Old tool count: restart `python main.py`; a running server keeps its current
  in-memory registry.
- Tool not found: run `python main.py --list-tools` and copy the exact name.

For full setup, see `SETUP_AND_RUN.md`.
