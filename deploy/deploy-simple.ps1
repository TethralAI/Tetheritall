#!/usr/bin/env pwsh

# Simple Tethral Deployment Script
param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$DryRun
)

Write-Host "🚀 Starting Tethral Deployment..." -ForegroundColor Green

# Check prerequisites
Write-Host "🔍 Checking prerequisites..." -ForegroundColor Blue

try {
    $awsVersion = aws --version
    Write-Host "✅ AWS CLI is installed: $awsVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ AWS CLI is not installed" -ForegroundColor Red
    exit 1
}

try {
    $kubectlVersion = kubectl version --client
    Write-Host "✅ kubectl is installed" -ForegroundColor Green
}
catch {
    Write-Host "❌ kubectl is not installed" -ForegroundColor Red
    exit 1
}

try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker is installed: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not installed" -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "🔐 Checking AWS credentials..." -ForegroundColor Blue
if (-not (Test-Path "$env:USERPROFILE\.aws\credentials")) {
    Write-Host "⚠️  AWS credentials not found. Please configure them:" -ForegroundColor Yellow
    Write-Host "   aws configure" -ForegroundColor Cyan
    exit 1
}
Write-Host "✅ AWS credentials found" -ForegroundColor Green

# Deploy Terraform infrastructure
if (-not $DryRun) {
    Write-Host "🏗️  Deploying Terraform infrastructure..." -ForegroundColor Blue
    
    Push-Location "deploy/terraform"
    
    try {
        Write-Host "📦 Initializing Terraform..." -ForegroundColor Cyan
        terraform init
        
        Write-Host "📋 Planning deployment..." -ForegroundColor Cyan
        terraform plan -var="environment=$Environment" -var="region=$Region"
        
        Write-Host "🚀 Applying infrastructure..." -ForegroundColor Cyan
        terraform apply -var="environment=$Environment" -var="region=$Region" -auto-approve
        
        Write-Host "✅ Infrastructure deployed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Infrastructure deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "🔍 Dry run - skipping infrastructure deployment" -ForegroundColor Yellow
}

# Build Docker image
Write-Host "🐳 Building Docker image..." -ForegroundColor Blue
Push-Location "iot-api-discovery"

try {
    docker build -t "tethral/iot-api-discovery:latest" .
    Write-Host "✅ Docker image built successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to build Docker image: $($_.Exception.Message)" -ForegroundColor Red
    Pop-Location
    exit 1
}
finally {
    Pop-Location
}

# Configure kubectl for EKS
Write-Host "⚙️  Configuring Kubernetes..." -ForegroundColor Blue
try {
    aws eks update-kubeconfig --region $Region --name "tethral-$Environment-cluster"
    kubectl create namespace tethral --dry-run=client -o yaml | kubectl apply -f -
    Write-Host "✅ Kubernetes configured successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ Kubernetes configuration failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Deploy applications
if (-not $DryRun) {
    Write-Host "🚀 Deploying applications..." -ForegroundColor Blue
    Push-Location "deploy/k8s"
    
    try {
        Write-Host "🔐 Applying secrets..." -ForegroundColor Cyan
        kubectl apply -f secrets.yaml
        
        Write-Host "🗄️  Deploying database and Redis..." -ForegroundColor Cyan
        kubectl apply -f postgres.yaml
        kubectl apply -f redis.yaml
        
        Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Cyan
        kubectl wait --for=condition=ready pod -l app=postgres -n tethral --timeout=300s
        
        Write-Host "🔌 Deploying API service..." -ForegroundColor Cyan
        kubectl apply -f iot-api-discovery.yaml
        
        Write-Host "⏳ Waiting for API service to be ready..." -ForegroundColor Cyan
        kubectl wait --for=condition=ready pod -l app=iot-api-discovery -n tethral --timeout=300s
        
        Write-Host "✅ Applications deployed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Application deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "🔍 Dry run - skipping application deployment" -ForegroundColor Yellow
}

Write-Host "🎉 Tethral deployment completed successfully!" -ForegroundColor Green
Write-Host "📊 Check the dashboard for monitoring and logs" -ForegroundColor Cyan
