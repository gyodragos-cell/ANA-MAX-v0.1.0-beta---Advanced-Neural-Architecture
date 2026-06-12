param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RequiredDocs = @(
    "AGENTS.md",
    "docs\PROJECT_SUMMARY.md",
    "docs\ARCHITECTURE.md",
    "docs\ROADMAP.md",
    "docs\ANA_MEMORY.md"
)

$MissingDocs = @()
foreach ($Doc in $RequiredDocs) {
    $Path = Join-Path $ProjectRoot $Doc
    if (-not (Test-Path -LiteralPath $Path)) {
        $MissingDocs += $Doc
    }
}

$BridgeOutput = ""
$BridgeOk = $false
$BridgeError = ""
try {
    $BridgeOutput = & python (Join-Path $ProjectRoot "cascade_integration\direct_bridge.py") --health-check
    $BridgeData = $BridgeOutput | ConvertFrom-Json
    $BridgeOk = [bool]$BridgeData.success -and $BridgeData.mode -eq "direct" -and -not [bool]$BridgeData.mcp_enabled
}
catch {
    $BridgeError = $_.Exception.Message
}

$Result = [ordered]@{
    success = ($MissingDocs.Count -eq 0 -and $BridgeOk)
    project_root = [string]$ProjectRoot
    missing_docs = $MissingDocs
    direct_bridge_ok = $BridgeOk
    bridge_error = $BridgeError
    next_action = ""
}

if (-not $Result.success) {
    if ($MissingDocs.Count -gt 0) {
        $Result.next_action = "Create or repair missing startup docs before project work."
    }
    elseif (-not $BridgeOk) {
        $Result.next_action = "Run direct bridge health check manually and repair local runtime readiness."
    }
}
else {
    $Result.next_action = "Startup ready. Continue with observe -> act -> verify."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 4
}
else {
    if ($Result.success) {
        Write-Host "PASS agent startup check"
    }
    else {
        Write-Host "FAIL agent startup check"
    }
    Write-Host "Project: $($Result.project_root)"
    Write-Host "Missing docs: $($MissingDocs.Count)"
    Write-Host "Direct bridge ok: $BridgeOk"
    if ($BridgeError) {
        Write-Host "Bridge error: $BridgeError"
    }
    Write-Host "Next: $($Result.next_action)"
}

if (-not $Result.success) {
    exit 1
}
