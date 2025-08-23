# Local Environment Setup Guide

This guide will help you set up your local development environment for Tetheritall, including connections to CockroachDB and AWS.

## Prerequisites

- Python 3.8+
- Docker (optional, for containerized development)
- Git (already done - you've cloned the repo)

## Quick Setup

Run the automated setup script:

```bash
python setup-local-env.py
```

This will:
- Create a `.env` file with default configuration
- Check your system for required dependencies
- Provide instructions for CockroachDB and AWS setup

## Manual Setup Steps

### 1. Environment Configuration

The setup script creates `iot-api-discovery/.env` with all necessary configuration options. Key settings:

#### Database Configuration
```bash
# For local development (SQLite)
DATABASE_URL=sqlite:///./iot_discovery.db

# For CockroachDB (uncomment and configure)
# DATABASE_URL=postgresql+psycopg2://username:password@your-cockroachdb-host:26257/iot_discovery?sslmode=require
```

#### AWS Configuration
```bash
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name
```

#### API Configuration
```bash
API_TOKEN=your-api-token-here
JWT_SECRET=your-jwt-secret-here
```

### 2. CockroachDB Setup

#### Option A: CockroachDB Cloud (Recommended)

1. **Sign up for CockroachDB Cloud**
   - Go to https://cockroachlabs.cloud/
   - Create a free account
   - Create a new cluster

2. **Get Connection Details**
   - From your cluster dashboard, copy the connection string
   - It will look like: `postgresql://username:password@host:26257/defaultdb?sslmode=require`

3. **Create Database**
   - Connect to your cluster using the CockroachDB SQL client or web console
   - Run: `CREATE DATABASE iot_discovery;`

4. **Update Environment**
   - Edit `iot-api-discovery/.env`
   - Uncomment and update the DATABASE_URL line:
   ```bash
   DATABASE_URL=postgresql+psycopg2://username:password@your-cluster-host:26257/iot_discovery?sslmode=require
   ```

#### Option B: Local CockroachDB

1. **Install CockroachDB**
   ```bash
   # Download and install from https://www.cockroachlabs.com/docs/stable/install-cockroachdb.html
   # Or use Docker:
   docker run -d --name cockroachdb -p 26257:26257 -p 8080:8080 cockroachdb/cockroach:latest start-single-node --insecure
   ```

2. **Create Database**
   ```bash
   cockroach sql --insecure --host=localhost:26257
   CREATE DATABASE iot_discovery;
   ```

3. **Update Environment**
   ```bash
   DATABASE_URL=postgresql+psycopg2://root@localhost:26257/iot_discovery?sslmode=disable
   ```

### 3. AWS Setup

#### Install AWS CLI

1. **Download and Install**
   - Windows: https://aws.amazon.com/cli/
   - macOS: `brew install awscli`
   - Linux: `sudo apt-get install awscli` or `sudo yum install awscli`

2. **Configure Credentials**
   ```bash
   aws configure
   ```
   Enter your:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., us-east-1)
   - Default output format (json)

#### Create S3 Bucket

1. **Create Bucket**
   ```bash
   aws s3 mb s3://your-tetheritall-bucket --region us-east-1
   ```

2. **Update Environment**
   ```bash
   AWS_S3_BUCKET=your-tetheritall-bucket
   AWS_REGION=us-east-1
   ```

#### IAM Permissions

Ensure your AWS user has the following permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-tetheritall-bucket",
                "arn:aws:s3:::your-tetheritall-bucket/*"
            ]
        }
    ]
}
```

### 4. Python Dependencies

Install required Python packages:

```bash
cd iot-api-discovery
pip install -r requirements.txt
```

### 5. Redis Setup

#### Option A: Docker (Recommended)
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

#### Option B: Local Installation
- **Windows**: Download from https://redis.io/download
- **macOS**: `brew install redis && brew services start redis`
- **Linux**: `sudo apt-get install redis-server && sudo systemctl start redis`

### 6. Database Migration

If using CockroachDB, run database migrations:

```bash
cd iot-api-discovery
alembic upgrade head
```

## Running the Application

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down
```

### Option 2: Local Development

```bash
cd iot-api-discovery

# Start Redis (if not using Docker)
redis-server

# Start the API server
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Start integrations service
uvicorn services.integrations.server:app --host 0.0.0.0 --port 8100 --reload

# Start API gateway
uvicorn services.api_gateway.server:app --host 0.0.0.0 --port 8001 --reload
```

## Verification

1. **Check API Health**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check Database Connection**
   ```bash
   curl http://localhost:8000/devices
   ```

3. **Check AWS Connection**
   ```bash
   aws s3 ls s3://your-tetheritall-bucket
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify DATABASE_URL in `.env`
   - Check if CockroachDB is running
   - Ensure SSL mode is correct

2. **AWS Credentials Not Found**
   - Run `aws configure`
   - Check `~/.aws/credentials`
   - Verify IAM permissions

3. **Redis Connection Failed**
   - Check if Redis is running: `redis-cli ping`
   - Verify REDIS_URL in `.env`

4. **Port Already in Use**
   - Check what's using the port: `netstat -an | grep 8000`
   - Kill the process or change the port

### Getting Help

- Check the logs: `make logs`
- Review `deploy/docs/` for additional documentation
- Check the main README.md for project overview

## Next Steps

1. **Explore the API**
   - Visit http://localhost:8000/docs for API documentation
   - Try the sample endpoints

2. **Kubernetes Deployment**
   ```bash
   make helm-deps
   make helm-install-dev
   ```

3. **Development**
   - The application uses SQLAlchemy for database operations
   - FastAPI for the web framework
   - Redis for caching and session management
   - AWS SDK for cloud integrations

