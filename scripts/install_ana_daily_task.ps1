param(
    [switch]$Apply,
    [switch]$Json,
    [string]$TaskName = "ANA_DEV_Daily_Check",
    [string]$At = "09:00"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DailyScript = Join-Path $ProjectRoot "scripts\ana_daily.ps1"
$PowerShell = (Get-Command powershell.exe).Source
$Argument = "-NoProfile -ExecutionPolicy Bypass -File `"$DailyScript`" -Iterations 1"

$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Argument -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Description = "ANA DEV local daily check: quick check plus maintenance dry-run report."

$Changed = $false
$Message = ""

if ($Apply) {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Description $Description `
        -Force | Out-Null
    $Changed = $true
    $Message = "Scheduled task installed or updated."
}
elseif ($Existing) {
    $Message = "Scheduled task already exists. Use -Apply to update it."
}
else {
    $Message = "Dry-run only. Use -Apply to install the scheduled task."
}

$Post = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$Result = [ordered]@{
    success = $true
    apply = [bool]$Apply
    changed = $Changed
    task_name = $TaskName
    at = $At
    project_root = [string]$ProjectRoot
    script = [string]$DailyScript
    exists = [bool]$Post
    state = if ($Post) { [string]$Post.State } else { "" }
    message = $Message
    next_action = ""
}

if ($Result.exists) {
    $Result.next_action = "Run Get-ScheduledTask -TaskName $TaskName to inspect or Start-ScheduledTask -TaskName $TaskName to test manually."
}
else {
    $Result.next_action = "Run this script with -Apply when task installation is intentional."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 4
}
else {
    if ($Result.exists) {
        Write-Host "PASS ANA daily task check"
    }
    else {
        Write-Host "DRY-RUN ANA daily task check"
    }
    Write-Host "Task: $TaskName"
    Write-Host "At: $At"
    Write-Host "Exists: $($Result.exists)"
    Write-Host "Message: $Message"
    Write-Host "Next: $($Result.next_action)"
}
