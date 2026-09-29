# EMERGENCY SYSTEM RESET - Malware/Bad Driver Detection
Write-Host "=== EMERGENCY SYSTEM RESET ===" -ForegroundColor Red
Write-Host ""

# 1. CHECK ALL RUNNING PROCESSES
Write-Host "[1] Checking all running processes..." -ForegroundColor Yellow
$allProcesses = Get-Process | Select-Object ProcessName, Id, CPU, WorkingSet
Write-Host "Total processes: $($allProcesses.Count)" -ForegroundColor Cyan

# 2. CHECK HIGH CPU PROCESSES
Write-Host "[2] Checking high CPU processes..." -ForegroundColor Yellow
$highCPU = Get-Process | Where-Object { $_.CPU -gt 10 } | Select-Object ProcessName, Id, CPU
if ($highCPU) {
    Write-Host "High CPU processes found:" -ForegroundColor Red
    $highCPU | Format-Table
} else {
    Write-Host "No high CPU processes" -ForegroundColor Green
}

# 3. FORCE RESTART EXPLORER WITH CLEANUP
Write-Host "[3] Force restart explorer with cleanup..." -ForegroundColor Yellow
try {
    # Kill ALL explorer instances
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force

    # Clear ALL caches
    $caches = @(
        "$env:LOCALAPPDATA\Microsoft\Windows\Explorer",
        "$env:APPDATA\Microsoft\Windows\Recent",
        "$env:TEMP\*"
    )

    foreach ($cache in $caches) {
        if (Test-Path $cache) {
            Remove-Item $cache -Force -Recurse -ErrorAction SilentlyContinue
        }
    }

    Start-Sleep -Seconds 5

    # Start fresh explorer
    Start-Process explorer.exe

    Write-Host "Explorer force restarted" -ForegroundColor Green
} catch {
    Write-Host "Explorer restart error: $_" -ForegroundColor Red
}

# 4. CHECK FOR MALWARE PATTERNS
Write-Host "[4] Checking for malware patterns..." -ForegroundColor Yellow
$malwarePatterns = @(
    "*malware*",
    "*virus*",
    "*trojan*",
    "*backdoor*",
    "*keylogger*",
    "*inject*",
    "*hook*"
)

$maliciousProcesses = Get-Process | Where-Object {
    $p = $_.ProcessName
    $malwarePatterns | Where-Object { $p -like $_ }
}

if ($maliciousProcesses) {
    Write-Host "POTENTIAL MALWARE FOUND:" -ForegroundColor Red
    $maliciousProcesses | Select-Object ProcessName, Id | Format-Table
    Write-Host "IMMEDIATE ACTION REQUIRED" -ForegroundColor Red
} else {
    Write-Host "No obvious malware patterns" -ForegroundColor Green
}

# 5. SYSTEM INTEGRITY CHECK
Write-Host "[5] System integrity check..." -ForegroundColor Yellow
try {
    dism /Online /Cleanup-Image /CheckHealth
    Write-Host "System integrity check completed" -ForegroundColor Green
} catch {
    Write-Host "DISM check error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== EMERGENCY RESET COMPLETE ===" -ForegroundColor Red
Write-Host ""
Write-Host "CRITICAL RECOMMENDATION:" -ForegroundColor Yellow
Write-Host "1. RESTART COMPUTER NOW - this is required"
Write-Host "2. After restart, run Windows Update"
Write-Host "3. Update NVIDIA drivers to latest version"
Write-Host "4. Check installed programs for anything printer-related"
Write-Host "5. If problems persist, run full system scan with Windows Defender"
Write-Host ""
Write-Host "If after restart taskbar still doesn't work:" -ForegroundColor Red
Write-Host "- Boot into Safe Mode" -ForegroundColor Yellow
Write-Host "- Uninstall recent printer software" -ForegroundColor Yellow
Write-Host "- Perform System Restore to before printer installation" -ForegroundColor Yellow
Write-Host ""
