param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$AnaMaxRoot = Join-Path $ProjectRoot "ANA_MAX"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
$EnvExampleFile = Join-Path $AnaMaxRoot ".env.example"
$EnvFile = Join-Path $AnaMaxRoot ".env"
$VenvRoot = Join-Path $AnaMaxRoot "venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Args = @("-3") }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Args = @() }
    }

    throw "Python launcher not found. Install Python 3 or make 'py' available."
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
    if (Test-Path -LiteralPath $EnvExampleFile) {
        Copy-Item -LiteralPath $EnvExampleFile -Destination $EnvFile -Force
    }
    else {
        New-Item -ItemType File -Path $EnvFile -Force | Out-Null
    }
}

$CreatedVenv = $false
$InstalledDeps = $false

if ($Apply) {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        $Launcher = Get-PythonLauncher
        $LauncherArgs = @($Launcher.Args + @("-m", "venv", $VenvRoot))
        & $Launcher.Command @LauncherArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create ANA_MAX venv. Exit code: $LASTEXITCODE"
        }
        $CreatedVenv = Test-Path -LiteralPath $VenvPython
    }

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        throw "ANA_MAX venv was not created successfully."
    }

    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed. Exit code: $LASTEXITCODE"
    }
    & $VenvPython -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed. Exit code: $LASTEXITCODE"
    }
    $InstalledDeps = $true
}

$Result = [ordered]@{
    project_root = [string]$ProjectRoot
    ana_max_root = [string]$AnaMaxRoot
    env_file = [string]$EnvFile
    env_exists = (Test-Path -LiteralPath $EnvFile)
    requirements_file = [string]$RequirementsFile
    venv_root = [string]$VenvRoot
    venv_exists = (Test-Path -LiteralPath $VenvPython)
    venv_created = $CreatedVenv
    dependencies_installed = $InstalledDeps
    apply = [bool]$Apply
    next_step = if ($Apply) {
        "Run START_ANA.bat to launch ANA MAX."
    } else {
        "Re-run with -Apply to create the venv and install dependencies."
    }
}

$Result | ConvertTo-Json -Depth 4
