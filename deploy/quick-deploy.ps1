# Quick Deployment Script - Bypasses kubectl authentication issues
# Uses AWS CLI and direct kubectl commands

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "status", "cleanup")]
    [string]$Command = "deploy",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev"
)

Write-Host "🚀 Quick Deployment Script for Tethral Suggestion Engine" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

# Function to print colored output
function Write-Info {
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

# Function to check AWS credentials
function Test-AWSCredentials {
    Write-Info "Checking AWS credentials..."
    try {
        $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
        Write-Success "AWS credentials valid for user: $($identity.Arn)"
        return $true
    }
    catch {
        Write-Error "AWS credentials not valid"
        return $false
    }
}

# Function to check EKS cluster
function Test-EKSCluster {
    Write-Info "Checking EKS cluster..."
    try {
        $cluster = aws eks describe-cluster --name tethral-cluster --region us-east-1 --output json | ConvertFrom-Json
        Write-Success "EKS cluster found: $($cluster.cluster.name)"
        Write-Info "Cluster status: $($cluster.cluster.status)"
        Write-Info "Kubernetes version: $($cluster.cluster.version)"
        return $true
    }
    catch {
        Write-Error "Cannot access EKS cluster"
        return $false
    }
}

# Function to deploy using AWS Console approach
function Deploy-ViaAWSConsole {
    Write-Info "Setting up deployment for AWS Console..."
    
    # Create deployment manifests
    Write-Info "Creating deployment manifests..."
    
    # Create namespace
    $namespaceYaml = @"
apiVersion: v1
kind: Namespace
metadata:
  name: iot
  labels:
    name: iot
"@
    
    $namespaceYaml | Out-File -FilePath "deploy/namespace.yaml" -Encoding UTF8
    
    # Create basic PostgreSQL deployment
    $postgresYaml = @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: iot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "tethral"
        - name: POSTGRES_USER
          value: "tethral"
        - name: POSTGRES_PASSWORD
          value: "tethral123"
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: iot
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
"@
    
    $postgresYaml | Out-File -FilePath "deploy/postgres.yaml" -Encoding UTF8
    
    # Create basic Redis deployment
    $redisYaml = @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: iot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
      volumes:
      - name: redis-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: iot
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
"@
    
    $redisYaml | Out-File -FilePath "deploy/redis.yaml" -Encoding UTF8
    
    Write-Success "Deployment manifests created!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "1. Go to AWS Console → EKS → tethral-cluster"
    Write-Host "2. Click 'Launch kubectl' button"
    Write-Host "3. In the web terminal, run these commands:"
    Write-Host ""
    Write-Host "   kubectl apply -f deploy/namespace.yaml"
    Write-Host "   kubectl apply -f deploy/postgres.yaml"
    Write-Host "   kubectl apply -f deploy/redis.yaml"
    Write-Host "   kubectl get pods -n iot"
    Write-Host ""
    Write-Info "Or wait for kubectl authentication to work and run:"
    Write-Host "   .\deploy\infra\deploy-infrastructure.ps1 -Command deploy -Environment dev"
}

# Function to show status
function Show-Status {
    Write-Info "Checking deployment status..."
    
    # Check if manifests exist
    if (Test-Path "deploy/namespace.yaml") {
        Write-Success "Deployment manifests found"
    } else {
        Write-Warning "Deployment manifests not found"
    }
    
    # Check AWS and EKS status
    Test-AWSCredentials
    Test-EKSCluster
    
    Write-Host ""
    Write-Info "To check cluster status, use AWS Console:"
    Write-Host "AWS Console → EKS → tethral-cluster → Launch kubectl"
}

# Function to cleanup
function Cleanup-Deployment {
    Write-Info "Cleaning up deployment files..."
    
    if (Test-Path "deploy/namespace.yaml") {
        Remove-Item "deploy/namespace.yaml"
        Write-Success "Removed namespace.yaml"
    }
    
    if (Test-Path "deploy/postgres.yaml") {
        Remove-Item "deploy/postgres.yaml"
        Write-Success "Removed postgres.yaml"
    }
    
    if (Test-Path "deploy/redis.yaml") {
        Remove-Item "deploy/redis.yaml"
        Write-Success "Removed redis.yaml"
    }
    
    Write-Success "Cleanup completed"
}

# Main script logic
switch ($Command) {
    "deploy" {
        Write-Info "Starting quick deployment..."
        if (Test-AWSCredentials) {
            if (Test-EKSCluster) {
                Deploy-ViaAWSConsole
            } else {
                Write-Error "Cannot access EKS cluster. Please check permissions."
            }
        } else {
            Write-Error "AWS credentials not valid. Please configure AWS CLI."
        }
    }
    "status" {
        Show-Status
    }
    "cleanup" {
        Cleanup-Deployment
    }
    default {
        Write-Error "Unknown command: $Command"
        Write-Host "Valid commands: deploy, status, cleanup"
    }
}
