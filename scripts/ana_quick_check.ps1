param(
    [int]$Iterations = 3,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Bridge = Join-Path $ProjectRoot "cascade_integration\direct_bridge.py"

function Invoke-JsonCommand {
    param(
        [string[]]$Command
    )

    $Output = & $Command[0] $Command[1..($Command.Count - 1)]
    return $Output | ConvertFrom-Json
}

$Startup = Invoke-JsonCommand @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "agent_startup_check.ps1"), "-Json")
$Smoke = Invoke-JsonCommand @("python", $Bridge, "--smoke-test")
$Benchmark = Invoke-JsonCommand @("python", $Bridge, "--benchmark", "--iterations", [string]$Iterations)
$Security = Invoke-JsonCommand @("python", $Bridge, "--security-diagnostics")

$Result = [ordered]@{
    success = ([bool]$Startup.success -and [bool]$Smoke.success -and [bool]$Benchmark.success -and [bool]$Security.success)
    project_root = [string]$ProjectRoot
    iterations = $Iterations
    startup = $Startup
    smoke = @{
        passed = $Smoke.passed
        failed = $Smoke.failed
    }
    benchmark = $Benchmark.direct
    security = @{
        success = $Security.success
        findings = $Security.findings
    }
    next_action = ""
}

if ($Result.success) {
    $Result.next_action = "Quick check PASS. Continue with scoped work."
}
else {
    $Result.next_action = "Inspect failed section before mutating project state."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
}
else {
    if ($Result.success) {
        Write-Host "PASS ANA quick check"
    }
    else {
        Write-Host "FAIL ANA quick check"
    }
    Write-Host "Startup: $($Startup.success)"
    Write-Host "Smoke: $($Smoke.passed) passed / $($Smoke.failed) failed"
    Write-Host "Security: $($Security.success)"
    Write-Host "Benchmark iterations: $Iterations"
    Write-Host "Next: $($Result.next_action)"
}

if (-not $Result.success) {
    exit 1
}
