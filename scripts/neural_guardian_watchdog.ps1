# OS27 HYPER++ Neural Mode - Guardian Watchdog
# Logheza anomalii: ACTION -> RESULT -> NEXT STEP
# FIX: MCP server e stdio (nu TCP) - detectam prin PID, nu port

$AnaDir    = "C:\Users\billy\Desktop\ana-manus"
$LogFile   = "$AnaDir\logs\guardian_anomaly.log"
$McpScript = "$AnaDir\mcp\os27_mcp_server.py"
$PythonExe = "$AnaDir\ANA_MAX\venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }
if (-not (Test-Path "$AnaDir\logs")) {
    New-Item -ItemType Directory -Path "$AnaDir\logs" -Force | Out-Null
}

$iteration   = 0
$mcpPid      = $null   # tinem minte PID-ul pe care l-am pornit noi

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "   OS27 HYPER++ | NEURAL MODE | Guardian Active" -ForegroundColor Cyan
Write-Host "   Bucla monitorizare: 10 secunde" -ForegroundColor Cyan
Write-Host "   Log: $LogFile" -ForegroundColor DarkGray
Write-Host "   Apasa Ctrl+C pentru stop." -ForegroundColor Yellow
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host ""

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content $LogFile "[$ts] ACTION -> OS27 Neural Mode Guardian pornit"
Add-Content $LogFile "[$ts] RESULT -> Watchdog activ, bucla 10s"
Add-Content $LogFile "[$ts] NEXT STEP -> Monitorizare continua"

# Porneste MCP o singura data la inceput
$existingMcp = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*os27_mcp_server*" } |
    Select-Object -First 1

if ($existingMcp) {
    $mcpPid = $existingMcp.ProcessId
    Write-Host "[$ts] MCP server deja rulind (PID $mcpPid). Guardian preia monitorizarea." -ForegroundColor Green
} else {
    $proc = Start-Process -FilePath $PythonExe -ArgumentList "`"$McpScript`"" -WindowStyle Minimized -PassThru
    $mcpPid = $proc.Id
    Write-Host "[$ts] MCP server pornit de Guardian (PID $mcpPid)." -ForegroundColor Green
    Add-Content $LogFile "[$ts] ACTION -> MCP server pornit de Guardian (PID $mcpPid)"
    Add-Content $LogFile "[$ts] RESULT -> os27_mcp_server.py activ"
    Add-Content $LogFile "[$ts] NEXT STEP -> Monitorizare PID $mcpPid"
}

while ($true) {
    $iteration++
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $anomalies = @()

    # === Check 1: MCP Server - verifica prin PID exact ===
    $mcpAlive = $false
    if ($mcpPid) {
        $mcpAlive = (Get-Process -Id $mcpPid -ErrorAction SilentlyContinue) -ne $null
    }

    if (-not $mcpAlive) {
        $anomalies += "MCP server (PID $mcpPid) s-a oprit"
        Add-Content $LogFile "[$ts] ACTION -> Detectat: MCP server (PID $mcpPid) oprit"
        Write-Host "[$ts] ANOMALIE: MCP server oprit. Restart..." -ForegroundColor Red

        # Restart O SINGURA DATA
        $proc = Start-Process -FilePath $PythonExe -ArgumentList "`"$McpScript`"" -WindowStyle Minimized -PassThru
        $mcpPid = $proc.Id
        Start-Sleep -Seconds 3

        Add-Content $LogFile "[$ts] RESULT -> MCP restartat (PID nou: $mcpPid)"
        Add-Content $LogFile "[$ts] NEXT STEP -> Monitorizare PID $mcpPid"
        Write-Host "[$ts] RESULT -> MCP restartat PID=$mcpPid. NEXT STEP -> Monitorizare." -ForegroundColor Yellow
    }

    # === Check 2: Logs folder ===
    if (-not (Test-Path "$AnaDir\logs")) {
        $anomalies += "Director logs lips"
        Add-Content $LogFile "[$ts] ACTION -> Detectat: director logs lips"
        New-Item -ItemType Directory -Path "$AnaDir\logs" -Force | Out-Null
        Add-Content $LogFile "[$ts] RESULT -> Director logs recreat"
        Add-Content $LogFile "[$ts] NEXT STEP -> Monitorizare continua"
        Write-Host "[$ts] ANOMALIE: logs/ recreat." -ForegroundColor Yellow
    }

    # === Check 3: ana_memory.db ===
    $memDb = "$AnaDir\ana_memory.db"
    if (Test-Path $memDb) {
        $dbSize = (Get-Item $memDb).Length
        if ($dbSize -lt 100) {
            $anomalies += "ana_memory.db suspecta ($dbSize bytes)"
            Add-Content $LogFile "[$ts] ACTION -> Detectat: ana_memory.db corupta? ($dbSize B)"
            Add-Content $LogFile "[$ts] RESULT -> Semnalizat pentru inspectie manuala"
            Add-Content $LogFile "[$ts] NEXT STEP -> Verifica si restaureaza din .ana_backups"
            Write-Host "[$ts] ANOMALIE: ana_memory.db size mica ($dbSize B)!" -ForegroundColor Red
        }
    }

    # === Heartbeat la fiecare 30 iteratii (~5 min) ===
    if ($iteration % 30 -eq 0) {
        Add-Content $LogFile "[$ts] HEARTBEAT -> OS27 Neural Mode OK | Iter=$iteration | MCP PID=$mcpPid"
        Write-Host "[$ts] HEARTBEAT [iter=$iteration] Neural Mode stabil. MCP PID=$mcpPid" -ForegroundColor DarkGreen
    }

    if ($anomalies.Count -eq 0 -and $iteration % 6 -eq 0) {
        Write-Host "[$ts] Guardian OK [iter=$iteration] MCP=$mcpPid" -ForegroundColor DarkGray
    }

    Start-Sleep -Seconds 10
}
