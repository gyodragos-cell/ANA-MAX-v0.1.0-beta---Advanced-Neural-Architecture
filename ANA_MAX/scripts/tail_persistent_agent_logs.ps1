# ANA MAX Persistent Agent Live Log Viewer
# Real-time monitoring of persistent agent operations

param(
    [string]$LogFile = "C:\ANA_MAX\logs\persistent_agent_live.log",
    [int]$Lines = 50
)

$ErrorActionPreference = "Stop"

Write-Host "=== ANA MAX Persistent Agent Live Log Viewer ===" -ForegroundColor Cyan
Write-Host "Monitoring: $LogFile" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $LogFile)) {
    Write-Host "Log file not found: $LogFile" -ForegroundColor Red
    Write-Host "Waiting for log file to be created..." -ForegroundColor Yellow
    
    while (-not (Test-Path $LogFile)) {
        Start-Sleep -Seconds 1
    }
    
    Write-Host "Log file detected. Starting monitoring..." -ForegroundColor Green
    Write-Host ""
}

# Get initial content
Get-Content $LogFile -Tail $Lines | ForEach-Object {
    $color = switch -Regex ($_ {
        '\[ERROR\]' { 'Red' }
        '\[WARN\]' { 'Yellow' }
        '\[SUCCESS\]' { 'Green' }
        '\[INFO\]' { 'Cyan' }
        default { 'White' }
    }
    Write-Host $_ -ForegroundColor $color
}

# Monitor for new content
$reader = [System.IO.StreamReader]::new($LogFile)
$reader.BaseStream.Seek(0, [System.IO.SeekOrigin]::End) | Out-Null

try {
    while ($true) {
        $line = $reader.ReadLine()
        if ($line) {
            $color = switch -Regex ($line) {
                '\[ERROR\]' { 'Red' }
                '\[WARN\]' { 'Yellow' }
                '\[SUCCESS\]' { 'Green' }
                '\[INFO\]' { 'Cyan' }
                default { 'White' }
            }
            Write-Host $line -ForegroundColor $color
        } else {
            Start-Sleep -Milliseconds 100
        }
    }
}
finally {
    $reader.Close()
}
