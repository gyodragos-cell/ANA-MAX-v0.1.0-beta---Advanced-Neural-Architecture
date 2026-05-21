# 🧪 Quick MCP Testing Guide

Test ANA MAX MCP tools rapid cu PowerShell. MCP server trebuie pornit pe `http://127.0.0.1:8765`.

---

## 1️⃣ Health Check
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing -ErrorAction Stop | 
  Select-Object -ExpandProperty Content | ConvertFrom-Json
```
**Expected:** Status=online, 42 tools listed

---

## 2️⃣ List All Tools
```powershell
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8765/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"method":"tools/list","params":{}}' `
  -UseBasicParsing

$response.Content | ConvertFrom-Json | Select-Object -ExpandProperty result | 
  Select-Object -ExpandProperty tools | ConvertTo-Json -Depth 2
```

---

## 3️⃣ Execute Tool: File Operations
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
  -Body $body `
  -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 4️⃣ Execute Tool: System Vitals
```powershell
$body = @{
    tool = "system_control"
    params = @{
        operation = "vitals"
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8765/execute" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 5️⃣ Execute Tool: Windows UI Bridge
```powershell
$body = @{
    tool = "windows_uia_bridge"
    params = @{
        action = "find_windows"
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8765/execute" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 6️⃣ Test MCP JSON-RPC Format
```powershell
$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/call"
    params = @{
        name = "file_operations"
        arguments = @{
            operation = "list"
            path = "."
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://127.0.0.1:8765/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 🎯 Full Test Script

Salveaza ca `test-mcp.ps1`:
```powershell
param(
    [string]$Url = "http://127.0.0.1:8765"
)

Write-Host "🧪 Testing ANA MAX MCP Server at $Url" -ForegroundColor Cyan
Write-Host ""

try {
    # Health
    Write-Host "[1/3] Health Check..." -ForegroundColor Yellow
    $health = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -ErrorAction Stop
    $healthData = $health.Content | ConvertFrom-Json
    Write-Host "✅ Online - $($healthData.tools_count) tools" -ForegroundColor Green
    Write-Host ""

    # File ops
    Write-Host "[2/3] Testing file_operations..." -ForegroundColor Yellow
    $fileBody = @{tool="file_operations"; params=@{operation="list"; path="."}} | ConvertTo-Json
    $fileResp = Invoke-WebRequest -Uri "$Url/execute" -Method POST -ContentType "application/json" -Body $fileBody -UseBasicParsing
    $fileData = $fileResp.Content | ConvertFrom-Json
    Write-Host "✅ Success: $($fileData.message)" -ForegroundColor Green
    Write-Host ""

    # System vitals
    Write-Host "[3/3] Testing system_control..." -ForegroundColor Yellow
    $sysBody = @{tool="system_control"; params=@{operation="vitals"}} | ConvertTo-Json
    $sysResp = Invoke-WebRequest -Uri "$Url/execute" -Method POST -ContentType "application/json" -Body $sysBody -UseBasicParsing
    $sysData = $sysResp.Content | ConvertFrom-Json
    Write-Host "✅ Success: $($sysData.message)" -ForegroundColor Green
    Write-Host ""

    Write-Host "🎉 All tests passed!" -ForegroundColor Green

} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
```

**Run:**
```powershell
.\test-mcp.ps1
```

---

## Expected Output Example
```
🧪 Testing ANA MAX MCP Server at http://127.0.0.1:8765

[1/3] Health Check...
✅ Online - 42 tools

[2/3] Testing file_operations...
✅ Success: Found 26 items

[3/3] Testing system_control...
✅ Success: Vitals obtained

🎉 All tests passed!
```

---

## Troubleshooting

### Connection Refused
- Verifica daca `python main.py` e pornit
- Verifica portul: `netstat -ano | grep 8765`

### Invalid JSON Response
- Check MCP server logs in terminal
- Verifica payload-ul JSON format

### Tool Not Found
- Run `python main.py --list-tools` pentru lista exacta
- Verify tool name spelling

---

**Need help?** Check `SETUP_AND_RUN.md` for full documentation.
