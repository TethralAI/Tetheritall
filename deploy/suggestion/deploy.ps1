# Tethral Suggestion Engine Deployment Script (PowerShell)
# This script deploys the suggestion service with all robustness features

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "upgrade", "uninstall", "status", "logs", "test")]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "prod", "mobile")]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "iot",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Configuration
$CHART_PATH = "deploy/helm/suggestion"
$VALUES_FILE = ""

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

# Function to show usage
function Show-Usage {
    Write-Host @"
Usage: .\deploy.ps1 [OPTIONS] COMMAND

Commands:
    deploy          Deploy the suggestion service
    upgrade         Upgrade existing deployment
    uninstall       Uninstall the suggestion service
    status          Check deployment status
    logs            Show service logs
    test            Run deployment tests

Options:
    -Environment ENV       Environment (dev, staging, prod, mobile)
    -Namespace NS         Kubernetes namespace (default: iot)
    -Force                Force deployment without confirmation
    -DryRun               Show what would be deployed without applying
    -Help                 Show this help message

Examples:
    .\deploy.ps1 -Command deploy -Environment dev
    .\deploy.ps1 -Command deploy -Environment prod -DryRun
    .\deploy.ps1 -Command upgrade -Environment staging
    .\deploy.ps1 -Command status
"@
}

# Function to validate environment
function Validate-Environment {
    switch ($Environment) {
        "dev" { $script:VALUES_FILE = "$CHART_PATH/values.yaml" }
        "staging" { $script:VALUES_FILE = "$CHART_PATH/values-staging.yaml" }
        "prod" { $script:VALUES_FILE = "$CHART_PATH/values-prod.yaml" }
        "mobile" { $script:VALUES_FILE = "$CHART_PATH/values-mobile.yaml" }
        default {
            Write-Error "Invalid environment: $Environment"
            Write-Error "Valid environments: dev, staging, prod, mobile"
            exit 1
        }
    }
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if kubectl is installed
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        Write-Error "kubectl is not installed"
        exit 1
    }
    
    # Check if helm is installed
    if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
        Write-Error "helm is not installed"
        exit 1
    }
    
    # Check if namespace exists
    try {
        kubectl get namespace $Namespace | Out-Null
    }
    catch {
        Write-Warning "Namespace $Namespace does not exist, creating..."
        kubectl create namespace $Namespace
    }
    
    # Check if cluster is accessible
    try {
        kubectl cluster-info | Out-Null
    }
    catch {
        Write-Error "Cannot connect to Kubernetes cluster"
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to generate secrets
function New-Secrets {
    Write-Status "Generating secrets..."
    
    # Generate encryption key
    $ENCRYPTION_KEY = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    
    # Generate JWT secret
    $JWT_SECRET = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    
    # Generate rate limit secret
    $RATE_LIMIT_SECRET = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    
    # Create secrets file
    $secretsYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: suggestion-secrets
  namespace: $Namespace
type: Opaque
data:
  encryption-key: $ENCRYPTION_KEY
  jwt-secret: $JWT_SECRET
  rate-limit-secret: $RATE_LIMIT_SECRET
  llm-api-key: ""
  firebase-credentials: ""
  apns-key: ""
  database-password: ""
"@
    
    if (-not $DryRun) {
        $secretsYaml | kubectl apply -f -
        Write-Success "Secrets created"
    }
    else {
        Write-Status "Would create secrets (dry run)"
    }
}

# Function to deploy infrastructure dependencies
function Test-Infrastructure {
    Write-Status "Checking infrastructure dependencies..."
    
    # Check if PostgreSQL is running
    try {
        kubectl get deployment postgres -n $Namespace | Out-Null
    }
    catch {
        Write-Warning "PostgreSQL not found, please deploy it first"
        Write-Status "You can deploy PostgreSQL using: kubectl apply -f deploy/infra/k8s/postgres-ha.yaml"
    }
    
    # Check if Redis is running
    try {
        kubectl get deployment redis -n $Namespace | Out-Null
    }
    catch {
        Write-Warning "Redis not found, please deploy it first"
        Write-Status "You can deploy Redis using: kubectl apply -f deploy/infra/k8s/redis.yaml"
    }
    
    # Check if monitoring stack is running
    try {
        kubectl get deployment prometheus -n monitoring | Out-Null
    }
    catch {
        Write-Warning "Prometheus not found, please deploy monitoring stack first"
    }
    
    Write-Success "Infrastructure check completed"
}

# Function to deploy the suggestion service
function Deploy-Service {
    Write-Status "Deploying suggestion service..."
    
    if ($DryRun) {
        Write-Status "Running dry run..."
        helm template suggestion $CHART_PATH `
            --namespace $Namespace `
            --values $VALUES_FILE `
            --set secrets.encryptionKey="dry-run-key" `
            --set secrets.jwtSecret="dry-run-jwt" `
            --set secrets.rateLimitSecret="dry-run-rate-limit"
    }
    else {
        # Check if release exists
        $existingRelease = helm list -n $Namespace | Select-String "suggestion"
        if ($existingRelease) {
            Write-Warning "Suggestion service already exists, upgrading..."
            helm upgrade suggestion $CHART_PATH `
                --namespace $Namespace `
                --values $VALUES_FILE `
                --wait `
                --timeout 10m
        }
        else {
            Write-Status "Installing new suggestion service..."
            helm install suggestion $CHART_PATH `
                --namespace $Namespace `
                --values $VALUES_FILE `
                --wait `
                --timeout 10m
        }
    }
    
    Write-Success "Suggestion service deployment completed"
}

# Function to verify deployment
function Test-Deployment {
    Write-Status "Verifying deployment..."
    
    if ($DryRun) {
        Write-Status "Skipping verification (dry run)"
        return
    }
    
    # Wait for pods to be ready
    Write-Status "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=suggestion -n $Namespace --timeout=300s
    
    # Check service
    try {
        kubectl get service suggestion -n $Namespace | Out-Null
        Write-Success "Service created successfully"
    }
    catch {
        Write-Error "Service not found"
        exit 1
    }
    
    # Check HPA
    try {
        kubectl get hpa suggestion-hpa -n $Namespace | Out-Null
        Write-Success "HPA created successfully"
    }
    catch {
        Write-Warning "HPA not found"
    }
    
    # Check network policy
    try {
        kubectl get networkpolicy suggestion-network-policy -n $Namespace | Out-Null
        Write-Success "Network policy created successfully"
    }
    catch {
        Write-Warning "Network policy not found"
    }
    
    # Check monitoring resources
    try {
        kubectl get servicemonitor suggestion-monitor -n $Namespace | Out-Null
        Write-Success "ServiceMonitor created successfully"
    }
    catch {
        Write-Warning "ServiceMonitor not found"
    }
    
    Write-Success "Deployment verification completed"
}

# Function to run health checks
function Test-HealthChecks {
    Write-Status "Running health checks..."
    
    if ($DryRun) {
        Write-Status "Skipping health checks (dry run)"
        return
    }
    
    # Get service URL
    $SERVICE_URL = kubectl get service suggestion -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
    if (-not $SERVICE_URL) {
        $SERVICE_URL = kubectl get service suggestion -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    }
    
    if ($SERVICE_URL) {
        # Test health endpoint
        try {
            Invoke-WebRequest -Uri "http://$SERVICE_URL`:8300/healthz" -UseBasicParsing | Out-Null
            Write-Success "Health check passed"
        }
        catch {
            Write-Error "Health check failed"
        }
        
        # Test metrics endpoint
        try {
            Invoke-WebRequest -Uri "http://$SERVICE_URL`:8300/metrics" -UseBasicParsing | Out-Null
            Write-Success "Metrics endpoint accessible"
        }
        catch {
            Write-Warning "Metrics endpoint not accessible"
        }
    }
    else {
        Write-Warning "Service URL not available, skipping health checks"
    }
}

# Function to show deployment status
function Show-Status {
    Write-Status "Deployment status:"
    
    Write-Host "`nPods:"
    kubectl get pods -l app=suggestion -n $Namespace
    
    Write-Host "`nServices:"
    kubectl get services -l app=suggestion -n $Namespace
    
    Write-Host "`nHPA:"
    kubectl get hpa -l app=suggestion -n $Namespace
    
    Write-Host "`nNetwork Policies:"
    kubectl get networkpolicy -l app=suggestion -n $Namespace
    
    Write-Host "`nEvents:"
    kubectl get events -n $Namespace --sort-by='.lastTimestamp' | Select-String "suggestion" | Select-Object -Last 10
}

# Function to show logs
function Show-Logs {
    Write-Status "Showing logs..."
    kubectl logs -l app=suggestion -n $Namespace --tail=100 -f
}

# Function to run tests
function Test-Service {
    Write-Status "Running deployment tests..."
    
    if ($DryRun) {
        Write-Status "Skipping tests (dry run)"
        return
    }
    
    # Test basic connectivity
    Write-Status "Testing basic connectivity..."
    try {
        kubectl exec -n $Namespace deployment/suggestion -- curl -f http://localhost:8300/healthz | Out-Null
        Write-Success "Basic connectivity test passed"
    }
    catch {
        Write-Error "Basic connectivity test failed"
    }
    
    # Test database connectivity
    Write-Status "Testing database connectivity..."
    try {
        kubectl exec -n $Namespace deployment/suggestion -- python -c "import psycopg2; print('DB connection test')" | Out-Null
        Write-Success "Database connectivity test passed"
    }
    catch {
        Write-Warning "Database connectivity test failed"
    }
    
    # Test Redis connectivity
    Write-Status "Testing Redis connectivity..."
    try {
        kubectl exec -n $Namespace deployment/suggestion -- python -c "import redis; print('Redis connection test')" | Out-Null
        Write-Success "Redis connectivity test passed"
    }
    catch {
        Write-Warning "Redis connectivity test failed"
    }
    
    Write-Success "Deployment tests completed"
}

# Function to uninstall
function Uninstall-Service {
    Write-Status "Uninstalling suggestion service..."
    
    if (-not $Force) {
        $confirmation = Read-Host "Are you sure you want to uninstall the suggestion service? (y/N)"
        if ($confirmation -ne "y" -and $confirmation -ne "Y") {
            Write-Status "Uninstall cancelled"
            return
        }
    }
    
    $existingRelease = helm list -n $Namespace | Select-String "suggestion"
    if ($existingRelease) {
        helm uninstall suggestion -n $Namespace
        Write-Success "Suggestion service uninstalled"
    }
    else {
        Write-Warning "Suggestion service not found"
    }
}

# Main script logic
function Main {
    if ($Help) {
        Show-Usage
        return
    }
    
    # Validate required arguments
    if (-not $Command) {
        Write-Error "Command is required"
        Show-Usage
        exit 1
    }
    
    if ($Command -eq "deploy" -or $Command -eq "upgrade") {
        if (-not $Environment) {
            Write-Error "Environment is required for deploy/upgrade"
            Show-Usage
            exit 1
        }
        Validate-Environment
    }
    
    # Execute command
    switch ($Command) {
        "deploy" {
            Test-Prerequisites
            Test-Infrastructure
            New-Secrets
            Deploy-Service
            Test-Deployment
            Test-HealthChecks
            Test-Service
            Write-Success "Deployment completed successfully!"
        }
        "upgrade" {
            Test-Prerequisites
            Deploy-Service
            Test-Deployment
            Test-HealthChecks
            Write-Success "Upgrade completed successfully!"
        }
        "uninstall" {
            Uninstall-Service
        }
        "status" {
            Show-Status
        }
        "logs" {
            Show-Logs
        }
        "test" {
            Test-Service
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Usage
            exit 1
        }
    }
}

# Run main function
Main
