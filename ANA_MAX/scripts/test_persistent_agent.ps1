# ANA MAX Persistent Agent Mode Smoke Test
# Validates persistent agent behavior across Ollama, MCP, and OpenRouter backends
# Includes live logging for real-time monitoring

param(
    [switch]$Verbose,
    [int]$TestDuration = 120
)

$ErrorActionPreference = "Stop"
$LogDir = "C:\ANA_MAX\logs"
$SmokeTestLog = "$LogDir\persistent_agent_smoke_test.log"
$LiveLog = "$LogDir\persistent_agent_live.log"

# Ensure log directory exists
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Function for live logging
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to smoke test log
    Add-Content -Path $SmokeTestLog -Value $logEntry -Encoding UTF8
    
    # Write to live log for real-time monitoring
    Add-Content -Path $LiveLog -Value $logEntry -Encoding UTF8
    
    # Console output with color
    switch ($Level) {
        "INFO" { Write-Host $logEntry -ForegroundColor Cyan }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
        "ERROR" { Write-Host $logEntry -ForegroundColor Red }
        "WARN" { Write-Host $logEntry -ForegroundColor Yellow }
        default { Write-Host $logEntry }
    }
}

# Function to test Ollama backend
function Test-OllamaBackend {
    Write-Log "Testing Ollama backend..." -Level "INFO"
    
    try {
        # Check if Ollama is running
        $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        Write-Log "Ollama is running. Available models: $($ollamaResponse.models.Count)" -Level "SUCCESS"
        
        # Check if ana_max_agent model exists
        $anaMaxModel = $ollamaResponse.models | Where-Object { $_.name -like "*ana_max*" }
        if ($anaMaxModel) {
            Write-Log "ANA_MAX agent model found: $($anaMaxModel.name)" -Level "SUCCESS"
        } else {
            Write-Log "ANA_MAX agent model not found. Using default qwen2.5-coder:7b" -Level "WARN"
        }
        
        return $true
    }
    catch {
        Write-Log "Ollama backend test failed: $_" -Level "ERROR"
        return $false
    }
}

# Function to test OpenRouter backend
function Test-OpenRouterBackend {
    Write-Log "Testing OpenRouter backend..." -Level "INFO"
    
    try {
        $keysFile = "C:\Users\billy\Desktop\ana_dev\apikeys_openrouter.txt"
        if (Test-Path $keysFile) {
            $keys = Get-Content $keysFile
            $keyCount = ($keys | Where-Object { $_.Trim() -ne "" }).Count
            Write-Log "OpenRouter keys found: $keyCount" -Level "SUCCESS"
            
            if ($keyCount -ge 10) {
                Write-Log "OpenRouter has required 10 keys for rotation" -Level "SUCCESS"
            } else {
                Write-Log "OpenRouter has $keyCount keys (expected 10)" -Level "WARN"
            }
            
            return $true
        } else {
            Write-Log "OpenRouter keys file not found: $keysFile" -Level "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "OpenRouter backend test failed: $_" -Level "ERROR"
        return $false
    }
}

# Function to test MCP config
function Test-MCPConfig {
    Write-Log "Testing MCP configuration..." -Level "INFO"
    
    try {
        $mcpConfig = "C:\Users\billy\Desktop\ana_dev\ANA_MAX\config\mcp_ana_max_agent.json"
        if (Test-Path $mcpConfig) {
            $config = Get-Content $mcpConfig | ConvertFrom-Json
            Write-Log "MCP config loaded successfully" -Level "SUCCESS"
            Write-Log "Agent name: $($config.name)" -Level "INFO"
            Write-Log "Persistent mode: $($config.persistent)" -Level "INFO"
            Write-Log "Context window: $($config.context_window)" -Level "INFO"
            
            # Check backends
            Write-Log "Ollama enabled: $($config.backends.ollama.enabled)" -Level "INFO"
            Write-Log "OpenRouter enabled: $($config.backends.openrouter.enabled)" -Level "INFO"
            
            return $true
        } else {
            Write-Log "MCP config not found: $mcpConfig" -Level "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "MCP config test failed: $_" -Level "ERROR"
        return $false
    }
}

# Function to test backend connections
function Test-BackendConnections {
    Write-Log "Testing backend connections..." -Level "INFO"
    
    try {
        $connectionsConfig = "C:\Users\billy\Desktop\ana_dev\ANA_MAX\config\backend_connections.json"
        if (Test-Path $connectionsConfig) {
            $config = Get-Content $connectionsConfig | ConvertFrom-Json
            Write-Log "Backend connections config loaded" -Level "SUCCESS"
            
            # Test each connection
            foreach ($connection in $config.connections.PSObject.Properties) {
                $name = $connection.Name
                $enabled = $connection.Value.enabled
                Write-Log "Connection ${name}: enabled=${enabled}" -Level "INFO"
            }
            
            # Check orchestration settings
            Write-Log "Default backend: $($config.orchestration.default_backend)" -Level "INFO"
            Write-Log "Fallback backend: $($config.orchestration.fallback_backend)" -Level "INFO"
            Write-Log "Auto failover: $($config.orchestration.auto_failover)" -Level "INFO"
            
            return $true
        } else {
            Write-Log "Backend connections config not found: $connectionsConfig" -Level "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Backend connections test failed: $_" -Level "ERROR"
        return $false
    }
}

# Function to test persistent agent prompt
function Test-PersistentAgentPrompt {
    Write-Log "Testing persistent agent prompt..." -Level "INFO"
    
    try {
        $openrouterBackend = "C:\Users\billy\Desktop\ana_dev\ANA_MAX\core\backends\openrouter_backend.py"
        if (Test-Path $openrouterBackend) {
            $content = Get-Content $openrouterBackend -Raw
            
            # Check for persistent agent prompt markers
            if ($content -match "ANA MAX Distributed Copilot Agent") {
                Write-Log "Persistent agent prompt found in OpenRouter backend" -Level "SUCCESS"
            } else {
                Write-Log "Persistent agent prompt not found in OpenRouter backend" -Level "ERROR"
                return $false
            }
            
            # Check for required response format
            if ($content -match "ANA_MAX Agent Online") {
                Write-Log "Response format marker found" -Level "SUCCESS"
            } else {
                Write-Log "Response format marker not found" -Level "WARN"
            }
            
            return $true
        } else {
            Write-Log "OpenRouter backend not found: $openrouterBackend" -Level "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Persistent agent prompt test failed: $_" -Level "ERROR"
        return $false
    }
}

# Function to test ANA MAX modules
function Test-ANAMAXModules {
    Write-Log "Testing ANA MAX OS modules..." -Level "INFO"
    
    $modules = @{
        "Procmon" = "C:\ANA_MAX\procmon"
        "Blackbox" = "C:\ANA_MAX\logs"
        "Runtime" = "C:\ANA_MAX\runtime"
    }
    
    $allModulesOK = $true
    
    foreach ($module in $modules.GetEnumerator()) {
        if (Test-Path $module.Value) {
            Write-Log "$($module.Key) module found at $($module.Value)" -Level "SUCCESS"
        } else {
            Write-Log "$($module.Key) module not found at $($module.Value)" -Level "WARN"
            $allModulesOK = $false
        }
    }
    
    return $allModulesOK
}

# Main test execution
Write-Log "=== ANA MAX Persistent Agent Mode Smoke Test ===" -Level "INFO"
Write-Log "Test duration: $TestDuration seconds" -Level "INFO"
Write-Log "Verbose mode: $Verbose" -Level "INFO"
Write-Log ""

$results = @{}

# Run all tests
$results["Ollama"] = Test-OllamaBackend
Write-Log ""

$results["OpenRouter"] = Test-OpenRouterBackend
Write-Log ""

$results["MCP"] = Test-MCPConfig
Write-Log ""

$results["Connections"] = Test-BackendConnections
Write-Log ""

$results["Prompt"] = Test-PersistentAgentPrompt
Write-Log ""

$results["Modules"] = Test-ANAMAXModules
Write-Log ""

# Summary
Write-Log "=== Test Summary ===" -Level "INFO"
$passed = 0
$failed = 0

foreach ($result in $results.GetEnumerator()) {
    $status = if ($result.Value) { "PASS" } else { "FAIL" }
    $level = if ($result.Value) { "SUCCESS" } else { "ERROR" }
    Write-Log "$($result.Name): $status" -Level $level
    
    if ($result.Value) { $passed++ } else { $failed++ }
}

Write-Log ""
Write-Log "Total: $passed passed, $failed failed" -Level "INFO"

if ($failed -eq 0) {
    Write-Log "=== SMOKE TEST PASSED ===" -Level "SUCCESS"
    exit 0
} else {
    Write-Log "=== SMOKE TEST FAILED ===" -Level "ERROR"
    exit 1
}
