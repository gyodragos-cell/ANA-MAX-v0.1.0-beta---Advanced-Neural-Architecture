# Comprehensive System Repair - Post Printer Installation
Write-Host "=== COMPREHENSIVE SYSTEM REPAIR ===" -ForegroundColor Cyan
Write-Host ""

# 1. Taskbar Repair
Write-Host "[1] Taskbar Repair..." -ForegroundColor Yellow
try {
    # Reset taskbar settings
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarGlomLevel" -Value 0 -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "MMTaskbarEnabled" -Value 1 -Force -ErrorAction SilentlyContinue

    # Clear taskbar cache
    $taskbarCache = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\IconCache*"
    if (Test-Path $taskbarCache) {
        Remove-Item $taskbarCache -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Taskbar settings reset" -ForegroundColor Green
} catch {
    Write-Host "Taskbar repair error: $_" -ForegroundColor Red
}

# 2. Explorer Restart
Write-Host "[2] Explorer Restart..." -ForegroundColor Yellow
try {
    Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Process explorer.exe
    Write-Host "Explorer restarted" -ForegroundColor Green
} catch {
    Write-Host "Explorer restart error: $_" -ForegroundColor Red
}

# 3. Keyboard Shortcuts Reset
Write-Host "[3] Keyboard Shortcuts Reset..." -ForegroundColor Yellow
try {
    # Reset keyboard shortcuts in registry
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarDa" -Value 0 -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarMn" -Value 0 -Force -ErrorAction SilentlyContinue
    Write-Host "Keyboard shortcuts reset" -ForegroundColor Green
} catch {
    Write-Host "Keyboard shortcuts reset error: $_" -ForegroundColor Red
}

# 4. Windows Update Repair
Write-Host "[4] Windows Update Repair..." -ForegroundColor Yellow
try {
    $updatePath = "$env:SYSTEMROOT\SoftwareDistribution"
    if (Test-Path $updatePath) {
        # Stop services
        Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
        Stop-Service -Name bits -Force -ErrorAction SilentlyContinue
        Stop-Service -Name cryptSvc -Force -ErrorAction SilentlyContinue

        Start-Sleep -Seconds 2

        # Rename folder
        Rename-Item -Path $updatePath -NewName "SoftwareDistribution.old" -Force -ErrorAction SilentlyContinue

        # Start services
        Start-Service -Name wuauserv -ErrorAction SilentlyContinue
        Start-Service -Name bits -ErrorAction SilentlyContinue
        Start-Service -Name cryptSvc -ErrorAction SilentlyContinue

        Write-Host "Windows Update repaired" -ForegroundColor Green
    }
} catch {
    Write-Host "Windows Update repair error: $_" -ForegroundColor Red
}

# 5. Check for Malicious/Bloatware Processes
Write-Host "[5] Checking for Bloatware..." -ForegroundColor Yellow
$suspiciousPatterns = @("*HP*", "*Epson*", "*Canon*", "*Brother*", "*Lexmark*", "*Video*", "*Print*")
$suspiciousProcesses = Get-Process | Where-Object {
    $p = $_.ProcessName
    $suspiciousPatterns | Where-Object { $p -like $_ }
}

if ($suspiciousProcesses) {
    Write-Host "Suspicious processes found:" -ForegroundColor Red
    $suspiciousProcesses | Select-Object ProcessName, Id | Format-Table
    Write-Host "Review these processes manually" -ForegroundColor Yellow
} else {
    Write-Host "No suspicious processes found" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== REPAIR COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. Test taskbar - try left and right click"
Write-Host "2. Test Start button - try clicking it"
Write-Host "3. Test Ctrl+Tab in browser"
Write-Host "4. Try Windows Update manually"
Write-Host "5. If issues persist, restart computer"
Write-Host ""
