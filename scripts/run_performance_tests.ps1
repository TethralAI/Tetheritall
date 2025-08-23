# Performance Test Runner Script (PowerShell)
# This script runs various performance tests to validate the system's ability to handle
# complex calls, simultaneous calls, and high user load.

param(
    [string]$GatewayBase = "http://localhost:8000",
    [string]$ApiToken = "test-api-key",
    [string]$TestDuration = "5m",
    [int]$VUs = 50,
    [string]$K6Binary = "k6",
    [switch]$All,
    [switch]$Results,
    [switch]$Help,
    [string]$TestName
)

# Test scenarios
$TestScenarios = @{
    "constant_load" = "Constant load testing with sustained traffic"
    "spike_load" = "Spike testing with sudden traffic increases"
    "stress_load" = "Stress testing with gradual load increase"
    "complex_operations" = "Complex operations testing"
    "simultaneous_calls" = "Simultaneous calls testing"
}

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if k6 is installed
    try {
        $null = Get-Command $K6Binary -ErrorAction Stop
    }
    catch {
        Write-Error "k6 is not installed or not in PATH"
        Write-Status "Please install k6 from https://k6.io/docs/getting-started/installation/"
        exit 1
    }
    
    # Check if gateway is accessible
    try {
        $response = Invoke-WebRequest -Uri "$GatewayBase/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            throw "Gateway returned status code $($response.StatusCode)"
        }
    }
    catch {
        Write-Warning "Gateway is not accessible at $GatewayBase"
        Write-Status "Make sure the API server is running"
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -notmatch "^[Yy]$") {
            exit 1
        }
    }
    
    Write-Success "Prerequisites check completed"
}

# Function to run a single test
function Invoke-Test {
    param(
        [string]$TestName,
        [string]$Description,
        [int]$TestVUs = $VUs,
        [string]$TestDuration = $TestDuration
    )
    
    Write-Status "Running $TestName`: $Description"
    Write-Status "VUs: $TestVUs, Duration: $TestDuration"
    
    # Create output directory
    $date = Get-Date -Format "yyyyMMdd"
    $time = Get-Date -Format "HHmmss"
    $resultsDir = "test_results\$date"
    New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
    
    $outputFile = "$resultsDir\${TestName}_${time}.json"
    $summaryFile = "$resultsDir\${TestName}_${time}_summary.json"
    
    # Run k6 test
    $env:GATEWAY_BASE = $GatewayBase
    $env:API_TOKEN = $ApiToken
    $env:VUS = $TestVUs
    $env:TEST_DURATION = $TestDuration
    
    try {
        & $K6Binary run `
            --env GATEWAY_BASE="$GatewayBase" `
            --env API_TOKEN="$ApiToken" `
            --env VUS="$TestVUs" `
            --env TEST_DURATION="$TestDuration" `
            --out json="$outputFile" `
            --summary-export="$summaryFile" `
            k6/enhanced_load.js
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$TestName completed successfully"
            Write-Status "Results saved to $outputFile"
        }
        else {
            Write-Error "$TestName failed"
            return $false
        }
    }
    catch {
        Write-Error "$TestName failed with error: $_"
        return $false
    }
    
    return $true
}

# Function to run all tests
function Invoke-AllTests {
    Write-Status "Starting comprehensive performance test suite..."
    
    # Create results directory
    $date = Get-Date -Format "yyyyMMdd"
    $resultsDir = "test_results\$date"
    New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
    
    # Run each test scenario
    foreach ($testName in $TestScenarios.Keys) {
        $success = $false
        
        switch ($testName) {
            "constant_load" {
                $success = Invoke-Test $testName $TestScenarios[$testName] 50 "10m"
            }
            "spike_load" {
                $success = Invoke-Test $testName $TestScenarios[$testName] 100 "5m"
            }
            "stress_load" {
                $success = Invoke-Test $testName $TestScenarios[$testName] 60 "15m"
            }
            "complex_operations" {
                $success = Invoke-Test $testName $TestScenarios[$testName] 10 "5m"
            }
            "simultaneous_calls" {
                $success = Invoke-Test $testName $TestScenarios[$testName] 20 "5m"
            }
        }
        
        # Wait between tests
        if ($success) {
            Write-Status "Waiting 30 seconds before next test..."
            Start-Sleep -Seconds 30
        }
    }
    
    Write-Success "All tests completed"
}

# Function to run a specific test
function Invoke-SpecificTest {
    param([string]$TestName)
    
    if (-not $TestScenarios.ContainsKey($TestName)) {
        Write-Error "Unknown test: $TestName"
        Write-Status "Available tests: $($TestScenarios.Keys -join ', ')"
        exit 1
    }
    
    switch ($TestName) {
        "constant_load" {
            Invoke-Test $TestName $TestScenarios[$TestName] 50 "10m"
        }
        "spike_load" {
            Invoke-Test $TestName $TestScenarios[$TestName] 100 "5m"
        }
        "stress_load" {
            Invoke-Test $TestName $TestScenarios[$TestName] 60 "15m"
        }
        "complex_operations" {
            Invoke-Test $TestName $TestScenarios[$TestName] 10 "5m"
        }
        "simultaneous_calls" {
            Invoke-Test $TestName $TestScenarios[$TestName] 20 "5m"
        }
    }
}

# Function to show test results
function Show-Results {
    $date = Get-Date -Format "yyyyMMdd"
    $resultsDir = "test_results\$date"
    
    if (-not (Test-Path $resultsDir)) {
        Write-Error "No test results found for today"
        exit 1
    }
    
    Write-Status "Test Results Summary:"
    Write-Host ""
    
    $summaryFiles = Get-ChildItem -Path $resultsDir -Filter "*_summary.json"
    
    foreach ($summaryFile in $summaryFiles) {
        $testName = $summaryFile.BaseName -replace "_summary$", ""
        Write-Status "Test: $testName"
        
        try {
            $json = Get-Content $summaryFile.FullName | ConvertFrom-Json
            
            if ($json.metrics.http_reqs.values.count) {
                Write-Host "  Total Requests: $($json.metrics.http_reqs.values.count)"
            }
            if ($json.metrics.http_req_duration.values.avg) {
                Write-Host "  Avg Response Time: $([math]::Round($json.metrics.http_req_duration.values.avg, 2))ms"
            }
            if ($json.metrics.http_req_failed.values.rate) {
                $errorRate = [math]::Round($json.metrics.http_req_failed.values.rate * 100, 2)
                Write-Host "  Error Rate: ${errorRate}%"
            }
        }
        catch {
            Write-Host "  Results file: $($summaryFile.FullName)"
        }
        
        Write-Host ""
    }
}

# Function to show help
function Show-Help {
    Write-Host "Performance Test Runner"
    Write-Host ""
    Write-Host "Usage: .\run_performance_tests.ps1 [OPTIONS] [TEST_NAME]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help                    Show this help message"
    Write-Host "  -All                     Run all tests"
    Write-Host "  -Results                 Show test results"
    Write-Host "  -GatewayBase URL         Set gateway URL (default: $GatewayBase)"
    Write-Host "  -ApiToken TOKEN          Set API token (default: $ApiToken)"
    Write-Host "  -TestDuration DUR        Set test duration (default: $TestDuration)"
    Write-Host "  -VUs VUS                 Set virtual users (default: $VUs)"
    Write-Host ""
    Write-Host "Available Tests:"
    foreach ($testName in $TestScenarios.Keys) {
        Write-Host "  $testName`: $($TestScenarios[$testName])"
    }
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_performance_tests.ps1 -All                    # Run all tests"
    Write-Host "  .\run_performance_tests.ps1 constant_load           # Run constant load test"
    Write-Host "  .\run_performance_tests.ps1 -GatewayBase http://api:8000 -All  # Run all tests with custom gateway"
    Write-Host "  .\run_performance_tests.ps1 -Results                # Show today's test results"
}

# Main script logic
function Main {
    # Show help if requested
    if ($Help) {
        Show-Help
        return
    }
    
    # Check prerequisites
    Test-Prerequisites
    
    # Show configuration
    Write-Status "Configuration:"
    Write-Host "  Gateway: $GatewayBase"
    Write-Host "  API Token: $ApiToken"
    Write-Host "  Test Duration: $TestDuration"
    Write-Host "  Virtual Users: $VUs"
    Write-Host ""
    
    # Execute based on arguments
    if ($Results) {
        Show-Results
    }
    elseif ($All) {
        Invoke-AllTests
    }
    elseif ($TestName) {
        Invoke-SpecificTest $TestName
    }
    else {
        Write-Error "No test specified"
        Show-Help
        exit 1
    }
}

# Run main function
Main
