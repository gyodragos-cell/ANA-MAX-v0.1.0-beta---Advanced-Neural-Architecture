param(
    [switch]$Apply,
    [switch]$ArchiveLogs,
    [switch]$RotateLargeLogs,
    [switch]$CompressArchive,
    [switch]$Json,
    [int]$MaxLogMb = 25,
    [int]$MaxCacheMb = 250,
    [int]$LogAgeDays = 7
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Targets = @(
    @{ Name = "ANA logs"; Path = Join-Path $ProjectRoot "ANA_MAX\logs"; Type = "logs"; MaxMb = $MaxLogMb },
    @{ Name = "pytest cache"; Path = Join-Path $ProjectRoot ".pytest_cache"; Type = "cache"; MaxMb = $MaxCacheMb },
    @{ Name = "Python caches"; Path = $ProjectRoot; Type = "pycache"; MaxMb = $MaxCacheMb }
)

function Get-DirectorySize {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    return (Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { -not $_.PSIsContainer } |
        Measure-Object -Property Length -Sum).Sum
}

function Convert-BytesToMb {
    param([double]$Bytes)
    return [math]::Round($Bytes / 1MB, 3)
}

$Drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($ProjectRoot).Substring(0, 1))
$Memory = Get-CimInstance Win32_OperatingSystem
$Items = @()
$Actions = @()
$ArchiveRoot = Join-Path $ProjectRoot "ANA_MAX\sandbox\log_archive"
$ArchiveCandidates = @()
$LargeLogCandidates = @()
$CompressCandidates = @()

foreach ($Target in $Targets) {
    if ($Target.Type -eq "pycache") {
        $CacheDirs = Get-ChildItem -LiteralPath $Target.Path -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
        $Bytes = ($CacheDirs | ForEach-Object { Get-DirectorySize $_.FullName } | Measure-Object -Sum).Sum
        $OverLimit = (Convert-BytesToMb $Bytes) -gt $Target.MaxMb
        $Items += [ordered]@{
            name = $Target.Name
            path = [string]$Target.Path
            type = $Target.Type
            size_mb = Convert-BytesToMb $Bytes
            count = $CacheDirs.Count
            over_limit = $OverLimit
        }
        if ($Apply -and $OverLimit) {
            foreach ($Dir in $CacheDirs) {
                Remove-Item -LiteralPath $Dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
            $Actions += "Removed __pycache__ directories."
        }
        continue
    }

    $Bytes = Get-DirectorySize $Target.Path
    $SizeMb = Convert-BytesToMb $Bytes
    $OverLimit = $SizeMb -gt $Target.MaxMb
    $Items += [ordered]@{
        name = $Target.Name
        path = [string]$Target.Path
        type = $Target.Type
        size_mb = $SizeMb
        max_mb = $Target.MaxMb
        over_limit = $OverLimit
    }

    if ($Apply -and $OverLimit -and $Target.Type -eq "cache" -and (Test-Path -LiteralPath $Target.Path)) {
        Remove-Item -LiteralPath $Target.Path -Recurse -Force
        $Actions += "Removed $($Target.Name)."
    }
}

if (Test-Path -LiteralPath (Join-Path $ProjectRoot "ANA_MAX\logs")) {
    $LogRoot = Join-Path $ProjectRoot "ANA_MAX\logs"
    $Cutoff = (Get-Date).AddDays(-1 * $LogAgeDays)
    $ArchiveCandidates = Get-ChildItem -LiteralPath $LogRoot -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $Cutoff -and $_.Length -gt 0 } |
        Sort-Object LastWriteTime
    $LargeLogCandidates = Get-ChildItem -LiteralPath $LogRoot -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt ($MaxLogMb * 1MB) } |
        Sort-Object Length -Descending

    if ($Apply -and $ArchiveLogs -and $ArchiveCandidates.Count -gt 0) {
        $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $Destination = Join-Path $ArchiveRoot $Stamp
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
        foreach ($Log in $ArchiveCandidates) {
            Move-Item -LiteralPath $Log.FullName -Destination (Join-Path $Destination $Log.Name) -Force
        }
        $Actions += "Archived $($ArchiveCandidates.Count) old log files to $Destination."
    }

    if ($Apply -and $RotateLargeLogs -and $LargeLogCandidates.Count -gt 0) {
        $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $Destination = Join-Path $ArchiveRoot "rotated_$Stamp"
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
        foreach ($Log in $LargeLogCandidates) {
            $ArchivedPath = Join-Path $Destination $Log.Name
            Move-Item -LiteralPath $Log.FullName -Destination $ArchivedPath -Force
            New-Item -ItemType File -Path $Log.FullName -Force | Out-Null
        }
        $Actions += "Rotated $($LargeLogCandidates.Count) large log files to $Destination."
    }
}

if (Test-Path -LiteralPath $ArchiveRoot) {
    $CompressCandidates = Get-ChildItem -LiteralPath $ArchiveRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { -not (Test-Path -LiteralPath ($_.FullName + ".zip")) } |
        Sort-Object LastWriteTime

    if ($Apply -and $CompressArchive -and $CompressCandidates.Count -gt 0) {
        foreach ($Dir in $CompressCandidates) {
            $ZipPath = $Dir.FullName + ".zip"
            Compress-Archive -LiteralPath (Join-Path $Dir.FullName "*") -DestinationPath $ZipPath -Force
            Remove-Item -LiteralPath $Dir.FullName -Recurse -Force
        }
        $Actions += "Compressed $($CompressCandidates.Count) archive directories."
    }
}

$Result = [ordered]@{
    success = $true
    apply = [bool]$Apply
    archive_logs = [bool]$ArchiveLogs
    rotate_large_logs = [bool]$RotateLargeLogs
    compress_archive = [bool]$CompressArchive
    project_root = [string]$ProjectRoot
    disk = @{
        drive = $Drive.Name
        free_gb = [math]::Round($Drive.Free / 1GB, 2)
        used_gb = [math]::Round($Drive.Used / 1GB, 2)
    }
    memory = @{
        free_gb = [math]::Round($Memory.FreePhysicalMemory / 1MB, 2)
        total_gb = [math]::Round($Memory.TotalVisibleMemorySize / 1MB, 2)
    }
    items = $Items
    log_archive = @{
        root = [string]$ArchiveRoot
        age_days = $LogAgeDays
        candidates = $ArchiveCandidates.Count
        candidate_mb = Convert-BytesToMb (($ArchiveCandidates | Measure-Object -Property Length -Sum).Sum)
        large_candidates = $LargeLogCandidates.Count
        large_candidate_mb = Convert-BytesToMb (($LargeLogCandidates | Measure-Object -Property Length -Sum).Sum)
        compress_candidates = $CompressCandidates.Count
    }
    actions = $Actions
    next_action = ""
}

if ($Actions.Count -eq 0) {
    $Result.next_action = "No cleanup applied. Use -ArchiveLogs, -RotateLargeLogs, or -CompressArchive with -Apply intentionally."
}
else {
    $Result.next_action = "Cleanup applied. Run quick check next."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
}
else {
    Write-Host "PASS ANA maintenance report"
    Write-Host "Apply: $Apply"
    Write-Host "Disk free: $($Result.disk.free_gb) GB"
    Write-Host "Memory free: $($Result.memory.free_gb) GB"
    Write-Host "Archive log candidates: $($Result.log_archive.candidates)"
    Write-Host "Large log candidates: $($Result.log_archive.large_candidates)"
    Write-Host "Compress archive candidates: $($Result.log_archive.compress_candidates)"
    foreach ($Item in $Items) {
        Write-Host "$($Item.name): $($Item.size_mb) MB"
    }
    Write-Host "Next: $($Result.next_action)"
}
