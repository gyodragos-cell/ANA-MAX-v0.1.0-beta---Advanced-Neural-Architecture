param(
    [string]$LogFile = "C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log",
    [int]$Tail = 50,
    [switch]$IncludeFoundry
)

Write-Host "=== ANA MAX LIVE LOG MONITOR (Manus Edition) ===" -ForegroundColor Cyan
Write-Host "Monitoring: $LogFile" -ForegroundColor Gray

if ($IncludeFoundry) {
    Write-Host "Including Foundry logs..." -ForegroundColor Cyan
    # Try to find Foundry logs
    $foundryPaths = @(
        "$env:LOCALAPPDATA\Packages\Microsoft.FoundryLocal_*\LocalState\*.log",
        "$env:LOCALAPPDATA\Microsoft\FoundryLocal\*.log"
    )
    $foundryLog = $null
    foreach ($path in $foundryPaths) {
        $files = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
        if ($files) {
            $foundryLog = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            Write-Host "Foundry Log: $($foundryLog.FullName)" -ForegroundColor Green
            break
        }
    }
}

if (-not (Test-Path $LogFile)) {
    Write-Host "[WARN] Log file not found yet. Waiting..." -ForegroundColor Yellow
    while (-not (Test-Path $LogFile)) { Start-Sleep -Seconds 2 }
}

Get-Content -Path $LogFile -Tail $Tail -Wait | ForEach-Object {
    $line = $_
    if ($line -match "OS27-DEBUG" -or $line -match "OS27-ALERT") {
        Write-Host $line -ForegroundColor Red
    } elseif ($line -match "OLLAMA-LOG" -or $line -match "qwen" -or $line -match "ollama") {
        Write-Host $line -ForegroundColor Cyan
    } elseif ($line -match "ERROR" -or $line -match "EROARE" -or $line -match "FAIL") {
        Write-Host $line -ForegroundColor Red
    } elseif ($line -match "WARNING" -or $line -match "WARN") {
        Write-Host $line -ForegroundColor Yellow
    } elseif ($line -match "SUCCESS" -or $line -match "OK" -or $line -match "INFO") {
        Write-Host $line -ForegroundColor Green
    } elseif ($line -match "ACTION" -or $line -match "DECISION" -or $line -match "THOUGHT") {
        Write-Host $line -ForegroundColor Magenta
    } else {
        Write-Host $line -ForegroundColor White
    }
}
