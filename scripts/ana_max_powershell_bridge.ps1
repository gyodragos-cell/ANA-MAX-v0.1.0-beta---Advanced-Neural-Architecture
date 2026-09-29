#!/usr/bin/env pwsh
# ANA MAX PowerShell Bridge
# ========================
# Expune tool-urile ANA MAX direct în PowerShell pentru integrare cu Windows Copilot

param(
    [string]$ToolName,
    [hashtable]$Arguments = @{}
)

$ErrorActionPreference = "Stop"

# Configurare cai
$ANA_MANUS_ROOT = "C:\Users\billy\Desktop\ana-manus"
$PYTHON_VENV = "$ANA_MANUS_ROOT\ANA_MAX\venv\Scripts\python.exe"
$BRIDGE_SCRIPT = "$ANA_MANUS_ROOT\ANA_MAX\bridge\direct_bridge.py"

# Verifică venv
if (-not (Test-Path $PYTHON_VENV)) {
    Write-Error "Python venv not found at $PYTHON_VENV"
    exit 1
}

# Verifică bridge
if (-not (Test-Path $BRIDGE_SCRIPT)) {
    Write-Error "Bridge script not found at $BRIDGE_SCRIPT"
    exit 1
}

# Set environment
$env:ana_manus_ROOT = $ANA_MANUS_ROOT
$env:PYTHONPATH = $ANA_MANUS_ROOT

# Funcție pentru a executa tool
function Invoke-ANATool {
    param(
        [string]$Name,
        [hashtable]$Args = @{}
    )
    
    # Convert arguments to JSON
    $argsJson = $Args | ConvertTo-Json -Compress
    
    # Execute through Python bridge
    $pythonCode = @"
import sys
import json
sys.path.insert(0, r'$ANA_MANUS_ROOT')
sys.path.insert(0, r'$ANA_MANUS_ROOT\ANA_MAX')

try:
    from bridge.direct_bridge import DirectBridge
    bridge = DirectBridge(include_hybrid_tools=True)
    result = bridge.execute_tool('$Name', json.loads('''$argsJson'''), confirm=True)
    print(json.dumps(result, default=str))
except Exception as e:
    print(json.dumps({'error': str(e)}), default=str)
"@
    
    $output = & $PYTHON_VENV -c $pythonCode 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tool execution failed: $output"
        return $null
    }
    
    try {
        return $output | ConvertFrom-Json
    }
    catch {
        return $output
    }
}

# List available tools
function Get-ANATools {
    $pythonCode = @"
import sys
import json
sys.path.insert(0, r'$ANA_MANUS_ROOT')
sys.path.insert(0, r'$ANA_MANUS_ROOT\ANA_MAX')

try:
    from tools.base import registry
    tools = registry.list_tools()
    print(json.dumps(tools, default=str))
except Exception as e:
    print(json.dumps({'error': str(e)}), default=str)
"@
    
    $output = & $PYTHON_VENV -c $pythonCode 2>&1
    try {
        return $output | ConvertFrom-Json
    }
    catch {
        return $output
    }
}

# Main logic
if ($ToolName -eq "list") {
    Get-ANATools | Format-Table -AutoSize
}
elseif ($ToolName) {
    $result = Invoke-ANATool -Name $ToolName -Args $Arguments
    if ($result) {
        $result | ConvertTo-Json -Depth 10
    }
}
else {
    Write-Host "ANA MAX PowerShell Bridge" -ForegroundColor Cyan
    Write-Host "Usage: .\ana_max_powershell_bridge.ps1 -ToolName <name> [-Arguments @{}]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Available tools:" -ForegroundColor Green
    Get-ANATools | Format-Table -AutoSize
}
