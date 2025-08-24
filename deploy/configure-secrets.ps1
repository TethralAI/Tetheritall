#!/usr/bin/env pwsh

# Configure AWS Secrets Manager for Tethral
# This script sets up all required secrets in AWS Secrets Manager

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$DryRun
)

Write-Host "🔐 Configuring AWS Secrets Manager..." -ForegroundColor Green

# Function to create or update a secret
function Set-AWSSecret {
    param(
        [string]$SecretName,
        [hashtable]$SecretValue,
        [string]$Description
    )
    
    $fullSecretName = "tethral/$Environment/$SecretName"
    
    try {
        # Convert to JSON
        $secretJson = $SecretValue | ConvertTo-Json -Compress
        
        if ($DryRun) {
            Write-Host "🔍 Would create/update secret: $fullSecretName" -ForegroundColor Yellow
            Write-Host "   Description: $Description" -ForegroundColor Gray
            return $true
        }
        
        # Check if secret exists
        $existingSecret = aws secretsmanager describe-secret --secret-id $fullSecretName --region $Region 2>$null
        
        if ($existingSecret) {
            Write-Host "🔄 Updating existing secret: $fullSecretName" -ForegroundColor Cyan
            aws secretsmanager update-secret --secret-id $fullSecretName --secret-string $secretJson --region $Region
        } else {
            Write-Host "🆕 Creating new secret: $fullSecretName" -ForegroundColor Cyan
            aws secretsmanager create-secret --name $fullSecretName --description $Description --secret-string $secretJson --region $Region
        }
        
        Write-Host "✅ Secret $fullSecretName configured successfully" -ForegroundColor Green
        return $true
    }
    catch {
        $errorMessage = $_.Exception.Message
        Write-Host "❌ Failed to configure secret $fullSecretName`: $errorMessage" -ForegroundColor Red
        return $false
    }
}

# Database secrets
$databaseSecrets = @{
    "database-url" = "postgresql://tethral_user:tethral_password@tethral-${Environment}-db.cluster-xyz.us-east-1.rds.amazonaws.com:5432/tethral_db"
    "username" = "tethral_user"
    "password" = "tethral_password"
    "host" = "tethral-${Environment}-db.cluster-xyz.us-east-1.rds.amazonaws.com"
    "port" = "5432"
    "database" = "tethral_db"
}

Set-AWSSecret -SecretName "database" -SecretValue $databaseSecrets -Description "Tethral database credentials"

# Redis secrets
$redisSecrets = @{
    "redis-url" = "redis://tethral-${Environment}-redis.xyz.us-east-1.cache.amazonaws.com:6379"
    "password" = "tethral_redis_password"
    "host" = "tethral-${Environment}-redis.xyz.us-east-1.cache.amazonaws.com"
    "port" = "6379"
}

Set-AWSSecret -SecretName "redis" -SecretValue $redisSecrets -Description "Tethral Redis credentials"

# API secrets
$apiSecrets = @{
    "api-token" = "tethral_api_token_$(Get-Random -Minimum 1000 -Maximum 9999)"
    "jwt-secret" = "tethral_jwt_secret_$(Get-Random -Minimum 10000 -Maximum 99999)"
    "session-secret" = "tethral_session_secret_$(Get-Random -Minimum 100000 -Maximum 999999)"
}

Set-AWSSecret -SecretName "api" -SecretValue $apiSecrets -Description "Tethral API authentication secrets"

# AWS credentials (for service-to-service communication)
$awsSecrets = @{
    "access-key-id" = "AKIAIOSFODNN7EXAMPLE"
    "secret-access-key" = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    "region" = $Region
}

Set-AWSSecret -SecretName "aws" -SecretValue $awsSecrets -Description "Tethral AWS service credentials"

# Third-party API keys (example)
$thirdPartySecrets = @{
    "smartthings-client-id" = "your_smartthings_client_id"
    "smartthings-client-secret" = "your_smartthings_client_secret"
    "tuya-access-id" = "your_tuya_access_id"
    "tuya-access-key" = "your_tuya_access_key"
    "hue-bridge-ip" = "192.168.1.100"
    "hue-username" = "your_hue_username"
}

Set-AWSSecret -SecretName "third-party" -SecretValue $thirdPartySecrets -Description "Tethral third-party service credentials"

# ML model secrets
$mlSecrets = @{
    "openai-api-key" = "your_openai_api_key"
    "anthropic-api-key" = "your_anthropic_api_key"
    "model-endpoint-url" = "https://tethral-${Environment}-ml.us-east-1.amazonaws.com"
}

Set-AWSSecret -SecretName "ml" -SecretValue $mlSecrets -Description "Tethral ML model credentials"

# Monitoring secrets
$monitoringSecrets = @{
    "grafana-admin-password" = "tethral_grafana_password_$(Get-Random -Minimum 1000 -Maximum 9999)"
    "prometheus-basic-auth" = "admin:tethral_prometheus_password_$(Get-Random -Minimum 1000 -Maximum 9999)"
    "alertmanager-webhook-url" = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
}

Set-AWSSecret -SecretName "monitoring" -SecretValue $monitoringSecrets -Description "Tethral monitoring credentials"

Write-Host "🎉 AWS Secrets Manager configuration completed!" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "📋 Summary of configured secrets:" -ForegroundColor Cyan
    aws secretsmanager list-secrets --region $Region --query "SecretList[?contains(Name, 'tethral/$Environment')].{Name:Name,Description:Description}" --output table
}
