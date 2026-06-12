param(
    [string]$ArchiveStamp = "20260610T043542Z",
    [switch]$Apply,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ArchiveTools = Join-Path $Root "ANA_MAX\archives\duplicates\$ArchiveStamp\tools"
$DestTools = Join-Path $Root "ANA_MAX\tools"

$Restored = @()
$Skipped = @()
$Errors = @()

if (-not (Test-Path -LiteralPath $ArchiveTools)) {
    throw "Archive tools directory not found: $ArchiveTools"
}

New-Item -ItemType Directory -Force -Path $DestTools | Out-Null

foreach ($Source in Get-ChildItem -LiteralPath $ArchiveTools -Filter "*.py" -File) {
    $Destination = Join-Path $DestTools $Source.Name
    if (Test-Path -LiteralPath $Destination) {
        $Skipped += $Source.Name
        continue
    }

    if ($Apply) {
        try {
            Copy-Item -LiteralPath $Source.FullName -Destination $Destination -Force:$false
            $Restored += $Source.Name
        } catch {
            $Errors += @{
                file = $Source.Name
                error = $_.Exception.Message
            }
        }
    } else {
        $Restored += $Source.Name
    }
}

$Result = @{
    success = ($Errors.Count -eq 0)
    apply = [bool]$Apply
    archive = $ArchiveTools
    destination = $DestTools
    restored_count = $Restored.Count
    skipped_count = $Skipped.Count
    error_count = $Errors.Count
    restored = $Restored
    skipped = $Skipped
    errors = $Errors
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 6
} else {
    $Result
}

if ($Errors.Count -gt 0) {
    exit 1
}
