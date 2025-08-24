# Tethral Infrastructure Deployment

This directory contains the infrastructure deployment scripts and Kubernetes manifests for the Tethral Suggestion Engine. The infrastructure provides all the foundational components needed to run the suggestion service in a production-ready environment.

## 🏗️ Architecture Overview

The infrastructure deployment includes:

### Core Infrastructure
- **Namespaces**: `iot`, `monitoring`, `ingress-nginx`, `cert-manager`, `chaos-testing`
- **Resource Quotas**: CPU and memory limits for the `iot` namespace
- **Network Policies**: Default deny-all with specific allow rules
- **Priority Classes**: Critical, standard, and low priority for pod scheduling

### Database Layer
- **PostgreSQL HA Cluster**: 3-node Patroni cluster with automatic failover
- **Redis Cluster**: 3-node Redis with Sentinel for high availability
- **Storage Classes**: AWS EBS storage classes (fast-ssd, standard-ssd, high-performance, backup-storage)

### Monitoring & Observability
- **Prometheus**: Metrics collection and storage
- **Grafana**: Dashboards and visualization
- **AlertManager**: Alert routing and notification
- **ServiceMonitors**: Automatic service discovery and monitoring

### Networking & Security
- **Nginx Ingress Controller**: Load balancing and SSL termination
- **Cert-Manager**: Automatic SSL certificate management with Let's Encrypt
- **Network Policies**: Pod-to-pod communication control
- **Load Balancers**: AWS Network Load Balancers for external access

### Backup & Disaster Recovery
- **Database Backups**: Automated daily PostgreSQL backups with S3 upload
- **Configuration Backups**: Automated backup of ConfigMaps, Secrets, and Deployments
- **Persistent Volumes**: Encrypted EBS volumes with KMS

### Chaos Engineering
- **Network Partition Testing**: Simulate network failures
- **Pod Failure Testing**: Test pod recreation and service resilience
- **Load Testing**: K6-based performance testing

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   - AWS EKS, GKE, AKS, or any compatible cluster
   - At least 4 CPU cores and 8GB RAM available

2. **kubectl** - Kubernetes command-line tool
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

3. **helm** - Kubernetes package manager
   ```bash
   # Install helm
   curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
   sudo mv linux-amd64/helm /usr/local/bin/
   ```

4. **AWS CLI** (for AWS-specific features)
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

### Deployment

#### Linux/macOS
```bash
# Make script executable
chmod +x deploy/infra/deploy-infrastructure.sh

# Deploy all infrastructure
./deploy/infra/deploy-infrastructure.sh deploy

# Deploy with specific options
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment prod \
  --namespace tethral-prod \
  --skip-monitoring
```

#### Windows PowerShell
```powershell
# Deploy all infrastructure
.\deploy\infra\deploy-infrastructure.ps1 deploy

# Deploy with specific options
.\deploy\infra\deploy-infrastructure.ps1 deploy `
  -Environment prod `
  -Namespace tethral-prod `
  -SkipMonitoring
```

## 📋 Available Commands

### Deploy Infrastructure
```bash
# Deploy all components
./deploy/infra/deploy-infrastructure.sh deploy

# Dry run (preview changes)
./deploy/infra/deploy-infrastructure.sh deploy --dry-run

# Production deployment
./deploy/infra/deploy-infrastructure.sh deploy --environment prod
```

### Check Status
```bash
# Show deployment status
./deploy/infra/deploy-infrastructure.sh status

# Show logs
./deploy/infra/deploy-infrastructure.sh logs

# Run health checks
./deploy/infra/deploy-infrastructure.sh test
```

### Manage Infrastructure
```bash
# Upgrade existing deployment
./deploy/infra/deploy-infrastructure.sh upgrade

# Uninstall all components
./deploy/infra/deploy-infrastructure.sh uninstall
```

## ⚙️ Configuration Options

### Environment Variables
- `NAMESPACE`: Kubernetes namespace (default: `iot`)
- `ENVIRONMENT`: Environment type (default: `dev`)
- `SKIP_MONITORING`: Skip monitoring stack deployment
- `SKIP_INGRESS`: Skip ingress controller deployment
- `SKIP_CERT_MANAGER`: Skip cert-manager deployment
- `DRY_RUN`: Preview changes without applying

### Environment-Specific Configurations

#### Development
```bash
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment dev \
  --skip-monitoring
```

#### Staging
```bash
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment staging
```

#### Production
```bash
./deploy/infra/deploy-infrastructure.sh deploy \
  --environment prod \
  --namespace tethral-prod
```

## 🔧 Component Details

### PostgreSQL HA Cluster
- **Replicas**: 3 nodes with Patroni
- **Storage**: 10GB encrypted EBS volumes per node
- **Backup**: Daily automated backups to S3
- **Failover**: Automatic leader election and failover

### Redis Cluster
- **Replicas**: 3 nodes with Sentinel
- **Storage**: 1GB encrypted EBS volumes per node
- **Memory**: 512MB per node with LRU eviction
- **Persistence**: AOF with every-second fsync

### Monitoring Stack
- **Prometheus**: 10GB storage, 15s scrape interval
- **Grafana**: 5GB storage, admin/admin credentials
- **AlertManager**: Webhook notifications
- **Dashboards**: Pre-configured for infrastructure monitoring

### Ingress Controller
- **Replicas**: 2 nodes for high availability
- **SSL**: Automatic certificate management
- **Rate Limiting**: 100 requests per minute per IP
- **Load Balancing**: Round-robin with health checks

## 🔒 Security Features

### Network Security
- **Default Deny**: All pod-to-pod communication blocked by default
- **DNS Access**: Only DNS resolution allowed for all pods
- **Service Access**: Explicit allow rules for required services
- **External Access**: HTTPS-only with rate limiting

### Data Security
- **Encryption**: All EBS volumes encrypted with KMS
- **Secrets**: Kubernetes secrets for sensitive data
- **RBAC**: Minimal required permissions for all service accounts
- **Audit Logging**: Enabled for all API operations

### Certificate Management
- **Automatic SSL**: Let's Encrypt certificates for all domains
- **Certificate Renewal**: Automatic renewal before expiration
- **Staging Environment**: Uses Let's Encrypt staging for testing

## 📊 Monitoring & Alerting

### Metrics Collected
- **Infrastructure**: CPU, memory, disk usage
- **Applications**: Request rate, response time, error rate
- **Databases**: Connection count, query performance
- **Networking**: Bandwidth, latency, packet loss

### Pre-configured Alerts
- **Service Down**: Critical alert when services are unavailable
- **High Error Rate**: Warning when error rate exceeds 10%
- **High Response Time**: Warning when 95th percentile > 2s
- **Resource Usage**: Warning when CPU/memory > 80%
- **Certificate Expiry**: Warning 30 days before expiration

### Dashboards
- **Infrastructure Overview**: Cluster health and resource usage
- **Application Metrics**: Request rates and performance
- **Database Performance**: Query times and connection stats
- **Network Monitoring**: Traffic patterns and errors

## 🔄 Backup & Recovery

### Automated Backups
- **Database**: Daily PostgreSQL dumps with compression
- **Configuration**: Daily backup of all K8s resources
- **Storage**: Encrypted backups stored in S3
- **Retention**: 7 days for daily backups, 30 days for weekly

### Recovery Procedures
1. **Database Recovery**: Restore from S3 backup
2. **Configuration Recovery**: Apply backed-up manifests
3. **Full Cluster Recovery**: Recreate cluster and restore data

## 🧪 Chaos Engineering

### Available Tests
- **Network Partition**: Simulate network failures between services
- **Pod Failure**: Delete pods and verify automatic recreation
- **Load Testing**: K6-based performance testing with realistic scenarios

### Running Tests
```bash
# Run all chaos tests
kubectl create -f deploy/infra/k8s/chaos-engineering.yaml

# Monitor test results
kubectl logs -n chaos-testing job/network-partition-test
kubectl logs -n chaos-testing job/pod-failure-test
kubectl logs -n chaos-testing job/load-test
```

## 🚨 Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -n iot

# Check pod events
kubectl describe pod <pod-name> -n iot

# Check pod logs
kubectl logs <pod-name> -n iot
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
kubectl exec -n iot deployment/postgres -- pg_isready

# Check Redis status
kubectl exec -n iot statefulset/redis -- redis-cli ping

# Check service endpoints
kubectl get endpoints -n iot
```

#### Monitoring Issues
```bash
# Check Prometheus status
kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/-/healthy

# Check Grafana status
kubectl exec -n monitoring deployment/grafana -- wget -qO- http://localhost:3000/api/health

# Check alert manager
kubectl exec -n monitoring deployment/alertmanager -- wget -qO- http://localhost:9093/-/healthy
```

#### Ingress Issues
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress rules
kubectl get ingress --all-namespaces

# Check SSL certificates
kubectl get certificates --all-namespaces
```

### Log Analysis
```bash
# Get logs from all components
./deploy/infra/deploy-infrastructure.sh logs

# Follow logs in real-time
kubectl logs -f deployment/postgres -n iot
kubectl logs -f deployment/prometheus -n monitoring
```

### Performance Issues
```bash
# Check resource usage
kubectl top pods --all-namespaces

# Check node resources
kubectl top nodes

# Check persistent volume usage
kubectl get pv,pvc --all-namespaces
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale PostgreSQL (requires manual configuration)
kubectl scale statefulset postgres --replicas=5 -n iot

# Scale Redis
kubectl scale statefulset redis --replicas=5 -n iot

# Scale monitoring
kubectl scale deployment prometheus --replicas=3 -n monitoring
```

### Vertical Scaling
```bash
# Update resource limits
kubectl patch deployment postgres -n iot -p '{"spec":{"template":{"spec":{"containers":[{"name":"patroni","resources":{"limits":{"cpu":"2000m","memory":"4Gi"}}}]}}}}'
```

## 🔄 Maintenance

### Regular Maintenance Tasks
1. **Certificate Renewal**: Automatic via cert-manager
2. **Backup Verification**: Weekly backup restore tests
3. **Security Updates**: Monthly image updates
4. **Performance Tuning**: Quarterly resource optimization

### Update Procedures
```bash
# Update infrastructure
./deploy/infra/deploy-infrastructure.sh upgrade

# Update specific components
kubectl set image deployment/postgres patroni=quay.io/zalando/patroni:3.3.3 -n iot
kubectl set image deployment/prometheus prometheus=prom/prometheus:v2.46.0 -n monitoring
```

## 📚 Additional Resources

### Documentation
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

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

### Operational Excellence
- **Deployment Time**: < 10 minutes for full infrastructure
- **Recovery Time**: < 5 minutes for service failures
- **Backup Success Rate**: > 99% successful backups
- **Security Compliance**: 100% of security policies enforced

### Cost Optimization
- **Resource Efficiency**: Optimal resource allocation
- **Storage Costs**: Minimized through proper sizing
- **Network Costs**: Optimized through efficient routing
- **Monitoring Overhead**: < 5% of total resource usage
