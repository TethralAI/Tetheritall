# Tethral Deployment Guide

This directory contains the complete deployment infrastructure for the Tethral Suggestion Engine, providing enterprise-grade deployment solutions for both development and production environments.

## 🏗️ Deployment Architecture

The Tethral deployment consists of two main layers:

### 1. Infrastructure Layer (`deploy/infra/`)
- **Database**: PostgreSQL HA cluster, Redis with Sentinel
- **Monitoring**: Prometheus, Grafana, AlertManager
- **Networking**: Nginx Ingress, Cert-Manager, Load Balancers
- **Security**: Network Policies, RBAC, Encrypted Storage
- **Operations**: Backup Systems, Chaos Engineering, Auto-scaling

### 2. Application Layer (`deploy/suggestion/`)
- **Suggestion Engine**: Core AI-powered recommendation service
- **API Gateway**: REST API endpoints and mobile integration
- **Security**: Data encryption, access control, audit logging
- **Monitoring**: Application metrics, performance tracking
- **Mobile Integration**: Push notifications, device management

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   ```bash
   # For local development (Docker Desktop)
   # Enable Kubernetes in Docker Desktop settings
   
   # For cloud deployment
   # Create EKS/GKE/AKS cluster with at least 4 CPU cores and 8GB RAM
   ```

2. **Required Tools**
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl && sudo mv kubectl /usr/local/bin/
   
   # Install helm
   curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
   sudo mv linux-amd64/helm /usr/local/bin/
   
   # Install AWS CLI (for AWS deployments)
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip && sudo ./aws/install
   ```

### Complete Deployment

#### Step 1: Deploy Infrastructure
```bash
# Linux/macOS
chmod +x deploy/infra/deploy-infrastructure.sh
./deploy/infra/deploy-infrastructure.sh deploy

# Windows PowerShell
.\deploy\infra\deploy-infrastructure.ps1 deploy
```

#### Step 2: Deploy Suggestion Engine
```bash
# Linux/macOS
chmod +x deploy/suggestion/deploy.sh
./deploy/suggestion/deploy.sh deploy

# Windows PowerShell
.\deploy\suggestion\deploy.ps1 deploy
```

#### Step 3: Verify Deployment
```bash
# Check infrastructure status
./deploy/infra/deploy-infrastructure.sh status

# Check application status
./deploy/suggestion/deploy.sh status

# Run health checks
./deploy/infra/deploy-infrastructure.sh test
./deploy/suggestion/deploy.sh test
```

## 📋 Deployment Options

### Development Environment
```bash
# Deploy with minimal resources
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment dev \
  --skip-monitoring

./deploy/suggestion/deploy.sh deploy \
  --environment dev \
  --replicas 1
```

### Staging Environment
```bash
# Deploy with full monitoring
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment staging

./deploy/suggestion/deploy.sh deploy \
  --environment staging \
  --replicas 2
```

### Production Environment
```bash
# Deploy with production settings
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment prod \
  --namespace tethral-prod

./deploy/suggestion/deploy.sh deploy \
  --environment prod \
  --replicas 3 \
  --enable-monitoring
```

## 🔧 Configuration

### Environment Variables

#### Infrastructure Configuration
```bash
# Core settings
NAMESPACE=iot                    # Kubernetes namespace
ENVIRONMENT=prod                 # Environment type (dev/staging/prod)
SKIP_MONITORING=false           # Skip monitoring stack
SKIP_INGRESS=false              # Skip ingress controller
SKIP_CERT_MANAGER=false         # Skip cert-manager

# Resource settings
POSTGRES_REPLICAS=3             # PostgreSQL cluster size
REDIS_REPLICAS=3                # Redis cluster size
STORAGE_CLASS=fast-ssd          # Storage class for volumes
```

#### Application Configuration
```bash
# Suggestion Engine settings
SUGGESTION_REPLICAS=3           # Number of replicas
MAX_COMBINATIONS=2000           # Max combinations to generate
TIME_BUDGET_MS=8000             # Time budget for generation
LLM_ENABLED=true                # Enable LLM integration

# Security settings
ENCRYPTION_ENABLED=true         # Enable data encryption
AUDIT_LOGGING_ENABLED=true      # Enable audit logging
SESSION_TIMEOUT_HOURS=24        # Session timeout

# Mobile settings
PUSH_NOTIFICATIONS_ENABLED=true # Enable push notifications
OFFLINE_CACHE_ENABLED=true      # Enable offline caching
DEVICE_REGISTRATION_ENABLED=true # Enable device registration
```

### Custom Values Files

#### Infrastructure Values
```yaml
# deploy/infra/values-prod.yaml
namespace: tethral-prod
environment: prod
postgres:
  replicas: 5
  storage: 100Gi
redis:
  replicas: 5
  memory: 1Gi
monitoring:
  enabled: true
  retention: 30d
```

#### Application Values
```yaml
# deploy/suggestion/values-prod.yaml
replicaCount: 5
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
```

## 🔒 Security Configuration

### Network Security
- **Network Policies**: Default deny-all with explicit allow rules
- **Pod Security**: Non-root containers with read-only filesystems
- **Service Mesh**: Optional Istio integration for advanced traffic management

### Data Security
- **Encryption at Rest**: All EBS volumes encrypted with KMS
- **Encryption in Transit**: TLS 1.2/1.3 for all communications
- **Secrets Management**: Kubernetes secrets with encryption

### Access Control
- **RBAC**: Role-based access control with least privilege
- **Service Accounts**: Dedicated accounts for each component
- **Audit Logging**: Comprehensive audit trail for all operations

## 📊 Monitoring & Observability

### Infrastructure Monitoring
- **Prometheus**: Metrics collection and storage
- **Grafana**: Dashboards and visualization
- **AlertManager**: Alert routing and notifications
- **ServiceMonitors**: Automatic service discovery

### Application Monitoring
- **Custom Metrics**: Suggestion generation rates, response times
- **Business Metrics**: User engagement, recommendation acceptance
- **Performance Metrics**: Resource utilization, error rates
- **Security Metrics**: Access patterns, authentication events

### Dashboards
- **Infrastructure Overview**: Cluster health and resource usage
- **Application Performance**: Request rates and response times
- **Business Intelligence**: User behavior and recommendation effectiveness
- **Security Monitoring**: Access patterns and security events

## 🔄 Backup & Disaster Recovery

### Automated Backups
- **Database Backups**: Daily PostgreSQL dumps with compression
- **Configuration Backups**: Daily backup of all K8s resources
- **Application Data**: Backup of user preferences and learning data
- **Storage**: Encrypted backups stored in S3 with lifecycle policies

### Recovery Procedures
1. **Point-in-Time Recovery**: Restore database to specific timestamp
2. **Configuration Recovery**: Apply backed-up manifests
3. **Full Cluster Recovery**: Recreate cluster and restore all data
4. **Application Recovery**: Restore application state and user data

## 🧪 Testing & Validation

### Chaos Engineering
- **Network Partition Tests**: Simulate network failures
- **Pod Failure Tests**: Test pod restart and recovery
- **Load Testing**: Performance testing with realistic scenarios
- **Security Testing**: Penetration testing and vulnerability scans

### Health Checks
- **Liveness Probes**: Detect and restart unhealthy containers
- **Readiness Probes**: Ensure services are ready to receive traffic
- **Startup Probes**: Handle slow-starting containers
- **Custom Health Checks**: Application-specific health validation

## 📈 Scaling & Performance

### Horizontal Scaling
```bash
# Scale infrastructure components
kubectl scale statefulset postgres --replicas=5 -n iot
kubectl scale statefulset redis --replicas=5 -n iot

# Scale application components
kubectl scale deployment suggestion --replicas=10 -n iot
```

### Vertical Scaling
```bash
# Update resource limits
kubectl patch deployment suggestion -n iot -p '{"spec":{"template":{"spec":{"containers":[{"name":"suggestion","resources":{"limits":{"cpu":"2000m","memory":"2Gi"}}}]}}}}'
```

### Auto-scaling
- **HPA**: Horizontal Pod Autoscalers for CPU and memory
- **VPA**: Vertical Pod Autoscalers for resource optimization
- **Cluster Autoscaler**: Automatic node scaling based on demand

## 🚨 Troubleshooting

### Common Issues

#### Infrastructure Issues
```bash
# Check infrastructure status
./deploy/infra/deploy-infrastructure.sh status

# Check infrastructure logs
./deploy/infra/deploy-infrastructure.sh logs

# Run infrastructure tests
./deploy/infra/deploy-infrastructure.sh test
```

#### Application Issues
```bash
# Check application status
./deploy/suggestion/deploy.sh status

# Check application logs
./deploy/suggestion/deploy.sh logs

# Run application tests
./deploy/suggestion/deploy.sh test
```

#### Database Issues
```bash
# Check PostgreSQL status
kubectl exec -n iot deployment/postgres -- pg_isready

# Check Redis status
kubectl exec -n iot statefulset/redis -- redis-cli ping

# Check database connections
kubectl exec -n iot deployment/suggestion -- curl -f http://localhost:8300/healthz
```

#### Monitoring Issues
```bash
# Check Prometheus
kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/-/healthy

# Check Grafana
kubectl exec -n monitoring deployment/grafana -- wget -qO- http://localhost:3000/api/health

# Check alert manager
kubectl exec -n monitoring deployment/alertmanager -- wget -qO- http://localhost:9093/-/healthy
```

### Performance Issues
```bash
# Check resource usage
kubectl top pods --all-namespaces
kubectl top nodes

# Check persistent volumes
kubectl get pv,pvc --all-namespaces

# Check network policies
kubectl get networkpolicy --all-namespaces
```

### Security Issues
```bash
# Check RBAC
kubectl get roles,rolebindings --all-namespaces

# Check service accounts
kubectl get serviceaccounts --all-namespaces

# Check secrets
kubectl get secrets --all-namespaces
```

## 🔄 Maintenance

### Regular Maintenance Tasks
1. **Security Updates**: Monthly image updates and security patches
2. **Backup Verification**: Weekly backup restore tests
3. **Performance Tuning**: Quarterly resource optimization
4. **Certificate Renewal**: Automatic via cert-manager
5. **Log Rotation**: Automated log management and cleanup

### Update Procedures
```bash
# Update infrastructure
./deploy/infra/deploy-infrastructure.sh upgrade

# Update application
./deploy/suggestion/deploy.sh upgrade

# Update specific components
kubectl set image deployment/suggestion suggestion=ghcr.io/tethralai/tetheritall-suggestion:v1.1.0 -n iot
```

### Rollback Procedures
```bash
# Rollback infrastructure
./deploy/infra/deploy-infrastructure.sh rollback

# Rollback application
./deploy/suggestion/deploy.sh rollback

# Manual rollback
kubectl rollout undo deployment/suggestion -n iot
```

## 📚 Additional Resources

### Documentation
- [Infrastructure Deployment](./infra/README.md)
- [Suggestion Engine Deployment](./suggestion/README.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)

### Monitoring Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### Support
- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and help
- **Documentation**: Check the main project README for additional information

## 🎯 Success Metrics

### Infrastructure Health
- **Uptime**: > 99.9% availability
- **Response Time**: < 2s 95th percentile
- **Error Rate**: < 1% for all services
- **Resource Utilization**: < 80% CPU and memory

### Application Performance
- **Suggestion Generation**: < 5s average response time
- **User Engagement**: > 70% recommendation acceptance rate
- **System Reliability**: < 0.1% error rate
- **Scalability**: Support 10,000+ concurrent users

### Operational Excellence
- **Deployment Time**: < 15 minutes for complete deployment
- **Recovery Time**: < 5 minutes for service failures
- **Backup Success Rate**: > 99% successful backups
- **Security Compliance**: 100% of security policies enforced

### Cost Optimization
- **Resource Efficiency**: Optimal resource allocation
- **Storage Costs**: Minimized through proper sizing
- **Network Costs**: Optimized through efficient routing
- **Monitoring Overhead**: < 5% of total resource usage

## 🔮 Future Enhancements

### Planned Improvements
1. **Multi-Region Deployment**: Geographic distribution for global users
2. **Edge Computing**: Edge nodes for low-latency processing
3. **Advanced ML Infrastructure**: GPU support for ML workloads
4. **Service Mesh**: Istio integration for advanced traffic management

### Scalability Roadmap
1. **Database Sharding**: Horizontal scaling for massive datasets
2. **Microservices Architecture**: Further service decomposition
3. **Event-Driven Architecture**: Kafka integration for real-time processing
4. **Serverless Components**: AWS Lambda integration for cost optimization

---

**Note**: This deployment guide provides a complete solution for running the Tethral Suggestion Engine in production. For development or testing environments, use the development values files with reduced resource requirements.
