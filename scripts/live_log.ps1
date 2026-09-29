$host.UI.RawUI.BackgroundColor='Black'
$host.UI.RawUI.WindowTitle='ANA LIVE LOG (Enterprise)'
Clear-Host
Write-Host '[ANA LIVE LOG] Ctrl+C pentru a opri' -ForegroundColor Cyan
Write-Host '=========================================' -ForegroundColor DarkGray

$LogPath = "$PSScriptRoot\..\ANA_MAX\logs\ana_max.log"
if (-not (Test-Path $LogPath)) {
    New-Item -Path $LogPath -ItemType File -Force | Out-Null
}

Get-Content $LogPath -Wait -Tail 80 | ForEach-Object {
    if ($_ -match 'ERROR|FAILED|FAILURE') {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match 'WARNING|WARN|CANCELLED') {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match 'FOUNDRY_READY|FOUNDRY_INIT|FOUNDRY_CHAT') {
        Write-Host $_ -ForegroundColor Cyan
    } elseif ($_ -match 'FOUNDRY_TOOL|TOOL START|TOOL END') {
        Write-Host $_ -ForegroundColor Magenta
    } elseif ($_ -match 'SEMANTIC-ACTION') {
        Write-Host $_ -ForegroundColor Blue
    } elseif ($_ -match 'INFO') {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match 'DEBUG') {
        Write-Host $_ -ForegroundColor DarkGray
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}
