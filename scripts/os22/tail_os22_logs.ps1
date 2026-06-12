param(
    [string]$Root = ""
)

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

Set-Location -LiteralPath $Root

$host.UI.RawUI.BackgroundColor = "Black"
$host.UI.RawUI.ForegroundColor = "Green"
$host.UI.RawUI.WindowTitle = "ANA MAX OS22 LIVE LOG"
Clear-Host

Write-Host "[ANA OS22 LIVE LOG]" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Watching chat, tool telemetry, and self-healing telemetry."
Write-Host "Press Ctrl+C to stop tailing."
Write-Host ""

New-Item -ItemType Directory -Force "ANA_MAX\logs" | Out-Null
New-Item -ItemType Directory -Force "ANA_MAX\local" | Out-Null

$paths = @(
    "ANA_MAX\logs\os22_chat.log",
    "ANA_MAX\local\tool_telemetry.log",
    "ANA_MAX\logs\self_healing_telemetry.jsonl"
)

foreach ($path in $paths) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType File -Force -Path $path | Out-Null
    }
}

Get-Content -LiteralPath $paths -Wait -Tail 80
