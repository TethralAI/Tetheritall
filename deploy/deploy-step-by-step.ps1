#!/usr/bin/env pwsh

Write-Host "🚀 Tethral Deployment - Step by Step" -ForegroundColor Green

# Step 1: Check prerequisites
Write-Host "`nStep 1: Checking prerequisites..." -ForegroundColor Blue

try {
    aws --version
    Write-Host "✅ AWS CLI is installed" -ForegroundColor Green
}
catch {
    Write-Host "❌ AWS CLI is not installed" -ForegroundColor Red
    exit 1
}

try {
    kubectl version --client
    Write-Host "✅ kubectl is installed" -ForegroundColor Green
}
catch {
    Write-Host "❌ kubectl is not installed" -ForegroundColor Red
    exit 1
}

try {
    docker --version
    Write-Host "✅ Docker is installed" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not installed" -ForegroundColor Red
    exit 1
}

# Step 2: Check AWS credentials
Write-Host "`nStep 2: Checking AWS credentials..." -ForegroundColor Blue
if (Test-Path "$env:USERPROFILE\.aws\credentials") {
    Write-Host "✅ AWS credentials found" -ForegroundColor Green
}
else {
    Write-Host "❌ AWS credentials not found. Please run: aws configure" -ForegroundColor Red
    exit 1
}

# Step 3: Build Docker image
Write-Host "`nStep 3: Building Docker image..." -ForegroundColor Blue
Set-Location "iot-api-discovery"
docker build -t "tethral/iot-api-discovery:latest" .
Set-Location ".."
Write-Host "✅ Docker image built successfully" -ForegroundColor Green

# Step 4: Initialize Terraform
Write-Host "`nStep 4: Initializing Terraform..." -ForegroundColor Blue
Set-Location "deploy/terraform"
terraform init
Write-Host "✅ Terraform initialized" -ForegroundColor Green

# Step 5: Plan Terraform deployment
Write-Host "`nStep 5: Planning Terraform deployment..." -ForegroundColor Blue
terraform plan -var="environment=dev" -var="region=us-east-1"
Write-Host "✅ Terraform plan completed" -ForegroundColor Green

# Step 6: Apply Terraform (commented out for safety)
Write-Host "`nStep 6: Terraform apply (commented out for safety)" -ForegroundColor Blue
Write-Host "To deploy infrastructure, uncomment the following line:" -ForegroundColor Yellow
Write-Host "# terraform apply -var='environment=dev' -var='region=us-east-1' -auto-approve" -ForegroundColor Cyan

# Step 7: Configure kubectl
Write-Host "`nStep 7: Configuring kubectl..." -ForegroundColor Blue
Set-Location ".."
aws eks update-kubeconfig --region us-east-1 --name "tethral-dev-cluster"
kubectl create namespace tethral --dry-run=client -o yaml | kubectl apply -f -
Write-Host "✅ kubectl configured" -ForegroundColor Green

# Step 8: Deploy applications
Write-Host "`nStep 8: Deploying applications..." -ForegroundColor Blue
Set-Location "k8s"
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml
kubectl apply -f iot-api-discovery.yaml
Write-Host "✅ Applications deployed" -ForegroundColor Green

# Step 9: Check deployment status
Write-Host "`nStep 9: Checking deployment status..." -ForegroundColor Blue
kubectl get pods -n tethral
kubectl get services -n tethral

Write-Host "`n🎉 Deployment completed!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Uncomment terraform apply line to deploy infrastructure" -ForegroundColor Yellow
Write-Host "2. Update secrets.yaml with real values" -ForegroundColor Yellow
Write-Host "3. Test API endpoints" -ForegroundColor Yellow
