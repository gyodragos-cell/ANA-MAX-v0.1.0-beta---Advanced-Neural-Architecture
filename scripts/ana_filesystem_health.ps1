param(
    [switch]$Apply,
    [switch]$Json,
    [int]$LargeFileMb = 100,
    [int]$OldFileDays = 30
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$CleanupArchive = Join-Path $ProjectRoot "ANA_MAX\sandbox\fs_cleanup_archive"
$Now = Get-Date
$IgnorePattern = "\\ANA_MAX\\sandbox\\log_archive\\|\\ANA_MAX\\venv\\|\\.venv\\|\\__pycache__\\"

$Files = Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch $IgnorePattern }

$LargeFiles = @($Files | Where-Object { $_.Length -ge ($LargeFileMb * 1MB) } | Sort-Object Length -Descending)
$OldFiles = @($Files | Where-Object { $_.LastWriteTime -lt $Now.AddDays(-1 * $OldFileDays) } | Sort-Object LastWriteTime)
$CleanupCandidates = @($Files | Where-Object { $_.Extension -in @(".tmp", ".bak", ".old") } | Sort-Object LastWriteTime)

$DuplicateGroups = @(
    $Files |
        Group-Object Length |
        Where-Object { $_.Count -gt 1 -and [int64]$_.Name -gt 0 } |
        ForEach-Object {
            $_.Group |
                Group-Object Name |
                Where-Object { $_.Count -gt 1 } |
                ForEach-Object {
                    [ordered]@{
                        name = $_.Name
                        count = $_.Count
                        bytes_each = $_.Group[0].Length
                        examples = @($_.Group | Select-Object -First 5 | ForEach-Object { $_.FullName })
                    }
                }
        }
)

$Actions = @()
if ($Apply -and $CleanupCandidates.Count -gt 0) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Destination = Join-Path $CleanupArchive $Stamp
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($File in $CleanupCandidates) {
        $Relative = Resolve-Path -LiteralPath $File.FullName -Relative
        $SafeName = ($Relative -replace "^[.][\\/]", "") -replace "[:\\/]", "_"
        Move-Item -LiteralPath $File.FullName -Destination (Join-Path $Destination $SafeName) -Force
    }
    $Actions += "Archived $($CleanupCandidates.Count) cleanup candidate files to $Destination."
}

$Result = [ordered]@{
    success = $true
    apply = [bool]$Apply
    project_root = [string]$ProjectRoot
    thresholds = @{
        large_file_mb = $LargeFileMb
        old_file_days = $OldFileDays
    }
    counts = @{
        scanned_files = $Files.Count
        large_files = $LargeFiles.Count
        old_files = $OldFiles.Count
        cleanup_candidates = $CleanupCandidates.Count
        duplicate_groups = $DuplicateGroups.Count
    }
    large_files = @($LargeFiles | Select-Object -First 20 | ForEach-Object {
        [ordered]@{
            path = $_.FullName
            size_mb = [math]::Round($_.Length / 1MB, 3)
            last_write = $_.LastWriteTime
        }
    })
    cleanup_candidates = @($CleanupCandidates | Select-Object -First 50 | ForEach-Object {
        [ordered]@{
            path = $_.FullName
            size_kb = [math]::Round($_.Length / 1KB, 3)
            last_write = $_.LastWriteTime
        }
    })
    duplicate_groups = @($DuplicateGroups | Select-Object -First 20)
    actions = $Actions
    next_action = ""
}

if ($Actions.Count -gt 0) {
    $Result.next_action = "Filesystem cleanup applied. Run quick check next."
}
else {
    $Result.next_action = "Filesystem health scan complete. No cleanup candidates archived."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
}
else {
    Write-Host "PASS ANA filesystem health"
    Write-Host "Scanned files: $($Result.counts.scanned_files)"
    Write-Host "Large files: $($Result.counts.large_files)"
    Write-Host "Old files: $($Result.counts.old_files)"
    Write-Host "Cleanup candidates: $($Result.counts.cleanup_candidates)"
    Write-Host "Duplicate groups: $($Result.counts.duplicate_groups)"
    Write-Host "Next: $($Result.next_action)"
}
