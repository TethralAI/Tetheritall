#!/usr/bin/env python3
"""
Local Environment Setup Script for Tetheritall
This script helps set up the local development environment with CockroachDB and AWS configuration.
"""

import os
import sys
import subprocess
from pathlib import Path

def create_env_file():
    """Create a .env file with default configuration."""
    env_content = """# Database Configuration
# For local development with SQLite (default)
DATABASE_URL=sqlite:///./iot_discovery.db

# For CockroachDB (uncomment and configure)
# DATABASE_URL=postgresql+psycopg2://username:password@your-cockroachdb-host:26257/iot_discovery?sslmode=require

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_TOKEN=your-api-token-here
JWT_SECRET=your-jwt-secret-here
JWT_AUDIENCE=your-jwt-audience

# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name
# AWS credentials will be loaded from ~/.aws/credentials or environment variables

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_PER_SECOND=2.0

# Request Configuration
REQUEST_TIMEOUT_SECONDS=20
MAX_CONCURRENT_REQUESTS=10

# Cloud Integrations (optional)
SMARTTHINGS_TOKEN=
TUYA_CLIENT_ID=
TUYA_CLIENT_SECRET=
TUYA_BASE_URL=https://openapi.tuyaus.com

# Firebase Cloud Messaging
FCM_SERVER_KEY=

# HCP Terraform (Terraform Cloud) API
HCP_TERRAFORM_TOKEN=
HCP_TERRAFORM_ORG=
HCP_TERRAFORM_WORKSPACE_ID=

# Home Assistant
HOME_ASSISTANT_BASE_URL=
HOME_ASSISTANT_TOKEN=

# Google Nest SDM
GOOGLE_NEST_ACCESS_TOKEN=

# Philips Hue
HUE_REMOTE_TOKEN=

# openHAB
OPENHAB_BASE_URL=
OPENHAB_TOKEN=

# Z-Wave JS
ZWAVE_JS_URL=ws://localhost:3000

# Alexa Smart Home
ALEXA_SKILL_SECRET=

# SmartThings OAuth
SMARTTHINGS_CLIENT_ID=
SMARTTHINGS_CLIENT_SECRET=
SMARTTHINGS_REDIRECT_URI=

# Tuya OAuth
TUYA_REDIRECT_URI=

# Zigbee2MQTT
Z2M_BROKER=localhost
Z2M_PORT=1883
Z2M_USERNAME=
Z2M_PASSWORD=

# Smartcar
SMARTCAR_CLIENT_ID=
SMARTCAR_CLIENT_SECRET=
SMARTCAR_REDIRECT_URI=

# LLM Configuration
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# LLM Guardrails
ORG_ID_HEADER=X-Org-Id
LLM_BUDGETS=default:1000,orgA:500
LLM_DETERMINISTIC=true
LLM_ALLOWED_TOOLS=

# Infrastructure
OUTBOUND_ALLOWLIST=integrations
OUTBOUND_CIDRS=

# Edge Configuration
EDGE_LAN_ONLY=true
TELEMETRY_OPT_IN=false
TELEMETRY_NAMESPACE=

# OCPI (Energy/EV protocols)
ENABLE_OCPI=false
OCPI_BASE_URL=
OCPI_TOKEN=

# Proxy Configuration
PROXY_CAPABILITIES_VIA_INTEGRATIONS=false
INTEGRATIONS_BASE_URL=http://integrations:8100
PROXY_CANARY_PERCENT=0

# Organization Management
ORG_ALLOWLIST=
ORG_DENYLIST=

# Caching
CACHE_GET_PREFIXES=
CACHE_TTL_SECONDS=60

# LLM Denylist
LLM_PROMPT_DENYLIST=

# Wearables/Health
OURA_CLIENT_ID=
OURA_REDIRECT_URI=
TERRA_API_KEY=

# Hubitat
HUBITAT_MAKER_BASE_URL=
HUBITAT_MAKER_TOKEN=

# mTLS Configuration
MTLS_CA_PATH=
MTLS_CLIENT_CERT_PATH=
MTLS_CLIENT_KEY_PATH=

# Event Bus Configuration
EVENT_BUS_BACKEND=nats
NATS_URL=nats://localhost:4222
NATS_STREAM=
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
EVENTS_STREAM_KEY=events:stream
EVENTS_MAXLEN=10000
"""
    
    env_path = Path("iot-api-discovery/.env")
    if env_path.exists():
        print(f"⚠️  {env_path} already exists. Skipping creation.")
        return
    
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with open(env_path, 'w') as f:
        f.write(env_content)
    print(f"✅ Created {env_path}")

def check_docker():
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker is not installed or not accessible")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False

def check_python_dependencies():
    """Check if Python dependencies are installed."""
    try:
        import fastapi
        import sqlalchemy
        import redis
        import boto3
        print("✅ Python dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        return False

def install_python_dependencies():
    """Install Python dependencies."""
    requirements_file = Path("iot-api-discovery/requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)], check=True)
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False

def setup_cockroachdb_instructions():
    """Provide instructions for setting up CockroachDB."""
    print("\n🐓 CockroachDB Setup Instructions:")
    print("1. Sign up for CockroachDB Cloud at https://cockroachlabs.cloud/")
    print("2. Create a new cluster")
    print("3. Get your connection string from the cluster dashboard")
    print("4. Update the DATABASE_URL in iot-api-discovery/.env:")
    print("   DATABASE_URL=postgresql+psycopg2://username:password@your-cluster-host:26257/iot_discovery?sslmode=require")
    print("5. Create the database: CREATE DATABASE iot_discovery;")

def setup_aws_instructions():
    """Provide instructions for setting up AWS."""
    print("\n☁️ AWS Setup Instructions:")
    print("1. Install AWS CLI: https://aws.amazon.com/cli/")
    print("2. Configure AWS credentials:")
    print("   aws configure")
    print("3. Update AWS settings in iot-api-discovery/.env:")
    print("   AWS_REGION=your-region")
    print("   AWS_S3_BUCKET=your-bucket-name")
    print("4. Ensure your AWS user has appropriate S3 permissions")

def setup_redis():
    """Check if Redis is available and provide setup instructions."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running on localhost:6379")
        return True
    except Exception:
        print("⚠️  Redis is not running. You can:")
        print("   - Install Redis locally")
        print("   - Use Docker: docker run -d -p 6379:6379 redis:7-alpine")
        print("   - Or use the provided docker-compose.yml which includes Redis")
        return False

def main():
    print("🚀 Setting up Tetheritall Local Environment")
    print("=" * 50)
    
    # Create environment file
    create_env_file()
    
    # Check Docker
    docker_available = check_docker()
    
    # Check Python dependencies
    if not check_python_dependencies():
        install_python_dependencies()
    
    # Check Redis
    setup_redis()
    
    # Provide setup instructions
    setup_cockroachdb_instructions()
    setup_aws_instructions()
    
    print("\n🎉 Setup Complete!")
    print("\nNext steps:")
    print("1. Edit iot-api-discovery/.env with your configuration")
    print("2. For local development: make up")
    print("3. For Kubernetes: make helm-deps && make helm-install-dev")
    print("\nFor more information, see deploy/docs/")

if __name__ == "__main__":
    main()

