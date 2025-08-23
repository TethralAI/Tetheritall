# Tetheritall

A comprehensive IoT orchestration platform with distributed ML processing, security monitoring, and edge computing capabilities.

## 🏗️ Architecture

```
Tetheritall/
├── api/                    # Core API server
│   ├── server.py          # Main FastAPI application
│   └── routes/            # API route modules
├── services/              # Microservices
│   ├── discovery/         # IoT device discovery
│   ├── ml/               # ML orchestration & inference
│   ├── orchestration/    # Workflow management
│   ├── security/         # Security monitoring
│   ├── edge/             # Edge computing services
│   └── gateway/          # API gateway
├── shared/               # Shared libraries
│   ├── database/         # Database models & utilities
│   ├── config/           # Configuration management
│   └── libs/             # Common utilities
├── deploy/               # Deployment configurations
├── tests/                # Test suite
└── docs/                 # Documentation
```

## 🚀 Features

### Core Capabilities
- **IoT Device Discovery**: Automated device detection and API endpoint discovery
- **ML Orchestration**: Distributed ML processing (local/edge/cloud)
- **Workflow Management**: Complex orchestration workflows
- **Security Monitoring**: Real-time threat detection and response
- **Edge Computing**: Distributed processing capabilities

### ML Processing Options
- **Local Processing**: On-premise ML inference
- **Edge Processing**: Distributed edge computing
- **Cloud Processing**: Scalable cloud-based ML
- **Hybrid Processing**: Dynamic routing based on requirements

## 🛠️ Quick Start

### Prerequisites
- Python 3.8+
- Docker (optional)
- Redis (optional)
- CockroachDB (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Tetheritall
   ```

2. **Set up environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Set up database**
   ```bash
   make setup-db
   ```

5. **Run the application**
   ```bash
   make run
   ```

### Docker Setup

```bash
# Build and run with Docker
make docker-build
make docker-run

# Or use Docker Compose
docker-compose up -d
```

## 📡 API Endpoints

### Health & Monitoring
- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

### Discovery
- `GET /discovery/devices` - List discovered devices
- `POST /discovery/scan` - Start discovery scan

### ML Orchestration
- `GET /ml/models` - List available ML models
- `POST /ml/inference` - Run ML inference

### Orchestration
- `GET /orchestration/workflows` - List workflows
- `POST /orchestration/workflows` - Create workflow

### Security
- `GET /security/audit` - Security audit logs

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=sqlite:///./tetheritall.db

# ML Processing
ML_LOCAL_ENABLED=true
ML_EDGE_ENABLED=true
ML_CLOUD_ENABLED=true

# Security
SECURITY_MONITORING_ENABLED=true
SECURITY_THREAT_DETECTION_ENABLED=true

# AWS Integration
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket
```

## 🧪 Testing

```bash
# Run tests
make test

# Run with coverage
make test-coverage
```

## 📊 Monitoring

### Health Checks
```bash
# Check service health
make health

# View metrics
make metrics
```

### Logs
```bash
# View application logs
docker-compose logs -f api

# View specific service logs
docker-compose logs -f discovery
```

## 🔒 Security

The platform includes comprehensive security features:

- **API Key Authentication**: Secure API access
- **Threat Detection**: Real-time security monitoring
- **Audit Logging**: Complete activity tracking
- **IP Blocking**: Automatic threat response
- **Rate Limiting**: DDoS protection

## 🚀 Deployment

### Local Development
```bash
make setup-local
make run
```

### Production
```bash
# Using Docker
make docker-build
make docker-run

# Using Kubernetes
kubectl apply -f deploy/k8s/
```

## 📈 Scaling

### Horizontal Scaling
- Stateless API services
- Load balancer support
- Auto-scaling capabilities

### ML Processing Scaling
- Local: Single-node processing
- Edge: Distributed edge nodes
- Cloud: Auto-scaling cloud resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[License information]

## 🆘 Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/your-repo/issues)
- Discussions: [GitHub Discussions](https://github.com/your-repo/discussions)
