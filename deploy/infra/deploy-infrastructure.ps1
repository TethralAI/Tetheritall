param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "upgrade", "uninstall", "status", "logs", "test")]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "iot",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipMonitoring,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipIngress,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipCertManager,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$White = "White"

# Print functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

# Usage function
function Show-Usage {
    Write-Host "Usage: $PSCommandPath [COMMAND] [OPTIONS]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  deploy     - Deploy all infrastructure components"
    Write-Host "  upgrade    - Upgrade existing infrastructure"
    Write-Host "  uninstall  - Remove all infrastructure components"
    Write-Host "  status     - Show deployment status"
    Write-Host "  logs       - Show logs for all components"
    Write-Host "  test       - Run infrastructure tests"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Namespace NAMESPACE  - Kubernetes namespace (default: iot)"
    Write-Host "  -Environment ENV      - Environment (dev/staging/prod, default: dev)"
    Write-Host "  -SkipMonitoring       - Skip monitoring stack deployment"
    Write-Host "  -SkipIngress          - Skip ingress controller deployment"
    Write-Host "  -SkipCertManager      - Skip cert-manager deployment"
    Write-Host "  -DryRun               - Show what would be deployed without applying"
    Write-Host "  -Help                 - Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  $PSCommandPath deploy -Environment prod"
    Write-Host "  $PSCommandPath status"
    Write-Host "  $PSCommandPath uninstall"
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Validate command
if (-not $Command) {
    Write-Error "No command specified"
    Show-Usage
    exit 1
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if kubectl is installed
    try {
        $null = Get-Command kubectl -ErrorAction Stop
    }
    catch {
        Write-Error "kubectl is not installed. Please install kubectl first."
        exit 1
    }
    
    # Check if kubectl can connect to cluster
    try {
        $null = kubectl cluster-info 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Cannot connect to cluster"
        }
    }
    catch {
        Write-Error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    }
    
    # Check if helm is installed
    try {
        $null = Get-Command helm -ErrorAction Stop
    }
    catch {
        Write-Error "helm is not installed. Please install helm first."
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to create namespaces
function New-Namespaces {
    Write-Info "Creating namespaces..."
    
    $namespaces = @($Namespace, "monitoring", "ingress-nginx", "cert-manager", "chaos-testing")
    
    foreach ($ns in $namespaces) {
        $exists = kubectl get namespace $ns 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Namespace $ns already exists"
        }
        else {
            if ($DryRun) {
                Write-Info "Would create namespace: $ns"
            }
            else {
                kubectl create namespace $ns
                Write-Success "Created namespace: $ns"
            }
        }
    }
}

# Function to deploy complete infrastructure
function Deploy-CompleteInfrastructure {
    Write-Info "Deploying complete infrastructure..."
    
    $manifestFile = "deploy/infra/k8s/complete-infrastructure.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Infrastructure manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply infrastructure manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied infrastructure manifest"
    }
}

# Function to deploy PostgreSQL
function Deploy-PostgreSQL {
    Write-Info "Deploying PostgreSQL..."
    
    $manifestFile = "deploy/infra/k8s/postgres-ha.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "PostgreSQL manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply PostgreSQL manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied PostgreSQL manifest"
    }
}

# Function to deploy monitoring stack
function Deploy-Monitoring {
    if ($SkipMonitoring) {
        Write-Info "Skipping monitoring stack deployment"
        return
    }
    
    Write-Info "Deploying monitoring stack..."
    
    $manifestFile = "deploy/infra/k8s/monitoring-stack.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Monitoring manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply monitoring manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied monitoring manifest"
    }
}

# Function to deploy ingress controller
function Deploy-Ingress {
    if ($SkipIngress) {
        Write-Info "Skipping ingress controller deployment"
        return
    }
    
    Write-Info "Deploying Nginx Ingress Controller..."
    
    $manifestFile = "deploy/infra/k8s/ingress-controller.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Ingress manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply ingress manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied ingress manifest"
    }
}

# Function to deploy cert-manager
function Deploy-CertManager {
    if ($SkipCertManager) {
        Write-Info "Skipping cert-manager deployment"
        return
    }
    
    Write-Info "Deploying cert-manager..."
    
    $manifestFile = "deploy/infra/k8s/cert-manager.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Cert-manager manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply cert-manager manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied cert-manager manifest"
    }
}

# Function to deploy storage classes
function Deploy-Storage {
    Write-Info "Deploying storage classes..."
    
    $manifestFile = "deploy/infra/k8s/storage-class.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Storage manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply storage manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied storage manifest"
    }
}

# Function to deploy load balancers
function Deploy-LoadBalancers {
    Write-Info "Deploying load balancers..."
    
    $manifestFile = "deploy/infra/k8s/load-balancer.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Load balancer manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply load balancer manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied load balancer manifest"
    }
}

# Function to deploy backup jobs
function Deploy-BackupJobs {
    Write-Info "Deploying backup jobs..."
    
    $manifestFile = "deploy/infra/k8s/backup-cronjob.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Backup manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply backup manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied backup manifest"
    }
}

# Function to deploy chaos engineering
function Deploy-ChaosEngineering {
    Write-Info "Deploying chaos engineering components..."
    
    $manifestFile = "deploy/infra/k8s/chaos-engineering.yaml"
    
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Chaos engineering manifest not found: $manifestFile"
        exit 1
    }
    
    if ($DryRun) {
        Write-Info "Would apply chaos engineering manifest (dry run)"
        kubectl apply -f $manifestFile --dry-run=client
    }
    else {
        kubectl apply -f $manifestFile
        Write-Success "Applied chaos engineering manifest"
    }
}

# Function to wait for deployments
function Wait-Deployments {
    if ($DryRun) {
        Write-Info "Skipping deployment wait (dry run)"
        return
    }
    
    Write-Info "Waiting for deployments to be ready..."
    
    # Wait for PostgreSQL
    Write-Info "Waiting for PostgreSQL..."
    kubectl wait --for=condition=available --timeout=300s deployment/postgres -n $Namespace
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "PostgreSQL deployment not ready within timeout"
    }
    
    # Wait for Redis
    Write-Info "Waiting for Redis..."
    kubectl wait --for=condition=available --timeout=300s statefulset/redis -n $Namespace
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Redis deployment not ready within timeout"
    }
    
    # Wait for monitoring components
    if (-not $SkipMonitoring) {
        Write-Info "Waiting for monitoring components..."
        kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Prometheus deployment not ready within timeout"
        }
        kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Grafana deployment not ready within timeout"
        }
    }
    
    # Wait for ingress controller
    if (-not $SkipIngress) {
        Write-Info "Waiting for ingress controller..."
        kubectl wait --for=condition=available --timeout=300s deployment/nginx-ingress-controller -n ingress-nginx
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Ingress controller deployment not ready within timeout"
        }
    }
    
    Write-Success "Deployment wait completed"
}

# Function to verify deployment
function Test-Deployment {
    if ($DryRun) {
        Write-Info "Skipping deployment verification (dry run)"
        return
    }
    
    Write-Info "Verifying deployment..."
    
    # Check if all pods are running
    $failedPods = kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded | Select-String -NotMatch "NAMESPACE" | Measure-Object | Select-Object -ExpandProperty Count
    
    if ($failedPods -gt 0) {
        Write-Warning "Found $failedPods pods not in Running state"
        kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded
    }
    else {
        Write-Success "All pods are running"
    }
    
    # Check services
    Write-Info "Checking services..."
    kubectl get services -n $Namespace
    
    # Check persistent volumes
    Write-Info "Checking persistent volumes..."
    kubectl get pv,pvc -n $Namespace
}

# Function to show status
function Show-Status {
    Write-Info "Infrastructure deployment status:"
    Write-Host ""
    
    # Show namespaces
    Write-Info "Namespaces:"
    kubectl get namespaces | Select-String -Pattern "(iot|monitoring|ingress-nginx|cert-manager|chaos-testing)" | Write-Host
    Write-Host ""
    
    # Show deployments
    Write-Info "Deployments:"
    kubectl get deployments --all-namespaces | Select-String -Pattern "(iot|monitoring|ingress-nginx|cert-manager)" | Write-Host
    Write-Host ""
    
    # Show services
    Write-Info "Services:"
    kubectl get services --all-namespaces | Select-String -Pattern "(iot|monitoring|ingress-nginx|cert-manager)" | Write-Host
    Write-Host ""
    
    # Show persistent volumes
    Write-Info "Persistent Volumes:"
    kubectl get pv,pvc --all-namespaces | Select-String -Pattern "(iot|monitoring)" | Write-Host
    Write-Host ""
    
    # Show pods status
    Write-Info "Pod Status:"
    kubectl get pods --all-namespaces | Select-String -Pattern "(iot|monitoring|ingress-nginx|cert-manager)" | Write-Host
}

# Function to show logs
function Show-Logs {
    Write-Info "Showing logs for infrastructure components..."
    
    # PostgreSQL logs
    Write-Info "PostgreSQL logs:"
    kubectl logs -n $Namespace -l app=postgres --tail=50 2>$null | Write-Host
    Write-Host ""
    
    # Redis logs
    Write-Info "Redis logs:"
    kubectl logs -n $Namespace -l app=redis --tail=50 2>$null | Write-Host
    Write-Host ""
    
    # Monitoring logs
    if (-not $SkipMonitoring) {
        Write-Info "Prometheus logs:"
        kubectl logs -n monitoring -l app=prometheus --tail=50 2>$null | Write-Host
        Write-Host ""
        
        Write-Info "Grafana logs:"
        kubectl logs -n monitoring -l app=grafana --tail=50 2>$null | Write-Host
        Write-Host ""
    }
    
    # Ingress logs
    if (-not $SkipIngress) {
        Write-Info "Ingress controller logs:"
        kubectl logs -n ingress-nginx -l app=nginx-ingress --tail=50 2>$null | Write-Host
        Write-Host ""
    }
}

# Function to run tests
function Test-Infrastructure {
    Write-Info "Running infrastructure tests..."
    
    # Test database connectivity
    Write-Info "Testing PostgreSQL connectivity..."
    kubectl exec -n $Namespace deployment/postgres -- pg_isready -h localhost
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PostgreSQL connectivity test failed"
        return 1
    }
    
    # Test Redis connectivity
    Write-Info "Testing Redis connectivity..."
    kubectl exec -n $Namespace statefulset/redis -- redis-cli ping
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Redis connectivity test failed"
        return 1
    }
    
    # Test monitoring endpoints
    if (-not $SkipMonitoring) {
        Write-Info "Testing monitoring endpoints..."
        kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/-/healthy
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Prometheus health check failed"
            return 1
        }
    }
    
    Write-Success "All infrastructure tests passed"
}

# Function to uninstall
function Uninstall-Infrastructure {
    Write-Warning "This will remove ALL infrastructure components. Are you sure? (y/N)"
    $response = Read-Host
    if ($response -notmatch "^[Yy]$") {
        Write-Info "Uninstall cancelled"
        exit 0
    }
    
    Write-Info "Uninstalling infrastructure components..."
    
    # Delete chaos engineering
    Write-Info "Removing chaos engineering components..."
    kubectl delete -f deploy/infra/k8s/chaos-engineering.yaml --ignore-not-found=true 2>$null
    
    # Delete backup jobs
    Write-Info "Removing backup jobs..."
    kubectl delete -f deploy/infra/k8s/backup-cronjob.yaml --ignore-not-found=true 2>$null
    
    # Delete load balancers
    Write-Info "Removing load balancers..."
    kubectl delete -f deploy/infra/k8s/load-balancer.yaml --ignore-not-found=true 2>$null
    
    # Delete storage classes
    Write-Info "Removing storage classes..."
    kubectl delete -f deploy/infra/k8s/storage-class.yaml --ignore-not-found=true 2>$null
    
    # Delete cert-manager
    if (-not $SkipCertManager) {
        Write-Info "Removing cert-manager..."
        kubectl delete -f deploy/infra/k8s/cert-manager.yaml --ignore-not-found=true 2>$null
    }
    
    # Delete ingress controller
    if (-not $SkipIngress) {
        Write-Info "Removing ingress controller..."
        kubectl delete -f deploy/infra/k8s/ingress-controller.yaml --ignore-not-found=true 2>$null
    }
    
    # Delete monitoring stack
    if (-not $SkipMonitoring) {
        Write-Info "Removing monitoring stack..."
        kubectl delete -f deploy/infra/k8s/monitoring-stack.yaml --ignore-not-found=true 2>$null
    }
    
    # Delete PostgreSQL
    Write-Info "Removing PostgreSQL..."
    kubectl delete -f deploy/infra/k8s/postgres-ha.yaml --ignore-not-found=true 2>$null
    
    # Delete complete infrastructure
    Write-Info "Removing complete infrastructure..."
    kubectl delete -f deploy/infra/k8s/complete-infrastructure.yaml --ignore-not-found=true 2>$null
    
    # Delete namespaces
    Write-Info "Removing namespaces..."
    kubectl delete namespace chaos-testing --ignore-not-found=true 2>$null
    kubectl delete namespace cert-manager --ignore-not-found=true 2>$null
    kubectl delete namespace ingress-nginx --ignore-not-found=true 2>$null
    kubectl delete namespace monitoring --ignore-not-found=true 2>$null
    kubectl delete namespace $Namespace --ignore-not-found=true 2>$null
    
    Write-Success "Infrastructure uninstalled successfully"
}

# Main deployment function
function Deploy-Infrastructure {
    Write-Info "Starting infrastructure deployment..."
    Write-Info "Environment: $Environment"
    Write-Info "Namespace: $Namespace"
    Write-Info "Dry run: $DryRun"
    
    Test-Prerequisites
    New-Namespaces
    Deploy-CompleteInfrastructure
    Deploy-PostgreSQL
    Deploy-Monitoring
    Deploy-Ingress
    Deploy-CertManager
    Deploy-Storage
    Deploy-LoadBalancers
    Deploy-BackupJobs
    Deploy-ChaosEngineering
    Wait-Deployments
    Test-Deployment
    
    Write-Success "Infrastructure deployment completed successfully!"
    
    if (-not $DryRun) {
        Write-Host ""
        Write-Info "Next steps:"
        Write-Host "1. Verify all components are running: $PSCommandPath status"
        Write-Host "2. Check logs if needed: $PSCommandPath logs"
        Write-Host "3. Run tests: $PSCommandPath test"
        Write-Host "4. Deploy the suggestion service: .\deploy\suggestion\deploy.ps1 deploy"
    }
}

# Main script logic
switch ($Command) {
    "deploy" {
        Deploy-Infrastructure
    }
    "upgrade" {
        Write-Info "Upgrading infrastructure..."
        Deploy-Infrastructure
    }
    "uninstall" {
        Uninstall-Infrastructure
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "test" {
        Test-Infrastructure
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Usage
        exit 1
    }
}
