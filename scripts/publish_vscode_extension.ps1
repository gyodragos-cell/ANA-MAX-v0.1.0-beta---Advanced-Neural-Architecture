param(
    [switch]$Publish,
    [switch]$InstallLocal
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExtensionDir = Join-Path $RepoRoot "vscode_extension"
$VsixName = "advanced-neural-architecture-0.2.0.vsix"
$VsixPath = Join-Path $ExtensionDir $VsixName
$CanonicalRepo = "ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Write-Host "ANA MAX VS Code extension publish helper"
Write-Host "Repo: $RepoRoot"
Write-Host "Extension: $ExtensionDir"

Set-Location $ExtensionDir

Write-Host "[1/5] Checking extension JavaScript"
Invoke-Checked { node --check .\src\extension.js } "JavaScript check"

Write-Host "[2/5] Packaging VSIX"
Invoke-Checked { npm.cmd run package } "VSIX package"

if (-not (Test-Path -LiteralPath $VsixPath)) {
    throw "VSIX was not created: $VsixPath"
}

Write-Host "[3/5] Verifying VSIX contents"
Invoke-Checked { python -m zipfile -l $VsixPath | Out-Host } "VSIX listing"

$LinkCheck = python -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); data=z.read('extension/package.json').decode('utf-8') + z.read('extension/src/extension.js').decode('utf-8'); print('OK' if sys.argv[2] in data else 'MISSING')" $VsixPath $CanonicalRepo
if ($LinkCheck.Trim() -ne "OK") {
    throw "Canonical repository link missing inside VSIX."
}

Write-Host "[4/5] VSIX link check OK"

if ($InstallLocal) {
    Write-Host "Installing locally with VS Code"
    Invoke-Checked { code --install-extension $VsixPath --force } "Local VSIX install"
}

if ($Publish) {
    Write-Host "[5/5] Publishing VSIX"
    Write-Host "No token is stored by this script. Use 'vsce login' first or set VSCE_PAT only for this shell."

    if ($env:VSCE_PAT) {
        Invoke-Checked { npx vsce publish --packagePath $VsixPath -p $env:VSCE_PAT } "VS Code Marketplace publish"
    } else {
        Invoke-Checked { npx vsce publish --packagePath $VsixPath } "VS Code Marketplace publish"
    }
} else {
    Write-Host "[5/5] Publish skipped. To publish, rerun with -Publish."
}

Write-Host "Done: $VsixPath"
