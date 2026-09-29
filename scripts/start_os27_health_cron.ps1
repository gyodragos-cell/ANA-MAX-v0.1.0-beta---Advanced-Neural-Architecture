# scripts/start_os27_health_cron.ps1
# OS27 Hyper++ Health Cron — ruleaza integrity + radar + dashboard la interval
# Foloseste MCP Server v3 cu backend-uri reale din ANA_MAX
param(
    [int]$IntervalMinutes = 30
)

$ErrorActionPreference = "Continue"
$workspace = "c:\Users\billy\Desktop\ana-manus"
$python = "python"
$server = Join-Path $workspace "mcp\os27_mcp_server.py"
$logDir = Join-Path $workspace "logs"
$logFile = Join-Path $logDir "os27_cron.log"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = Join-Path $workspace "ANA_MAX"

if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

function Send-McpCall {
    param([string]$ToolName, [hashtable]$Arguments = @{})
    $request = @{
        jsonrpc = "2.0"
        id      = [int](Get-Date -UFormat %s)
        method  = "tools/call"
        params  = @{
            name      = $ToolName
            arguments = $Arguments
        }
    } | ConvertTo-Json -Depth 5 -Compress
    
    try {
        $result = $request | & $python $server 2>$null
        # Extract only the JSON line (skip stderr)
        $jsonLine = ($result -split "`n" | Where-Object { $_ -match '^\{' }) -join ""
        return $jsonLine
    } catch {
        return "{`"error`": `"$($_.Exception.Message)`"}"
    }
}

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-Log "OS27 Health Cron pornit. Interval: $IntervalMinutes minute."
Write-Log "MCP Server: $server"
Write-Log "Log: $logFile"

while ($true) {
    Write-Log "--- CICLU HEALTH CHECK ---"
    
    # 1. System Integrity Hyper Scan
    Write-Log "Rulez os27_system_integrity_hyper_scan..."
    $integrity = Send-McpCall -ToolName "os27_system_integrity_hyper_scan"
    $hasCritical = $false
    if ($integrity -like '*broken*' -or $integrity -like '*CRITICAL*' -or $integrity -like '*failure*') {
        Write-Log "[WARN] Integrity scan a detectat probleme."
        $hasCritical = $true
    } else {
        Write-Log "[OK] Integrity scan clean."
    }

    # 2. Error Radar Scan
    Write-Log "Rulez os27_error_radar_scan..."
    $radar = Send-McpCall -ToolName "os27_error_radar_scan"
    if ($radar -like '*CRITICAL*' -or $radar -like '*error*') {
        Write-Log "[WARN] Error Radar a detectat erori."
        $hasCritical = $true
    } else {
        Write-Log "[OK] Error Radar clean."
    }

    # 3. Dashboard Snapshot
    Write-Log "Rulez os27_dashboard_feeder_snapshot..."
    $dashboard = Send-McpCall -ToolName "os27_dashboard_feeder_snapshot"
    if ($dashboard -like '*broken*') {
        $hasCritical = $true
        Write-Log "[WARN] Dashboard raporteaza tool-uri broken."
    } else {
        Write-Log "[OK] Dashboard snapshot generat."
    }

    # 4. Telemetry Save
    Write-Log "Salvez telemetry snapshot..."
    $telSave = Send-McpCall -ToolName "os27_telemetry_engine_save"
    Write-Log "[OK] Telemetry salvat."

    # 5. Auto-Heal daca e nevoie
    if ($hasCritical) {
        Write-Log "[ALERT] Probleme critice detectate. Rulez os27_self_heal(deep=True)..."
        $heal = Send-McpCall -ToolName "os27_self_heal" -Arguments @{ deep = $true }
        Write-Log "[HEAL] Rezultat: $heal"
    }

    Write-Log "--- SFARSIT CICLU. Urmatorul in $IntervalMinutes minute. ---"
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
