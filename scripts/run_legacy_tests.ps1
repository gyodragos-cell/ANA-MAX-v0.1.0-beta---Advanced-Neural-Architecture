param(
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $root
try {
    $env:ANA_INCLUDE_LEGACY_TESTS = "1"
    if ($PytestArgs.Count -eq 0) {
        python -m pytest tests
    } else {
        python -m pytest @PytestArgs
    }
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:\ANA_INCLUDE_LEGACY_TESTS -ErrorAction SilentlyContinue
    Pop-Location
}
