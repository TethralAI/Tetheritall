#!/usr/bin/env pwsh

# Tethral Deployment Script
# This script deploys the complete Tethral infrastructure and applications

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$SkipInfrastructure,
    [switch]$SkipApplications,
    [switch]$DryRun
)

Write-Host "🚀 Starting Tethral Deployment..." -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow

# Check prerequisites
function Test-Prerequisites {
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Blue
    
    $prerequisites = @{
        "AWS CLI" = "aws --version"
        "kubectl" = "kubectl version --client"
        "docker" = "docker --version"
    }
    
    foreach ($tool in $prerequisites.GetEnumerator()) {
        try {
            $null = Invoke-Expression $tool.Value
            Write-Host "✅ $($tool.Key) is installed" -ForegroundColor Green
        }
        catch {
            Write-Host "❌ $($tool.Key) is not installed" -ForegroundColor Red
            return $false
        }
    }
    
    return $true
}

# Configure AWS credentials
function Set-AWSCredentials {
    Write-Host "🔐 Configuring AWS credentials..." -ForegroundColor Blue
    
    if (-not (Test-Path "$env:USERPROFILE\.aws\credentials")) {
        Write-Host "⚠️  AWS credentials not found. Please configure them:" -ForegroundColor Yellow
        Write-Host "   aws configure" -ForegroundColor Cyan
        return $false
    }
    
    Write-Host "✅ AWS credentials configured" -ForegroundColor Green
    return $true
}

# Deploy Terraform infrastructure
function Start-InfrastructureDeployment {
    if ($SkipInfrastructure) {
        Write-Host "⏭️  Skipping infrastructure deployment" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "🏗️  Deploying Terraform infrastructure..." -ForegroundColor Blue
    
    Push-Location "deploy/terraform"
    
    try {
        # Initialize Terraform
        Write-Host "📦 Initializing Terraform..." -ForegroundColor Cyan
        terraform init
        
        # Plan deployment
        Write-Host "📋 Planning deployment..." -ForegroundColor Cyan
        terraform plan -var="environment=$Environment" -var="region=$Region"
        
        if ($DryRun) {
            Write-Host "🔍 Dry run completed" -ForegroundColor Yellow
            return $true
        }
        
        # Apply deployment
        Write-Host "🚀 Applying infrastructure..." -ForegroundColor Cyan
        terraform apply -var="environment=$Environment" -var="region=$Region" -auto-approve
        
        # Get outputs
        $outputs = terraform output -json
        $global:InfrastructureOutputs = $outputs | ConvertFrom-Json
        
        Write-Host "✅ Infrastructure deployed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Infrastructure deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    finally {
        Pop-Location
    }
}

# Build and push Docker images
function Start-ImageBuild {
    Write-Host "🐳 Building Docker images..." -ForegroundColor Blue
    
    $images = @(
        @{
            Name = "iot-api-discovery"
            Path = "iot-api-discovery"
            Tag = "latest"
        }
    )
    
    foreach ($image in $images) {
        Write-Host "📦 Building $($image.Name)..." -ForegroundColor Cyan
        Push-Location $image.Path
        
        try {
            docker build -t "tethral/$($image.Name):$($image.Tag)" .
            
            if (-not $DryRun) {
                # In real deployment, push to ECR
                # aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $global:InfrastructureOutputs.ecr_repository_url.value
                # docker tag "tethral/$($image.Name):$($image.Tag)" "$($global:InfrastructureOutputs.ecr_repository_url.value):$($image.Tag)"
                # docker push "$($global:InfrastructureOutputs.ecr_repository_url.value):$($image.Tag)"
                Write-Host "✅ Image $($image.Name) built successfully" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "❌ Failed to build image $($image.Name): $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
        finally {
            Pop-Location
        }
    }
    
    return $true
}

# Configure kubectl for EKS
function Set-KubernetesConfiguration {
    Write-Host "⚙️  Configuring Kubernetes..." -ForegroundColor Blue
    
    try {
        # Update kubeconfig for EKS cluster
        aws eks update-kubeconfig --region $Region --name "tethral-$Environment-cluster"
        
        # Create namespace
        kubectl create namespace tethral --dry-run=client -o yaml | kubectl apply -f -
        
        Write-Host "✅ Kubernetes configured successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Kubernetes configuration failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Deploy applications
function Start-ApplicationDeployment {
    if ($SkipApplications) {
        Write-Host "⏭️  Skipping application deployment" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "🚀 Deploying applications..." -ForegroundColor Blue
    
    Push-Location "deploy/k8s"
    
    try {
        # Apply secrets first
        Write-Host "🔐 Applying secrets..." -ForegroundColor Cyan
        kubectl apply -f secrets.yaml
        
        # Apply database and Redis
        Write-Host "🗄️  Deploying database and Redis..." -ForegroundColor Cyan
        kubectl apply -f postgres.yaml
        kubectl apply -f redis.yaml
        
        # Wait for database to be ready
        Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Cyan
        kubectl wait --for=condition=ready pod -l app=postgres -n tethral --timeout=300s
        
        # Apply API service
        Write-Host "🔌 Deploying API service..." -ForegroundColor Cyan
        kubectl apply -f iot-api-discovery.yaml
        
        # Wait for API service to be ready
        Write-Host "⏳ Waiting for API service to be ready..." -ForegroundColor Cyan
        kubectl wait --for=condition=ready pod -l app=iot-api-discovery -n tethral --timeout=300s
        
        Write-Host "✅ Applications deployed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Application deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    finally {
        Pop-Location
    }
}

# Test deployment
function Test-Deployment {
    Write-Host "🧪 Testing deployment..." -ForegroundColor Blue
    
    try {
        # Get API service URL
        $apiService = kubectl get service iot-api-discovery -n tethral -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
        
        if ($apiService) {
            Write-Host "🌐 API Service URL: http://$apiService" -ForegroundColor Green
            
            # Test health endpoint
            $healthResponse = Invoke-RestMethod -Uri "http://$apiService/api/health" -Method Get
            Write-Host "✅ Health check passed: $($healthResponse.status)" -ForegroundColor Green
            
            # Test device discovery endpoint
            $discoveryResponse = Invoke-RestMethod -Uri "http://$apiService/api/discovery/devices" -Method Get
            Write-Host "✅ Device discovery working: Found $($discoveryResponse.total_count) devices" -ForegroundColor Green
        }
        else {
            Write-Host "⚠️  API service not accessible via LoadBalancer" -ForegroundColor Yellow
        }
        
        return $true
    }
    catch {
        Write-Host "❌ Deployment test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main deployment flow
function Main {
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Host "❌ Prerequisites not met. Please install required tools." -ForegroundColor Red
        exit 1
    }
    
    # Configure AWS
    if (-not (Set-AWSCredentials)) {
        Write-Host "❌ AWS credentials not configured." -ForegroundColor Red
        exit 1
    }
    
    # Deploy infrastructure
    if (-not (Start-InfrastructureDeployment)) {
        Write-Host "❌ Infrastructure deployment failed." -ForegroundColor Red
        exit 1
    }
    
    # Build images
    if (-not (Start-ImageBuild)) {
        Write-Host "❌ Image building failed." -ForegroundColor Red
        exit 1
    }
    
    # Configure Kubernetes
    if (-not (Set-KubernetesConfiguration)) {
        Write-Host "❌ Kubernetes configuration failed." -ForegroundColor Red
        exit 1
    }
    
    # Deploy applications
    if (-not (Start-ApplicationDeployment)) {
        Write-Host "❌ Application deployment failed." -ForegroundColor Red
        exit 1
    }
    
    # Test deployment
    if (-not (Test-Deployment)) {
        Write-Host "❌ Deployment test failed." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🎉 Tethral deployment completed successfully!" -ForegroundColor Green
    Write-Host "📊 Check the dashboard for monitoring and logs" -ForegroundColor Cyan
}

# Run main function
Main
