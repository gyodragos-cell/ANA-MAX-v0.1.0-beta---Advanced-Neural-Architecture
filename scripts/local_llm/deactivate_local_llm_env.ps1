if (Get-Command deactivate -ErrorAction SilentlyContinue) {
    deactivate
}
$Keys = @(
    "ANA_LOCAL_LLM_ENABLED",
    "ANA_LOCAL_LLM_BACKEND",
    "ANA_LOCAL_LLM_MODEL_NAME",
    "ANA_LOCAL_LLM_FALLBACK_MODEL_NAME",
    "ANA_LOCAL_LLM_DEVICE",
    "ANA_LOCAL_LLM_MODEL_PATH"
)
foreach ($Key in $Keys) {
    [Environment]::SetEnvironmentVariable($Key, $null, "Process")
}
Write-Host "ANA local LLM env deactivated."
