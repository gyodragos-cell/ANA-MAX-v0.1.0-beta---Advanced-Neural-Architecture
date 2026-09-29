param(
    [switch]$Apply,
    [switch]$Json,
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ArchiveRoot = Join-Path $ProjectRoot "ANA_MAX\sandbox\log_archive"
$Removed = @()
$Compressed = @()

if (-not (Test-Path -LiteralPath $ArchiveRoot)) {
    New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
}

$Directories = Get-ChildItem -LiteralPath $ArchiveRoot -Directory -Force -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime
$CompressCandidates = $Directories |
    Where-Object { -not (Test-Path -LiteralPath ($_.FullName + ".zip")) }

if ($Apply) {
    foreach ($Directory in $CompressCandidates) {
        $ZipPath = $Directory.FullName + ".zip"
        Compress-Archive -LiteralPath (Join-Path $Directory.FullName "*") -DestinationPath $ZipPath -Force
        Remove-Item -LiteralPath $Directory.FullName -Recurse -Force
        $Compressed += [ordered]@{
            source = $Directory.FullName
            zip = $ZipPath
        }
    }
}

$Cutoff = (Get-Date).AddDays(-1 * $RetentionDays)
$OldZips = Get-ChildItem -LiteralPath $ArchiveRoot -File -Filter "*.zip" -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $Cutoff } |
    Sort-Object LastWriteTime

if ($Apply) {
    foreach ($Zip in $OldZips) {
        Remove-Item -LiteralPath $Zip.FullName -Force
        $Removed += $Zip.FullName
    }
}

$ZipFiles = Get-ChildItem -LiteralPath $ArchiveRoot -File -Filter "*.zip" -Force -ErrorAction SilentlyContinue
$ZipBytes = ($ZipFiles | Measure-Object -Property Length -Sum).Sum

$Result = [ordered]@{
    success = $true
    apply = [bool]$Apply
    archive_root = [string]$ArchiveRoot
    retention_days = $RetentionDays
    compress_candidates = $CompressCandidates.Count
    old_zip_candidates = $OldZips.Count
    compressed = $Compressed
    removed = $Removed
    zip_count = $ZipFiles.Count
    zip_mb = [math]::Round($ZipBytes / 1MB, 3)
    next_action = ""
}

if ($Apply) {
    $Result.next_action = "Compression/retention applied. Run quick check next."
}
else {
    $Result.next_action = "Dry-run complete. Use -Apply to compress candidates and remove old zip archives."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 6
}
else {
    Write-Host "PASS ANA log compress"
    Write-Host "Apply: $Apply"
    Write-Host "Compress candidates: $($Result.compress_candidates)"
    Write-Host "Old zip candidates: $($Result.old_zip_candidates)"
    Write-Host "Zip archives: $($Result.zip_count), $($Result.zip_mb) MB"
    Write-Host "Next: $($Result.next_action)"
}
