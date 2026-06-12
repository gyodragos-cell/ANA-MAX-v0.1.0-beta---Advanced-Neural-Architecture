param(
    [int]$Iterations = 2,
    [double]$SlowMs = 250,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Bridge = Join-Path $ProjectRoot "cascade_integration\direct_bridge.py"

$Output = & python $Bridge --benchmark-all --iterations $Iterations --slow-ms $SlowMs
$Result = $Output | ConvertFrom-Json

if ($Json) {
    $Result | ConvertTo-Json -Depth 8
}
else {
    Write-Host "PASS ANA tool benchmark"
    Write-Host "Iterations: $($Result.iterations)"
    Write-Host "Slow threshold ms: $($Result.slow_threshold_ms)"
    Write-Host "Slow tools: $($Result.slow_tools.PSObject.Properties.Count)"
    foreach ($Tool in $Result.direct.PSObject.Properties) {
        Write-Host "$($Tool.Name): avg=$($Tool.Value.avg_ms)ms success=$($Tool.Value.success_rate)%"
    }
}
