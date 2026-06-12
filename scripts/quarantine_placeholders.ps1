param(
    [string]$Stamp = (Get-Date -Format "yyyyMMddTHHmmssZ"),
    [switch]$Apply,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$AnaRoot = Join-Path $Root "ANA_MAX"
$QuarantineRoot = Join-Path $AnaRoot "archives\placeholders_quarantine\$Stamp"
$Marker = '"""Auto-created placeholder module."""'

$Moved = @()
$Skipped = @()
$Errors = @()
$ExcludedParts = @("archives", "sandbox", "logs", "memory", "venv", "__pycache__")

function Get-RelativePathLocal {
    param(
        [string]$Base,
        [string]$Path
    )
    $BaseFull = [System.IO.Path]::GetFullPath($Base).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $PathFull = [System.IO.Path]::GetFullPath($Path)
    if ($PathFull.StartsWith($BaseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $PathFull.Substring($BaseFull.Length)
    }
    return $PathFull
}

foreach ($File in Get-ChildItem -LiteralPath $AnaRoot -Recurse -Filter "*.py" -File) {
    $Relative = Get-RelativePathLocal -Base $AnaRoot -Path $File.FullName
    $Parts = $Relative -split '[\\/]'
    if ($Parts | Where-Object { $ExcludedParts -contains $_ }) {
        $Skipped += @{
            path = $Relative
            reason = "excluded_path"
        }
        continue
    }

    $RawContent = Get-Content -LiteralPath $File.FullName -Raw -ErrorAction Stop
    $Content = if ($null -eq $RawContent) { "" } else { $RawContent.Trim() }
    if ($Content -ne $Marker) {
        continue
    }

    $Destination = Join-Path $QuarantineRoot $Relative
    if ($Apply) {
        try {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
            Move-Item -LiteralPath $File.FullName -Destination $Destination -Force:$false
            $Moved += @{
                from = $Relative
                to = Get-RelativePathLocal -Base $AnaRoot -Path $Destination
            }
        } catch {
            $Errors += @{
                path = $Relative
                error = $_.Exception.Message
            }
        }
    } else {
        $Moved += @{
            from = $Relative
            to = Get-RelativePathLocal -Base $AnaRoot -Path $Destination
        }
    }
}

$Result = @{
    success = ($Errors.Count -eq 0)
    apply = [bool]$Apply
    quarantine_root = $QuarantineRoot
    moved_count = $Moved.Count
    skipped_count = $Skipped.Count
    error_count = $Errors.Count
    moved = $Moved
    skipped = $Skipped
    errors = $Errors
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
} else {
    $Result
}

if ($Errors.Count -gt 0) {
    exit 1
}
