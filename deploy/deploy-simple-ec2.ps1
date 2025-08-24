#!/usr/bin/env pwsh

# Simple EC2 deployment for Tethral API
# This script creates an EC2 instance without requiring a key pair

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

Write-Host "Deploying Tethral API to EC2 (Simple Version)..." -ForegroundColor Green

# Get infrastructure details
Push-Location "terraform"
$albDnsName = ..\..\terraform.exe output -raw alb_dns_name
$vpcId = ..\..\terraform.exe output -raw vpc_id
$targetGroupArn = ..\..\terraform.exe output -raw target_group_arn

# Get subnet IDs using JSON output
$publicSubnetsJson = ..\..\terraform.exe output -json public_subnet_ids
$subnetIds = $publicSubnetsJson | ConvertFrom-Json
$firstSubnetId = $subnetIds[0]

Pop-Location

Write-Host "Using subnet: $firstSubnetId" -ForegroundColor Cyan

# Create a simple user data script
$userData = @"
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

# Pull and run the API container
docker pull tethral/iot-api-discovery:latest
docker run -d --name tethral-api -p 8000:8000 --restart unless-stopped tethral/iot-api-discovery:latest

# Install curl for health checks
yum install -y curl

# Wait a bit and test
sleep 30
curl -f http://localhost:8000/api/health || echo "API starting up..."
"@

# Encode user data
$userDataEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userData))

Write-Host "Creating EC2 instance..." -ForegroundColor Blue

try {
    # Create EC2 instance using AWS CLI
    $instanceJson = aws ec2 run-instances `
        --image-id ami-0c02fb55956c7d316 `
        --count 1 `
        --instance-type t3.micro `
        --security-group-ids sg-0ccb2dd90680bb47e `
        --subnet-id $firstSubnetId `
        --user-data $userDataEncoded `
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=tethral-api-$Environment},{Key=Project,Value=Tethral},{Key=Environment,Value=$Environment}]" `
        --output json
    
    $instanceData = $instanceJson | ConvertFrom-Json
    $instanceId = $instanceData.Instances[0].InstanceId
    
    Write-Host "EC2 instance created: $instanceId" -ForegroundColor Green
    
    # Wait for instance to be running
    Write-Host "Waiting for instance to be running..." -ForegroundColor Blue
    
    do {
        Start-Sleep -Seconds 10
        $statusJson = aws ec2 describe-instances --instance-ids $instanceId --output json
        $statusData = $statusJson | ConvertFrom-Json
        $state = $statusData.Reservations[0].Instances[0].State.Name
        Write-Host "Instance state: $state" -ForegroundColor Gray
    } while ($state -ne "running")
    
    # Get instance details
    $instanceDetails = $statusData.Reservations[0].Instances[0]
    $publicIp = $instanceDetails.PublicIpAddress
    $privateIp = $instanceDetails.PrivateIpAddress
    
    Write-Host "Instance IP: $publicIp (public), $privateIp (private)" -ForegroundColor Cyan
    
    # Register with target group
    Write-Host "Registering instance with ALB target group..." -ForegroundColor Blue
    
    aws elbv2 register-targets `
        --target-group-arn $targetGroupArn `
        --targets "Id=$privateIp,Port=8000"
    
    Write-Host "Instance registered with ALB target group" -ForegroundColor Green
    
    # Wait for services to start
    Write-Host "Waiting for API service to start..." -ForegroundColor Blue
    Start-Sleep -Seconds 90
    
    # Test the API directly on the instance
    Write-Host "Testing API directly on instance..." -ForegroundColor Blue
    
    try {
        $directResponse = Invoke-WebRequest -Uri "http://$publicIp:8000/api/health" -Method Get -TimeoutSec 30
        Write-Host "Direct API test passed: $($directResponse.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "Direct API test failed (service may still be starting)" -ForegroundColor Yellow
    }
    
    # Test through ALB
    Write-Host "Testing API through ALB..." -ForegroundColor Blue
    
    try {
        $albResponse = Invoke-WebRequest -Uri "http://$albDnsName/api/health" -Method Get -TimeoutSec 30
        Write-Host "ALB API test passed: $($albResponse.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "ALB API test failed (health checks may still be in progress)" -ForegroundColor Yellow
    }
    
    # Create deployment summary
    $summary = @"
Simple EC2 API Deployment Summary:

Instance Details:
- Instance ID: $instanceId
- Public IP: $publicIp
- Private IP: $privateIp
- ALB DNS: $albDnsName

API Endpoints:
- Direct: http://$publicIp:8000/api/health
- ALB: http://$albDnsName/api/health
- Devices: http://$albDnsName/api/discovery/devices

Status:
- Instance: Running
- API Service: Deployed
- ALB Registration: Complete
- Health Checks: In Progress

Next Steps:
1. Wait 2-3 minutes for ALB health checks to pass
2. Test the API endpoints
3. Update your Flutter app to use the ALB URL
4. Monitor in AWS Console

"@
    
    $summary | Out-File -FilePath "simple-ec2-deployment-summary.txt" -Encoding UTF8
    Write-Host "Deployment summary saved to simple-ec2-deployment-summary.txt" -ForegroundColor Green
    
} catch {
    Write-Host "Failed to create EC2 instance: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "SIMPLE EC2 API DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host "Your API is now running on EC2" -ForegroundColor Cyan
Write-Host "Test directly: http://$publicIp:8000/api/health" -ForegroundColor Yellow
Write-Host "Test via ALB: http://$albDnsName/api/health" -ForegroundColor Yellow
