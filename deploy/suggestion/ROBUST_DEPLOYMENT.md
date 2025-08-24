# Tethral Suggestion Engine - Robust Deployment Guide

This guide provides comprehensive instructions for deploying the Tethral Suggestion Engine with enterprise-grade robustness, security, and scalability to withstand real-world usage.

## 🎯 Overview

The Tethral Suggestion Engine is designed to be deployed with the following robustness features:

- **High Availability**: Multi-replica deployments with auto-scaling
- **Security**: Network policies, RBAC, encryption, audit logging
- **Monitoring**: Prometheus metrics, Grafana dashboards, alerting
- **Mobile Integration**: Push notifications, device management
- **Performance**: Optimized resource allocation and caching
- **Compliance**: GDPR/CCPA compliance with data privacy controls

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Gateway   │    │   Mobile Apps   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Suggestion     │
                    │  Engine         │
                    │  (3-20 replicas)│
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   Monitoring    │
│   (HA Cluster)  │    │   (Sentinel)    │    │   Stack         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster** (v1.24+)
2. **Helm** (v3.8+)
3. **kubectl** (v1.24+)
4. **PostgreSQL** (HA cluster)
5. **Redis** (with Sentinel)
6. **Monitoring Stack** (Prometheus, Grafana, AlertManager)

### 1. Infrastructure Setup

```bash
# Deploy PostgreSQL HA cluster
kubectl apply -f deploy/infra/k8s/postgres-ha.yaml

# Deploy Redis with Sentinel
kubectl apply -f deploy/infra/k8s/redis.yaml

# Deploy monitoring stack
kubectl apply -f deploy/infra/k8s/monitoring.yaml
```

### 2. Deploy Suggestion Engine

#### Using Deployment Script (Recommended)

```bash
# Linux/macOS
./deploy/suggestion/deploy.sh deploy -e prod

# Windows PowerShell
.\deploy/suggestion/deploy.ps1 -Command deploy -Environment prod
```

#### Using Helm Directly

```bash
# Deploy with production values
helm install suggestion deploy/helm/suggestion \
  --namespace iot \
  --values deploy/helm/suggestion/values-prod.yaml

# Or for mobile integration
helm install suggestion deploy/helm/suggestion \
  --namespace iot \
  --values deploy/helm/suggestion/values-mobile.yaml
```

## 🔧 Configuration

### Environment-Specific Values

| Environment | File | Replicas | Resources | Features |
|-------------|------|----------|-----------|----------|
| Development | `values.yaml` | 2 | 200m/256Mi | Basic features |
| Staging | `values-staging.yaml` | 3 | 300m/384Mi | Full features |
| Production | `values-prod.yaml` | 3-20 | 500m/512Mi | All features + HA |
| Mobile | `values-mobile.yaml` | 2-15 | 300m/384Mi | Mobile features |

### Key Configuration Options

```yaml
# Production configuration example
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

env:
  REDIS_URL: redis://redis-cluster:6379/0
  LOG_LEVEL: INFO
  MAX_COMBINATIONS: "2000"
  TIME_BUDGET_MS: "8000"
  LLM_ENABLED: "true"
  ENVIRONMENT: "production"
  METRICS_ENABLED: "true"
  TRACING_ENABLED: "true"
```

## 🔒 Security Configuration

### 1. Network Policies

The deployment includes strict network policies:

```yaml
# Only allow traffic from API Gateway and health checks
ingress:
  - from:
      - podSelector:
          matchLabels:
            app: api-gateway
    ports:
      - protocol: TCP
        port: 8300
```

### 2. RBAC Configuration

Service account with minimal required permissions:

```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    resourceNames: ["suggestion-config", "suggestion-secrets"]
    verbs: ["get", "list", "watch"]
```

### 3. Secrets Management

Generate secure secrets:

```bash
# Generate encryption keys
ENCRYPTION_KEY=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
RATE_LIMIT_SECRET=$(openssl rand -base64 32)

# Create Kubernetes secret
kubectl create secret generic suggestion-secrets \
  --from-literal=encryption-key="$ENCRYPTION_KEY" \
  --from-literal=jwt-secret="$JWT_SECRET" \
  --from-literal=rate-limit-secret="$RATE_LIMIT_SECRET"
```

## 📊 Monitoring & Observability

### 1. Prometheus Metrics

The service exposes comprehensive metrics:

- `suggestion_requests_total` - Total request count
- `suggestion_response_time_seconds` - Response time histogram
- `suggestion_errors_total` - Error count by type
- `suggestion_combinations_generated` - Generated combinations
- `suggestion_llm_calls_total` - LLM API calls

### 2. Grafana Dashboard

Pre-configured dashboard with panels for:
- Request rate and response times
- Error rates and types
- Resource utilization
- Business metrics (suggestion acceptance)

### 3. Alerting Rules

Automated alerts for:
- High error rate (>10% for 2 minutes)
- High response time (>2s 95th percentile)
- Service down
- High resource usage (>80% CPU/memory)
- Low suggestion generation rate

## 📱 Mobile Integration

### 1. Push Notifications

Configure Firebase Cloud Messaging (FCM) for Android:

```yaml
secrets:
  firebaseCredentials: |
    {
      "type": "service_account",
      "project_id": "your-project-id",
      "private_key_id": "...",
      "private_key": "...",
      "client_email": "...",
      "client_id": "..."
    }
```

Configure Apple Push Notification Service (APNs) for iOS:

```yaml
secrets:
  apnsKey: |
    -----BEGIN PRIVATE KEY-----
    MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
    -----END PRIVATE KEY-----
```

### 2. Device Management

The service supports:
- Device registration and authentication
- Push token management
- Offline suggestion caching
- Background sync capabilities

## 🔄 High Availability

### 1. Pod Disruption Budget

Ensures minimum availability during updates:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: suggestion
```

### 2. Anti-Affinity Rules

Distribute pods across nodes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values: ["suggestion"]
          topologyKey: kubernetes.io/hostname
```

### 3. Auto-scaling

Horizontal Pod Autoscaler with custom metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## 🧪 Testing & Validation

### 1. Health Checks

The service includes comprehensive health checks:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8300
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /readyz
    port: 8300
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### 2. Load Testing

Run performance tests:

```bash
# Using k6 for load testing
k6 run deploy/k6/enhanced_load.js

# Or using the built-in test command
./deploy/suggestion/deploy.sh test
```

### 3. Chaos Engineering

Test resilience with chaos experiments:

```bash
# Deploy chaos experiments
kubectl apply -f deploy/chaos/experiments.yaml

# Run network partition test
kubectl apply -f deploy/chaos/network-partition.yaml
```

## 🔧 Maintenance & Operations

### 1. Rolling Updates

```bash
# Update to new version
helm upgrade suggestion deploy/helm/suggestion \
  --namespace iot \
  --values deploy/helm/suggestion/values-prod.yaml \
  --set image.tag=v1.1.0
```

### 2. Scaling

```bash
# Scale manually
kubectl scale deployment suggestion -n iot --replicas=5

# Or let HPA handle it automatically
kubectl get hpa suggestion-hpa -n iot
```

### 3. Monitoring

```bash
# Check service status
./deploy/suggestion/deploy.sh status

# View logs
./deploy/suggestion/deploy.sh logs

# Access Grafana dashboard
kubectl port-forward svc/grafana 3000:3000 -n monitoring
```

### 4. Backup & Recovery

```bash
# Backup PostgreSQL data
kubectl exec -n iot deployment/postgres -- pg_dump -U postgres tethral > backup.sql

# Restore from backup
kubectl exec -n iot deployment/postgres -- psql -U postgres tethral < backup.sql
```

## 🚨 Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod -l app=suggestion -n iot
   kubectl logs -l app=suggestion -n iot
   ```

2. **High memory usage**
   ```bash
   kubectl top pods -l app=suggestion -n iot
   kubectl exec -n iot deployment/suggestion -- python -c "import gc; gc.collect()"
   ```

3. **Database connection issues**
   ```bash
   kubectl exec -n iot deployment/suggestion -- python -c "import psycopg2; print('DB test')"
   ```

4. **Redis connection issues**
   ```bash
   kubectl exec -n iot deployment/suggestion -- python -c "import redis; print('Redis test')"
   ```

### Performance Tuning

1. **Adjust resource limits**
   ```yaml
   resources:
     requests:
       cpu: 1000m
       memory: 1Gi
     limits:
       cpu: 4000m
       memory: 4Gi
   ```

2. **Optimize combination generation**
   ```yaml
   env:
     MAX_COMBINATIONS: "5000"
     TIME_BUDGET_MS: "10000"
   ```

3. **Enable caching**
   ```yaml
   env:
     REDIS_CACHE_TTL: "3600"
     ENABLE_COMBINATION_CACHE: "true"
   ```

## 📈 Success Metrics

Monitor these key performance indicators:

### Performance Metrics
- **Response Time**: <2s average, <5s 95th percentile
- **Throughput**: >1000 requests/second
- **Uptime**: >99.9%
- **Error Rate**: <1%

### Business Metrics
- **Suggestion Acceptance Rate**: >60%
- **User Engagement**: >80% daily active users
- **Mobile App Usage**: >70% of total requests

### Resource Utilization
- **CPU Usage**: <70% average
- **Memory Usage**: <80% average
- **Database Connections**: <80% of pool size

## 🔮 Future Enhancements

1. **Multi-region Deployment**
   - Geographic distribution
   - Cross-region failover
   - Edge computing integration

2. **Advanced ML Features**
   - Real-time model updates
   - A/B testing framework
   - Personalized recommendations

3. **Enhanced Security**
   - Zero-trust architecture
   - Advanced threat detection
   - Compliance automation

4. **Performance Optimization**
   - GraphQL API
   - Real-time streaming
   - Advanced caching strategies

## 📞 Support

For deployment issues or questions:

1. Check the logs: `./deploy/suggestion/deploy.sh logs`
2. Review monitoring dashboards
3. Consult the troubleshooting section
4. Contact the DevOps team

---

**Note**: This deployment configuration is designed for production use and includes all robustness features. For development or testing environments, use the appropriate values files with reduced resource requirements.
