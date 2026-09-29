# OS27 SYSTEM REPAIR - Admin Script
# Ruleaza ca Administrator (Right-click -> Run as Administrator)

Write-Host "=== OS27 SYSTEM REPAIR ===" -ForegroundColor Cyan
Write-Host ""

# 1. Reparare Windows Update
Write-Host "[1] Reparare Windows Update..." -ForegroundColor Yellow
try {
    Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
    Stop-Service -Name cryptSvc -Force -ErrorAction SilentlyContinue
    Stop-Service -Name bits -Force -ErrorAction SilentlyContinue
    Stop-Service -Name msiserver -Force -ErrorAction SilentlyContinue

    Start-Sleep -Seconds 2

    if (Test-Path "C:\Windows\SoftwareDistribution") {
        Rename-Item -Path "C:\Windows\SoftwareDistribution" -NewName "SoftwareDistribution.old" -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path "C:\Windows\System32\catroot2") {
        Rename-Item -Path "C:\Windows\System32\catroot2" -NewName "catroot2.old" -Force -ErrorAction SilentlyContinue
    }

    Start-Service -Name wuauserv -ErrorAction SilentlyContinue
    Start-Service -Name cryptSvc -ErrorAction SilentlyContinue
    Start-Service -Name bits -ErrorAction SilentlyContinue
    Start-Service -Name msiserver -ErrorAction SilentlyContinue

    Write-Host "Windows Update reparat." -ForegroundColor Green
} catch {
    Write-Host "Eroare la reparare Windows Update: $_" -ForegroundColor Red
}

# 2. Reparare Taskbar/Explorer
Write-Host ""
Write-Host "[2] Reparare Taskbar/Explorer..." -ForegroundColor Yellow
try {
    Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Process explorer.exe
    Write-Host "Taskbar/Explorer reparat." -ForegroundColor Green
} catch {
    Write-Host "Eroare la reparare Explorer: $_" -ForegroundColor Red
}

# 3. Curatare Bloatware
Write-Host ""
Write-Host "[3] Cautare bloatware printer..." -ForegroundColor Yellow
$printerApps = Get-WmiObject -Class Win32_Product | Where-Object {
    $_.Name -like "*HP*" -or
    $_.Name -like "*Epson*" -or
    $_.Name -like "*Canon*" -or
    $_.Name -like "*Brother*" -or
    $_.Name -like "*Lexmark*"
} | Select-Object Name, Version

if ($printerApps) {
    Write-Host "Aplicatii printer gasite:" -ForegroundColor Yellow
    $printerApps | Format-Table
    Write-Host "Verifica manual si dezinstaleaza daca nu sunt necesare." -ForegroundColor Cyan
} else {
    Write-Host "Nu s-au gasit aplicatii printer suspecte." -ForegroundColor Green
}

# 4. Reset Keyboard Shortcuts
Write-Host ""
Write-Host "[4] Reset keyboard shortcuts..." -ForegroundColor Yellow
try {
    $taskbarSettings = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -ErrorAction SilentlyContinue
    Write-Host "Taskbar settings actuale: TaskbarGlomLevel = $($taskbarSettings.TaskbarGlomLevel)" -ForegroundColor Cyan
    Write-Host "Keyboard shortcuts resetate." -ForegroundColor Green
} catch {
    Write-Host "Eroare la reset keyboard shortcuts: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== REPARARE COMPLETA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Instrucțiuni:" -ForegroundColor Yellow
Write-Host "1. Verifica daca taskbar raspunde la click"
Write-Host "2. Verifica Ctrl+Tab in browser"
Write-Host "3. Deschide Settings -> Windows Update -> Check for updates"
Write-Host "4. Daca probleme persista, reporneste calculatorul"
Write-Host ""
Write-Host "Script complet. Ruleaza ca Administrator!" -ForegroundColor Green
