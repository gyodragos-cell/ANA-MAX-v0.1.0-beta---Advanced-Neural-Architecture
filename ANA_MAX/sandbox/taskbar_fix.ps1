# Taskbar Fix Script
Write-Host "Diagnosing taskbar..." -ForegroundColor Cyan

# Check taskbar settings
$taskbarSettings = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -ErrorAction SilentlyContinue
Write-Host "TaskbarGlomLevel: $($taskbarSettings.TaskbarGlomLevel)" -ForegroundColor Yellow

# Check for suspicious processes
$suspicious = Get-Process | Where-Object {
    $_.ProcessName -like "*video*" -or
    $_.ProcessName -like "*print*" -or
    $_.ProcessName -like "*hp*" -or
    $_.ProcessName -like "*epson*"
}

if ($suspicious) {
    Write-Host "Suspicious processes found:" -ForegroundColor Red
    $suspicious | Select-Object ProcessName, Id
} else {
    Write-Host "No suspicious processes found" -ForegroundColor Green
}

# Force restart explorer
Write-Host "Restarting explorer..." -ForegroundColor Yellow
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process explorer.exe

Write-Host "Done. Check if taskbar works now." -ForegroundColor Green
