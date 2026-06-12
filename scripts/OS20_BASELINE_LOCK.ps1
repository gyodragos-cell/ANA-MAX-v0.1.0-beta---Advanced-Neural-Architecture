param(
    [switch]$Json,
    [switch]$RunRuntimeChecks
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Checks = @()

function Add-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail = ""
    )

    $script:Checks += [ordered]@{
        name = $Name
        passed = $Passed
        detail = $Detail
    }
}

function Read-JsonFile {
    param(
        [string]$RelativePath
    )

    $Path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-FileContains {
    param(
        [string]$RelativePath,
        [string]$Pattern
    )

    $Path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    $Text = Get-Content -LiteralPath $Path -Raw
    return $Text.Contains($Pattern)
}

$RequiredFiles = @(
    "docs\OS20_FINAL_BASELINE.md",
    "ANA_MAX\memory\full_auto_audit_v2_report.json",
    "ANA_MAX\memory\personal_ai_studio_report.json",
    "ANA_MAX\context\context_bundle.json",
    "ANA_MAX\context\agent_bootstrap_prompt.txt",
    "ANA_MAX\skills\skill_engine.py",
    "ANA_MAX\skills\__init__.py",
    "ANA_MAX\self_optimization\fallback_engine.py",
    "ANA_MAX\self_optimization\error_model.py",
    "ANA_MAX\self_optimization\self_healing_engine.py"
)

foreach ($File in $RequiredFiles) {
    Add-Check "file_exists:$File" (Test-Path -LiteralPath (Join-Path $ProjectRoot $File)) $File
}

$Audit = Read-JsonFile "ANA_MAX\memory\full_auto_audit_v2_report.json"
$Studio = Read-JsonFile "ANA_MAX\memory\personal_ai_studio_report.json"
$Bundle = Read-JsonFile "ANA_MAX\context\context_bundle.json"

Add-Check "audit_schema" ($null -ne $Audit -and $Audit.schema -eq "ana.full_auto_audit.v2") "schema=$($Audit.schema)"
Add-Check "audit_pass" ($null -ne $Audit -and $Audit.status -eq "PASS") "status=$($Audit.status)"
Add-Check "audit_health_100" ($null -ne $Audit -and [int]$Audit.health_score -eq 100) "health_score=$($Audit.health_score)"
Add-Check "audit_warnings_zero" ($null -ne $Audit -and [int]$Audit.warnings -eq 0) "warnings=$($Audit.warnings)"
Add-Check "audit_parse_errors_zero" ($null -ne $Audit -and [int]$Audit.parse_error_count -eq 0) "parse_error_count=$($Audit.parse_error_count)"
Add-Check "audit_no_drift" ($null -ne $Audit -and [bool]$Audit.drift_detected -eq $false) "drift_detected=$($Audit.drift_detected)"
Add-Check "audit_overall_success" ($null -ne $Audit -and [bool]$Audit.overall_success) "overall_success=$($Audit.overall_success)"

Add-Check "studio_health_100" ($null -ne $Studio -and [int]$Studio.summary.health_score -eq 100) "health_score=$($Studio.summary.health_score)"
Add-Check "studio_warnings_zero" ($null -ne $Studio -and [int]$Studio.summary.warnings -eq 0) "warnings=$($Studio.summary.warnings)"
Add-Check "studio_parse_errors_zero" ($null -ne $Studio -and [int]$Studio.summary.parse_error_count -eq 0) "parse_error_count=$($Studio.summary.parse_error_count)"
Add-Check "studio_overall_success" ($null -ne $Studio -and [bool]$Studio.summary.overall_success) "overall_success=$($Studio.summary.overall_success)"

Add-Check "context_current_os20" ($null -ne $Bundle -and $Bundle.summary.current_os_level -eq "OS-20") "current_os_level=$($Bundle.summary.current_os_level)"
Add-Check "context_reports_20" ($null -ne $Bundle -and [int]$Bundle.summary.os_report_count -ge 20) "os_report_count=$($Bundle.summary.os_report_count)"
Add-Check "context_health_100" ($null -ne $Bundle -and [int]$Bundle.summary.health_score -eq 100) "health_score=$($Bundle.summary.health_score)"
Add-Check "context_overall_success" ($null -ne $Bundle -and [bool]$Bundle.summary.overall_success) "overall_success=$($Bundle.summary.overall_success)"
Add-Check "context_no_warning_cycles" ($null -ne $Bundle -and [int]$Bundle.summary.warning_cycles -eq 0) "warning_cycles=$($Bundle.summary.warning_cycles)"
Add-Check "context_no_parse_error_cycles" ($null -ne $Bundle -and [int]$Bundle.summary.parse_error_cycles -eq 0) "parse_error_cycles=$($Bundle.summary.parse_error_cycles)"

Add-Check "bootstrap_mentions_os20" (Test-FileContains "ANA_MAX\context\agent_bootstrap_prompt.txt" "current_os_level: OS-20") "agent_bootstrap_prompt.txt"
Add-Check "baseline_mentions_audit_v2" (Test-FileContains "docs\OS20_FINAL_BASELINE.md" "ana.full_auto_audit.v2") "docs\OS20_FINAL_BASELINE.md"
Add-Check "healing_has_diagnostic" (Test-FileContains "ANA_MAX\self_optimization\self_healing_engine.py" "--diagnostic") "self_healing_engine.py"
Add-Check "healing_has_simulate_repair" (Test-FileContains "ANA_MAX\self_optimization\self_healing_engine.py" "--simulate-repair") "self_healing_engine.py"

if ($RunRuntimeChecks) {
    $CompileOutput = & python "-m" "compileall" "-q" (Join-Path $ProjectRoot "ANA_MAX") 2>&1
    Add-Check "runtime_compileall" ($LASTEXITCODE -eq 0) (($CompileOutput | Out-String).Trim())

    try {
        $BridgeOutput = & python (Join-Path $ProjectRoot "cascade_integration\direct_bridge.py") --health-check 2>&1
        $BridgeData = $BridgeOutput | ConvertFrom-Json
        $BridgeOk = [bool]$BridgeData.success -and [int]$BridgeData.loaded_tools -eq 14 -and [int]$BridgeData.registered_tools -eq 14 -and -not [bool]$BridgeData.mcp_enabled
        Add-Check "runtime_direct_bridge_14_of_14" $BridgeOk "loaded=$($BridgeData.loaded_tools) registered=$($BridgeData.registered_tools) mcp_enabled=$($BridgeData.mcp_enabled)"
    }
    catch {
        Add-Check "runtime_direct_bridge_14_of_14" $false $_.Exception.Message
    }
}

$FailedChecks = @($Checks | Where-Object { -not $_.passed })
$Result = [ordered]@{
    schema = "ana.os20.baseline_lock.v1"
    success = ($FailedChecks.Count -eq 0)
    project_root = [string]$ProjectRoot
    run_runtime_checks = [bool]$RunRuntimeChecks
    summary = [ordered]@{
        total = $Checks.Count
        passed = ($Checks.Count - $FailedChecks.Count)
        failed = $FailedChecks.Count
    }
    checks = $Checks
    next_action = ""
}

if ($Result.success) {
    $Result.next_action = "OS-20 baseline locked. Safe to begin scoped OS-21 planning or refactor prep."
}
else {
    $Result.next_action = "Resolve failed baseline checks before OS-21 planning or refactor work."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
}
else {
    if ($Result.success) {
        Write-Host "PASS OS-20 baseline lock"
    }
    else {
        Write-Host "FAIL OS-20 baseline lock"
    }
    Write-Host "Project: $($Result.project_root)"
    Write-Host "Checks: $($Result.summary.passed) passed / $($Result.summary.failed) failed / $($Result.summary.total) total"
    Write-Host "Runtime checks: $RunRuntimeChecks"
    if ($FailedChecks.Count -gt 0) {
        Write-Host "Failed checks:"
        foreach ($Check in $FailedChecks) {
            Write-Host "- $($Check.name): $($Check.detail)"
        }
    }
    Write-Host "Next: $($Result.next_action)"
}

if (-not $Result.success) {
    exit 1
}
