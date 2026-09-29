param(
    [switch]$Apply,
    [switch]$KeepUnicode,
    [string[]]$ExtraFile = @()
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonScript = Join-Path $ScriptDir "ana_encoding_normalize.py"

$ArgsList = @($PythonScript, "--root", $ProjectRoot)
if ($Apply) {
    $ArgsList += "--apply"
}
if ($KeepUnicode) {
    $ArgsList += "--keep-unicode"
}
foreach ($File in $ExtraFile) {
    $ArgsList += @("--extra-file", $File)
}

python @ArgsList
exit $LASTEXITCODE
