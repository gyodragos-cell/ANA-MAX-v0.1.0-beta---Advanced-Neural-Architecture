$ModelFileContent = @"
FROM qwen2.5-coder:7b
PARAMETER num_ctx 2048
PARAMETER num_batch 128
SYSTEM `"OUTPUT ONLY VALID JSON. NO TALKING. Choose 1, 2, or 3 if presented with options.`"
"@

Set-Content -Path ".\Modelfile" -Value $ModelFileContent
Write-Host "Modelfile created. Building qwen-ana:7b..."
ollama create qwen-ana:7b -f Modelfile
Write-Host "Model built."
Remove-Item ".\Modelfile" -ErrorAction SilentlyContinue
