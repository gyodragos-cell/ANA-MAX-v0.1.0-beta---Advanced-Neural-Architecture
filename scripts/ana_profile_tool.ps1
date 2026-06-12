param(
    [string]$Tool = "agent_coach",
    [int]$Iterations = 5,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Bridge = Join-Path $ProjectRoot "cascade_integration\direct_bridge.py"

$Payloads = @{
    agent_coach = '{"action":"recommend","task":"profile direct tool latency","limit":5}'
    tool_router = '{"task":"profile direct tool latency","max_tools":4}'
    file_operations = '{"operation":"list","path":"."}'
}

if (-not $Payloads.ContainsKey($Tool)) {
    throw "No safe profile payload configured for tool: $Tool"
}

$Samples = @()
for ($Index = 0; $Index -lt $Iterations; $Index++) {
    $Started = Get-Date
    $PayloadBytes = [System.Text.Encoding]::UTF8.GetBytes($Payloads[$Tool])
    $PayloadB64 = [Convert]::ToBase64String($PayloadBytes)
    $Output = & python $Bridge --execute $Tool --payload-b64 $PayloadB64
    $Elapsed = ((Get-Date) - $Started).TotalMilliseconds
    $Data = $Output | ConvertFrom-Json
    $Samples += [ordered]@{
        iteration = $Index + 1
        process_ms = [math]::Round($Elapsed, 3)
        tool_ms = $Data.latency_ms
        success = [bool]$Data.success
        error = [string]$Data.error
    }
}

$ToolMs = @($Samples | ForEach-Object { [double]$_.tool_ms })
$ProcessMs = @($Samples | ForEach-Object { [double]$_.process_ms })
$Result = [ordered]@{
    success = -not ($Samples | Where-Object { -not $_.success })
    tool = $Tool
    iterations = $Iterations
    avg_tool_ms = [math]::Round(($ToolMs | Measure-Object -Average).Average, 3)
    avg_process_ms = [math]::Round(($ProcessMs | Measure-Object -Average).Average, 3)
    min_tool_ms = [math]::Round(($ToolMs | Measure-Object -Minimum).Minimum, 3)
    max_tool_ms = [math]::Round(($ToolMs | Measure-Object -Maximum).Maximum, 3)
    samples = $Samples
    next_action = "Compare process_ms vs tool_ms to separate Python startup overhead from tool execution."
}

if ($Json) {
    $Result | ConvertTo-Json -Depth 6
}
else {
    Write-Host "PASS ANA tool profile"
    Write-Host "Tool: $Tool"
    Write-Host "Avg tool ms: $($Result.avg_tool_ms)"
    Write-Host "Avg process ms: $($Result.avg_process_ms)"
    Write-Host "Next: $($Result.next_action)"
}

if (-not $Result.success) {
    exit 1
}
