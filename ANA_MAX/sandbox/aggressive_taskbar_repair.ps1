# AGGRESSIVE TASKBAR REPAIR - Post Printer Malware
Write-Host "=== AGGRESSIVE TASKBAR REPAIR ===" -ForegroundColor Red
Write-Host ""

# 1. KILL ALL EXPLORER PROCESSES
Write-Host "[1] Killing all explorer processes..." -ForegroundColor Yellow
try {
    Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 5
    Write-Host "All explorer processes killed" -ForegroundColor Green
} catch {
    Write-Host "Error killing explorer: $_" -ForegroundColor Red
}

# 2. SCAN FOR MALICIOUS SOFTWARE
Write-Host "[2] Scanning for printer-related software..." -ForegroundColor Yellow
$printerSoftware = Get-WmiObject -Class Win32_Product | Where-Object {
    $_.Name -like "*HP*" -or
    $_.Name -like "*Epson*" -or
    $_.Name -like "*Canon*" -or
    $_.Name -like "*Brother*" -or
    $_.Name -like "*Lexmark*" -or
    $_.Name -like "*Video*" -or
    $_.Name -like "*Print*"
} | Select-Object Name, Version

if ($printerSoftware) {
    Write-Host "PRINTER SOFTWARE FOUND:" -ForegroundColor Red
    $printerSoftware | Format-Table
    Write-Host "THIS SOFTWARE MAY BE BLOCKING TASKBAR" -ForegroundColor Red
    Write-Host "Recommend uninstallation if not needed" -ForegroundColor Yellow
} else {
    Write-Host "No printer software found" -ForegroundColor Green
}

# 3. CHECK SUSPICIOUS PROCESSES
Write-Host "[3] Checking for suspicious processes..." -ForegroundColor Yellow
$suspicious = Get-Process | Where-Object {
    $_.MainWindowTitle -like "*HP*" -or
    $_.MainWindowTitle -like "*Epson*" -or
    $_.MainWindowTitle -like "*Canon*" -or
    $_.ProcessName -like "*printer*" -or
    $_.ProcessName -like "*video*" -or
    $_.ProcessName -like "*overlay*"
}

if ($suspicious) {
    Write-Host "SUSPICIOUS PROCESSES FOUND:" -ForegroundColor Red
    $suspicious | Select-Object ProcessName, Id, MainWindowTitle | Format-Table
    Write-Host "KILLING SUSPICIOUS PROCESSES..." -ForegroundColor Red
    $suspicious | Stop-Process -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "No suspicious processes found" -ForegroundColor Green
}

# 4. RESET ALL TASKBAR REGISTRY KEYS
Write-Host "[4] Resetting all taskbar registry keys..." -ForegroundColor Yellow
try {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    $keys = @("TaskbarGlomLevel", "MMTaskbarEnabled", "TaskbarDa", "TaskbarMn", "TaskbarSizeMove", "TaskbarSmallIcons")

    foreach ($key in $keys) {
        Remove-ItemProperty -Path $regPath -Name $key -Force -ErrorAction SilentlyContinue
    }

    Set-ItemProperty -Path $regPath -Name "TaskbarGlomLevel" -Value 0 -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $regPath -Name "MMTaskbarEnabled" -Value 1 -Force -ErrorAction SilentlyContinue

    Write-Host "Registry keys reset" -ForegroundColor Green
} catch {
    Write-Host "Registry reset error: $_" -ForegroundColor Red
}

# 5. DELETE TASKBAR CACHE
Write-Host "[5] Deleting taskbar cache..." -ForegroundColor Yellow
try {
    $cachePaths = @(
        "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\IconCache*",
        "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\ThumbCache*",
        "$env:APPDATA\Microsoft\Windows\Recent\*"
    )

    foreach ($path in $cachePaths) {
        if (Test-Path $path) {
            Remove-Item $path -Force -Recurse -ErrorAction SilentlyContinue
        }
    }

    Write-Host "Taskbar cache deleted" -ForegroundColor Green
} catch {
    Write-Host "Cache deletion error: $_" -ForegroundColor Red
}

# 6. RESTART EXPLORER
Write-Host "[6] Restarting explorer..." -ForegroundColor Yellow
try {
    Start-Process explorer.exe
    Start-Sleep -Seconds 3
    Write-Host "Explorer restarted" -ForegroundColor Green
} catch {
    Write-Host "Explorer restart error: $_" -ForegroundColor Red
}

# 7. CHECK WINDOWS INTEGRITY
Write-Host "[7] Checking Windows integrity..." -ForegroundColor Yellow
try {
    sfc /scannow
    Write-Host "Windows integrity check completed" -ForegroundColor Green
} catch {
    Write-Host "SFC scan error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== AGGRESSIVE REPAIR COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Test taskbar immediately"
Write-Host "2. If still blocked, RESTART COMPUTER"
Write-Host "3. After restart, check if printer software is needed"
Write-Host "4. If printer software is causing issues, UNINSTALL IT"
Write-Host ""
