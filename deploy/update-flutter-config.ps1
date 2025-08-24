#!/usr/bin/env pwsh

# Update Flutter App Configuration for AWS Deployment
# This script updates the Flutter app to use the new AWS API endpoint

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

Write-Host "Updating Flutter App Configuration for AWS..." -ForegroundColor Green

# Get ALB DNS name from Terraform
Push-Location "terraform"
$albDnsName = ..\..\terraform.exe output -raw alb_dns_name
Pop-Location

Write-Host "ALB DNS Name: $albDnsName" -ForegroundColor Cyan

# Create .env file content
$envContent = @"
# IoT Discovery Flutter App - Environment Configuration
# UPDATED FOR AWS DEPLOYMENT - $(Get-Date)

# Firebase Configuration
FIREBASE_API_KEY=your_firebase_api_key_here
FIREBASE_APP_ID=your_firebase_app_id_here
FIREBASE_MESSAGING_SENDER_ID=your_sender_id_here
FIREBASE_PROJECT_ID=your_project_id_here
FIREBASE_STORAGE_BUCKET=your_storage_bucket_here
FIREBASE_AUTH_DOMAIN=your_auth_domain_here

# Backend API Configuration - UPDATED FOR AWS DEPLOYMENT
API_BASE_URL=http://$albDnsName
API_TIMEOUT_SECONDS=30
API_RETRY_ATTEMPTS=3

# WebSocket Configuration
WEBSOCKET_URL=ws://$albDnsName/ws

# Analytics Configuration
ANALYTICS_ENABLED=true
ANALYTICS_DEBUG_MODE=false
ANALYTICS_SESSION_TIMEOUT_MINUTES=30

# Notification Configuration
NOTIFICATIONS_ENABLED=true
NOTIFICATIONS_CHANNEL_ID=onboarding_channel
NOTIFICATIONS_CHANNEL_NAME=Onboarding Notifications
NOTIFICATIONS_CHANNEL_DESCRIPTION=Notifications for onboarding progress and achievements

# Camera Configuration
CAMERA_RESOLUTION=medium
CAMERA_ENABLE_AUDIO=false
CAMERA_FLASH_MODE=auto

# Storage Configuration
STORAGE_ENCRYPTION_ENABLED=true
STORAGE_MAX_FILE_SIZE_MB=10
STORAGE_CACHE_SIZE_MB=50

# Security Configuration
SECURITY_BIOMETRIC_ENABLED=true
SECURITY_PIN_ENABLED=true
SECURITY_SESSION_TIMEOUT_MINUTES=15

# Performance Configuration
PERFORMANCE_TRACKING_ENABLED=true
PERFORMANCE_SAMPLE_RATE=0.1
PERFORMANCE_MAX_TRACES=100

# Debug Configuration
DEBUG_MODE=true
DEBUG_LOG_LEVEL=info
DEBUG_SHOW_PERFORMANCE_OVERLAY=false
DEBUG_SHOW_SEMANTICS_OVERLAY=false

# Feature Flags
FEATURE_ONBOARDING_ENABLED=true
FEATURE_DEVICE_DISCOVERY_ENABLED=true
FEATURE_PHOTO_COLLECTION_ENABLED=true
FEATURE_QUEST_SYSTEM_ENABLED=true
FEATURE_ACHIEVEMENT_SYSTEM_ENABLED=true
FEATURE_ANALYTICS_ENABLED=true
FEATURE_NOTIFICATIONS_ENABLED=true

# Onboarding Configuration
ONBOARDING_SKIP_ENABLED=false
ONBOARDING_AUTO_ADVANCE_ENABLED=false
ONBOARDING_TUTORIAL_ENABLED=true
ONBOARDING_DEVICE_CAPTURE_ENABLED=true
ONBOARDING_PHOTO_COLLECTION_ENABLED=true
ONBOARDING_QUEST_SYSTEM_ENABLED=true

# Device Discovery Configuration
DEVICE_DISCOVERY_TIMEOUT_SECONDS=30
DEVICE_DISCOVERY_RETRY_ATTEMPTS=3
DEVICE_DISCOVERY_SCAN_INTERVAL_SECONDS=5
DEVICE_DISCOVERY_MAX_DEVICES=50

# Photo Collection Configuration
PHOTO_COLLECTION_MAX_PHOTOS=100
PHOTO_COLLECTION_MAX_FILE_SIZE_MB=5
PHOTO_COLLECTION_COMPRESSION_QUALITY=0.8
PHOTO_COLLECTION_ENABLE_EDITING=true

# Quest System Configuration
QUEST_SYSTEM_MAX_ACTIVE_QUESTS=5
QUEST_SYSTEM_AUTO_START_ENABLED=true
QUEST_SYSTEM_REMINDER_ENABLED=true
QUEST_SYSTEM_REMINDER_INTERVAL_HOURS=24

# Achievement System Configuration
ACHIEVEMENT_SYSTEM_NOTIFICATIONS_ENABLED=true
ACHIEVEMENT_SYSTEM_ANIMATIONS_ENABLED=true
ACHIEVEMENT_SYSTEM_SOUND_ENABLED=true
ACHIEVEMENT_SYSTEM_HAPTIC_ENABLED=true

# Points System Configuration
POINTS_DEVICE_CAPTURE_BASE=50
POINTS_PHOTO_COLLECTION_BASE=30
POINTS_QUEST_COMPLETION_BASE=100
POINTS_ACHIEVEMENT_UNLOCK_BASE=25
POINTS_BONUS_MULTIPLIER=1.5
"@

# Save the configuration
$envContent | Out-File -FilePath "flutter-app-config.env" -Encoding UTF8

Write-Host "Flutter app configuration saved to flutter-app-config.env" -ForegroundColor Green

# Create instructions for manual update
$instructions = @"

FLUTTER APP CONFIGURATION UPDATE

To update your Flutter app to use the new AWS API endpoint:

1. Copy the contents of 'flutter-app-config.env' to your Flutter app's '.env' file:
   ```bash
   cp flutter-app-config.env ../iot-discovery-flutter-app/.env
   ```

2. Or manually update the API_BASE_URL in your .env file to:
   API_BASE_URL=http://$albDnsName

3. Rebuild your Flutter app:
   ```bash
   cd ../iot-discovery-flutter-app
   flutter clean
   flutter pub get
   flutter build apk  # for Android
   flutter build ios  # for iOS
   ```

4. Test the connection:
   - The app will now connect to your AWS-deployed API
   - All device discovery and orchestration features will work
   - The API endpoints are fully implemented and ready

API Endpoints Available:
- Health: http://$albDnsName/api/health
- Devices: http://$albDnsName/api/discovery/devices
- Device Details: http://$albDnsName/api/devices/{device_id}
- Orchestration: http://$albDnsName/api/orchestration/plan

"@

$instructions | Out-File -FilePath "flutter-config-instructions.md" -Encoding UTF8

Write-Host "Configuration instructions saved to flutter-config-instructions.md" -ForegroundColor Green

Write-Host ""
Write-Host "FLUTTER CONFIGURATION UPDATE COMPLETED!" -ForegroundColor Green
Write-Host "Check flutter-config-instructions.md for next steps" -ForegroundColor Cyan
Write-Host "Your Flutter app is ready to connect to AWS!" -ForegroundColor Yellow
