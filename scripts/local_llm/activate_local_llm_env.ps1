$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$EnvFile = Join-Path $Root ".env.local_llm"
$Activate = Join-Path $Root "local_llm_env\Scripts\Activate.ps1"

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $Line = $_.Trim()
        if ($Line -and -not $Line.StartsWith("#") -and $Line.Contains("=")) {
            $Key, $Value = $Line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($Key.Trim(), $Value.Trim(), "Process")
        }
    }
}

if (-not (Test-Path $Activate)) {
    Write-Host "local_llm_env is missing. Run: python scripts\local_llm\create_local_llm_env.py --apply"
    return
}

. $Activate
Write-Host "ANA local LLM env activated."
