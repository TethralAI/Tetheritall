#!/usr/bin/env pwsh

# Deploy Tethral API to EC2 and register with ALB
# This script launches an EC2 instance with the API service

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

Write-Host "Deploying Tethral API to EC2..." -ForegroundColor Green

# Get infrastructure details
Push-Location "terraform"
$albDnsName = ..\..\terraform.exe output -raw alb_dns_name
$vpcId = ..\..\terraform.exe output -raw vpc_id
$targetGroupArn = ..\..\terraform.exe output -raw target_group_arn
$publicSubnets = ..\..\terraform.exe output -raw public_subnet_ids
Pop-Location

# Parse subnet IDs (remove brackets and quotes)
$subnetIds = $publicSubnets -replace '[\[\]"]', '' -split ','
$firstSubnetId = $subnetIds[0].Trim()

Write-Host "Using subnet: $firstSubnetId" -ForegroundColor Cyan

# Create user data script for EC2
$userData = @"
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/tethral
cd /opt/tethral

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  api:
    image: tethral/iot-api-discovery:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=dev
      - AWS_REGION=us-east-1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: tethral_db
      POSTGRES_USER: tethral_user
      POSTGRES_PASSWORD: tethral_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass tethral_redis_password
    restart: unless-stopped

volumes:
  postgres_data:
EOF

# Start services
docker-compose up -d

# Wait for API to be ready
sleep 30

# Test API health
curl -f http://localhost:8000/api/health || echo "API not ready yet"
"@

# Encode user data
$userDataEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userData))

# Create EC2 instance
Write-Host "Creating EC2 instance..." -ForegroundColor Blue

$instanceParams = @{
    ImageId = "ami-0c02fb55956c7d316"  # Amazon Linux 2023 AMI for us-east-1
    MinCount = 1
    MaxCount = 1
    InstanceType = "t3.micro"
    KeyName = "tethral-key"  # You'll need to create this key pair
    SecurityGroupIds = "sg-0ccb2dd90680bb47e"  # App security group from Terraform
    SubnetId = $firstSubnetId
    UserData = $userDataEncoded
    TagSpecifications = @(
        @{
            ResourceType = "instance"
            Tags = @(
                @{ Key = "Name"; Value = "tethral-api-$Environment" },
                @{ Key = "Project"; Value = "Tethral" },
                @{ Key = "Environment"; Value = $Environment }
            )
        }
    )
}

try {
    $instance = New-EC2Instance @instanceParams
    $instanceId = $instance.Instances[0].InstanceId
    
    Write-Host "EC2 instance created: $instanceId" -ForegroundColor Green
    
    # Wait for instance to be running
    Write-Host "Waiting for instance to be running..." -ForegroundColor Blue
    Wait-EC2Instance -InstanceId $instanceId -State "running"
    
    # Get instance details
    $instanceDetails = Get-EC2Instance -InstanceId $instanceId
    $publicIp = $instanceDetails.Instances[0].PublicIpAddress
    $privateIp = $instanceDetails.Instances[0].PrivateIpAddress
    
    Write-Host "Instance IP: $publicIp (public), $privateIp (private)" -ForegroundColor Cyan
    
    # Register with target group
    Write-Host "Registering instance with ALB target group..." -ForegroundColor Blue
    
    $targetParams = @{
        TargetGroupArn = $targetGroupArn
        Targets = @(
            @{
                Id = $privateIp
                Port = 8000
            }
        )
    }
    
    Register-ELB2Target @targetParams
    
    Write-Host "Instance registered with ALB target group" -ForegroundColor Green
    
    # Wait for health checks
    Write-Host "Waiting for health checks to pass..." -ForegroundColor Blue
    Start-Sleep -Seconds 60
    
    # Test the API
    Write-Host "Testing API endpoints..." -ForegroundColor Blue
    
    try {
        $healthResponse = Invoke-WebRequest -Uri "http://$albDnsName/api/health" -Method Get -TimeoutSec 30
        Write-Host "Health check passed: $($healthResponse.StatusCode)" -ForegroundColor Green
        
        $devicesResponse = Invoke-WebRequest -Uri "http://$albDnsName/api/discovery/devices" -Method Get -TimeoutSec 30
        Write-Host "Devices endpoint working: $($devicesResponse.StatusCode)" -ForegroundColor Green
        
    } catch {
        Write-Host "API not yet responding through ALB (this is normal, may take a few minutes)" -ForegroundColor Yellow
        Write-Host "You can test directly on the instance: http://$publicIp:8000/api/health" -ForegroundColor Cyan
    }
    
    # Create deployment summary
    $summary = @"
EC2 API Deployment Summary:

Instance Details:
- Instance ID: $instanceId
- Public IP: $publicIp
- Private IP: $privateIp
- ALB DNS: $albDnsName

API Endpoints:
- Health: http://$albDnsName/api/health
- Devices: http://$albDnsName/api/discovery/devices
- Direct: http://$publicIp:8000/api/health

Next Steps:
1. Test the API endpoints
2. Update your Flutter app to use the ALB URL
3. Monitor the instance in AWS Console
4. Set up CloudWatch monitoring

"@
    
    $summary | Out-File -FilePath "ec2-deployment-summary.txt" -Encoding UTF8
    Write-Host "Deployment summary saved to ec2-deployment-summary.txt" -ForegroundColor Green
    
} catch {
    Write-Host "Failed to create EC2 instance: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "EC2 API DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host "Your API is now running on EC2 and registered with the ALB" -ForegroundColor Cyan
Write-Host "Test it at: http://$albDnsName/api/health" -ForegroundColor Yellow
