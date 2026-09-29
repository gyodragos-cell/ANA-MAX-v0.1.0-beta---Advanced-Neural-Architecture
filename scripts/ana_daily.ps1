param(
    [int]$Iterations = 1,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PerformanceLog = Join-Path $ProjectRoot "docs\PERFORMANCE_LOG.md"

function Invoke-JsonCommand {
    param([string[]]$Command)
    $Output = & $Command[0] $Command[1..($Command.Count - 1)]
    return $Output | ConvertFrom-Json
}

$Quick = Invoke-JsonCommand @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "ana_quick_check.ps1"), "-Iterations", [string]$Iterations, "-Json")
$Maintenance = Invoke-JsonCommand @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "ana_maintenance.ps1"), "-Json")

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$LogItem = $Maintenance.items | Where-Object { $_.name -eq "ANA logs" } | Select-Object -First 1
$PyCacheItem = $Maintenance.items | Where-Object { $_.type -eq "pycache" } | Select-Object -First 1

$Result = [ordered]@{
    success = ([bool]$Quick.success -and [bool]$Maintenance.success)
    timestamp = $Timestamp
    project_root = [string]$ProjectRoot
    quick = @{
        smoke_passed = $Quick.smoke.passed
        smoke_failed = $Quick.smoke.failed
        agent_coach_avg_ms = $Quick.benchmark.agent_coach.avg_ms
        tool_router_avg_ms = $Quick.benchmark.tool_router.avg_ms
        file_operations_avg_ms = $Quick.benchmark.file_operations.avg_ms
    }
    maintenance = @{
        disk_free_gb = $Maintenance.disk.free_gb
        memory_free_gb = $Maintenance.memory.free_gb
        ana_logs_mb = $LogItem.size_mb
        pycache_mb = $PyCacheItem.size_mb
        archive_candidates = $Maintenance.log_archive.candidates
        large_log_candidates = $Maintenance.log_archive.large_candidates
    }
    next_action = ""
}

if ($Result.success) {
    $Result.next_action = "Daily check PASS. Continue normal lab work."
}
else {
    $Result.next_action = "Daily check failed. Inspect quick or maintenance output before changes."
}

$Entry = @"

## $Timestamp

- Daily check: $($Result.success)
- Smoke: $($Result.quick.smoke_passed) passed / $($Result.quick.smoke_failed) failed
- Benchmark avg ms: agent_coach $($Result.quick.agent_coach_avg_ms), tool_router $($Result.quick.tool_router_avg_ms), file_operations $($Result.quick.file_operations_avg_ms)
- Resources: disk_free_gb $($Result.maintenance.disk_free_gb), memory_free_gb $($Result.maintenance.memory_free_gb)
- Maintenance: ana_logs_mb $($Result.maintenance.ana_logs_mb), pycache_mb $($Result.maintenance.pycache_mb), archive_candidates $($Result.maintenance.archive_candidates), large_log_candidates $($Result.maintenance.large_log_candidates)
- Next: $($Result.next_action)
"@

Add-Content -LiteralPath $PerformanceLog -Value $Entry -Encoding UTF8

if ($Json) {
    $Result | ConvertTo-Json -Depth 6
}
else {
    if ($Result.success) {
        Write-Host "PASS ANA daily check"
    }
    else {
        Write-Host "FAIL ANA daily check"
    }
    Write-Host "Smoke: $($Result.quick.smoke_passed) passed / $($Result.quick.smoke_failed) failed"
    Write-Host "Logs: $($Result.maintenance.ana_logs_mb) MB"
    Write-Host "Performance log: $PerformanceLog"
    Write-Host "Next: $($Result.next_action)"
}

if (-not $Result.success) {
    exit 1
}
