# Tethral Suggestion Engine - Deployment Guide

This guide covers the complete deployment process for the Tethral Suggestion Engine, from development setup to production deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Local Deployment](#local-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Production Configuration](#production-configuration)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security & Privacy](#security--privacy)
8. [Mobile Integration](#mobile-integration)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher
- **Kubernetes**: 1.24 or higher (for production)
- **Helm**: 3.12 or higher
- **Redis**: 7.0 or higher
- **PostgreSQL**: 14 or higher (for production)

### Required Services

- **Database**: PostgreSQL with CockroachDB compatibility
- **Cache**: Redis for session management and caching
- **Message Queue**: Redis or RabbitMQ for async processing
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or similar
- **Push Notifications**: Firebase Cloud Messaging (FCM) / Apple Push Notification Service (APNs)

## Development Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd tetheritall

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tetheritall

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
ENCRYPTION_KEY=your-32-byte-encryption-key
JWT_SECRET=your-jwt-secret

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Suggestion Engine
SUGGESTION_ENGINE_LOG_LEVEL=INFO
SUGGESTION_ENGINE_MAX_COMBINATIONS=1000
SUGGESTION_ENGINE_TIME_BUDGET_MS=5000
SUGGESTION_ENGINE_LLM_ENABLED=false

# Mobile Integration
FIREBASE_PROJECT_ID=your-firebase-project
FIREBASE_PRIVATE_KEY=your-firebase-private-key
APNS_KEY_ID=your-apns-key-id
APNS_TEAM_ID=your-apns-team-id
APNS_PRIVATE_KEY=your-apns-private-key
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py
```

### 4. Start Development Services

```bash
# Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Start PostgreSQL
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_DB=tetheritall \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  postgres:14

# Start the suggestion engine
uvicorn services.suggestion.api:app --reload --host 0.0.0.0 --port 8300
```

## Local Deployment

### Docker Compose

```bash
# Build and start all services
docker-compose -f deploy/compose/docker-compose.yml up -d

# View logs
docker-compose logs -f suggestion

# Stop services
docker-compose down
```

### Docker Compose Configuration

```yaml
# deploy/compose/docker-compose.yml
version: "3.9"
services:
  suggestion:
    build:
      context: .
      dockerfile: Dockerfile.suggestion
    ports:
      - "8300:8300"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/tetheritall
      - REDIS_URL=redis://redis:6379/0
      - SUGGESTION_ENGINE_LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8300/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Kubernetes Deployment

### 1. Prerequisites

```bash
# Install Helm dependencies
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace iot
```

### 2. Deploy Infrastructure

```bash
# Deploy PostgreSQL
helm install postgres deploy/helm/postgres \
  --namespace iot \
  --values deploy/helm/postgres/values.yaml

# Deploy Redis
helm install redis deploy/helm/redis \
  --namespace iot \
  --values deploy/helm/redis/values.yaml

# Deploy monitoring stack
helm install monitoring deploy/helm/monitoring \
  --namespace iot \
  --values deploy/helm/monitoring/values.yaml
```

### 3. Deploy Suggestion Engine

```bash
# Build and push Docker image
docker build -f Dockerfile.suggestion -t ghcr.io/tethralai/tetheritall-suggestion:latest .
docker push ghcr.io/tethralai/tetheritall-suggestion:latest

# Deploy using Helm
helm install suggestion deploy/helm/suggestion \
  --namespace iot \
  --values deploy/helm/suggestion/values.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n iot -l app=suggestion

# Check services
kubectl get svc -n iot -l app=suggestion

# Check logs
kubectl logs -n iot -l app=suggestion -f

# Port forward for testing
kubectl port-forward -n iot svc/suggestion 8300:8300
```

## Production Configuration

### 1. Production Values

```yaml
# deploy/helm/suggestion/values-prod.yaml
replicaCount: 3

image:
  repository: ghcr.io/tethralai/tetheritall-suggestion
  tag: "v1.0.0"
  pullPolicy: Always

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
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

env:
  LOG_LEVEL: WARNING
  MAX_COMBINATIONS: "2000"
  TIME_BUDGET_MS: "3000"
  LLM_ENABLED: "true"

# Security
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001

# Network policies
networkPolicy:
  enabled: true
  ingressRules:
    - from:
        - namespaceSelector:
            matchLabels:
              name: gateway
      ports:
        - protocol: TCP
          port: 8300

# Pod disruption budget
podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

### 2. Secrets Management

```bash
# Create secrets
kubectl create secret generic suggestion-secrets \
  --namespace iot \
  --from-literal=encryption-key=$(openssl rand -base64 32) \
  --from-literal=jwt-secret=$(openssl rand -base64 64) \
  --from-literal=database-url="postgresql://user:password@postgres:5432/tetheritall" \
  --from-literal=redis-url="redis://redis:6379/0"

# Create LLM API key secret
kubectl create secret generic suggestion-llm-secrets \
  --namespace iot \
  --from-literal=api-key="your-llm-api-key"
```

### 3. Ingress Configuration

```yaml
# deploy/helm/suggestion/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "suggestion.fullname" . }}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
    - hosts:
        - suggestion.tethral.ai
      secretName: suggestion-tls
  rules:
    - host: suggestion.tethral.ai
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "suggestion.fullname" . }}
                port:
                  number: 8300
```

## Monitoring & Observability

### 1. Prometheus Metrics

The suggestion engine exposes Prometheus metrics at `/metrics`:

```bash
# View metrics
curl http://localhost:8300/metrics

# Key metrics to monitor:
# - suggestion_requests_total
# - suggestion_response_time_seconds
# - suggestion_errors_total
# - suggestion_active_requests
# - suggestion_combinations_generated
# - suggestion_llm_calls_total
```

### 2. Grafana Dashboards

Create dashboards for:

- **Performance Metrics**: Response times, throughput, error rates
- **Business Metrics**: Suggestion acceptance rates, user engagement
- **System Metrics**: CPU, memory, disk usage
- **Security Metrics**: Failed authentication attempts, audit logs

### 3. Alerting Rules

```yaml
# deploy/helm/monitoring/templates/prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: suggestion-alerts
spec:
  groups:
    - name: suggestion-engine
      rules:
        - alert: HighErrorRate
          expr: rate(suggestion_errors_total[5m]) > 0.1
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: High error rate in suggestion engine
            
        - alert: HighResponseTime
          expr: histogram_quantile(0.95, suggestion_response_time_seconds) > 5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: High response time in suggestion engine
            
        - alert: ServiceDown
          expr: up{app="suggestion"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: Suggestion engine is down
```

### 4. Logging

Configure structured logging with correlation IDs:

```python
# Example log configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}
```

## Security & Privacy

### 1. Network Security

```yaml
# Network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: suggestion-network-policy
spec:
  podSelector:
    matchLabels:
      app: suggestion
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: gateway
      ports:
        - protocol: TCP
          port: 8300
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              name: redis
      ports:
        - protocol: TCP
          port: 6379
```

### 2. Data Encryption

- **At Rest**: Database encryption, volume encryption
- **In Transit**: TLS 1.3, mTLS for service-to-service communication
- **Application Level**: Field-level encryption for sensitive data

### 3. Access Control

```yaml
# RBAC configuration
apiVersion: rbac.authorization.k8s.io/v1
kind: ServiceAccount
metadata:
  name: suggestion-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: suggestion-role
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
    resourceNames: ["suggestion-secrets"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: suggestion-role-binding
subjects:
  - kind: ServiceAccount
    name: suggestion-sa
roleRef:
  kind: Role
  name: suggestion-role
  apiGroup: rbac.authorization.k8s.io
```

### 4. Privacy Compliance

- **GDPR**: Data export, deletion, consent management
- **CCPA**: Privacy rights, data disclosure
- **Data Retention**: Configurable retention policies
- **Audit Logging**: Complete audit trail

## Mobile Integration

### 1. Push Notification Setup

```bash
# Firebase Cloud Messaging
export FIREBASE_PROJECT_ID="your-project-id"
export FIREBASE_PRIVATE_KEY="your-private-key"

# Apple Push Notification Service
export APNS_KEY_ID="your-key-id"
export APNS_TEAM_ID="your-team-id"
export APNS_PRIVATE_KEY="your-private-key"
```

### 2. Mobile API Configuration

```yaml
# Mobile API settings
mobile:
  enabled: true
  pushNotifications:
    fcm:
      projectId: ${FIREBASE_PROJECT_ID}
      privateKey: ${FIREBASE_PRIVATE_KEY}
    apns:
      keyId: ${APNS_KEY_ID}
      teamId: ${APNS_TEAM_ID}
      privateKey: ${APNS_PRIVATE_KEY}
  rateLimiting:
    requestsPerMinute: 100
    burstSize: 20
```

### 3. Device Registration

```bash
# Register mobile device
curl -X POST http://localhost:8300/mobile/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "mobile-123",
    "user_id": "user-456",
    "device_type": "android",
    "push_token": "fcm-token-here",
    "app_version": "1.0.0",
    "os_version": "Android 13"
  }'
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   kubectl top pods -n iot -l app=suggestion
   
   # Increase memory limits
   kubectl patch deployment suggestion -n iot -p '{"spec":{"template":{"spec":{"containers":[{"name":"suggestion","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   kubectl exec -n iot deployment/suggestion -- nc -zv postgres 5432
   
   # Check database logs
   kubectl logs -n iot deployment/postgres
   ```

3. **Redis Connection Issues**
   ```bash
   # Check Redis connectivity
   kubectl exec -n iot deployment/suggestion -- redis-cli -h redis ping
   
   # Check Redis memory usage
   kubectl exec -n iot deployment/suggestion -- redis-cli -h redis info memory
   ```

### Debug Mode

```bash
# Enable debug logging
kubectl patch deployment suggestion -n iot -p '{"spec":{"template":{"spec":{"containers":[{"name":"suggestion","env":[{"name":"SUGGESTION_ENGINE_LOG_LEVEL","value":"DEBUG"}]}]}}}}'

# View debug logs
kubectl logs -n iot deployment/suggestion -f
```

### Performance Tuning

1. **Database Optimization**
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_suggestions_user_id ON suggestions(user_id);
   CREATE INDEX idx_suggestions_created_at ON suggestions(created_at);
   ```

2. **Redis Optimization**
   ```bash
   # Configure Redis for performance
   redis-cli config set maxmemory 2gb
   redis-cli config set maxmemory-policy allkeys-lru
   ```

3. **Application Tuning**
   ```yaml
   # Optimize for high throughput
   env:
     SUGGESTION_ENGINE_MAX_COMBINATIONS: "5000"
     SUGGESTION_ENGINE_TIME_BUDGET_MS: "2000"
     SUGGESTION_ENGINE_WORKER_PROCESSES: "4"
   ```

## Maintenance

### 1. Backup Strategy

```bash
# Database backup
kubectl exec -n iot deployment/postgres -- pg_dump -U user tetheritall > backup.sql

# Redis backup
kubectl exec -n iot deployment/redis -- redis-cli BGSAVE

# Configuration backup
kubectl get configmap suggestion-config -n iot -o yaml > config-backup.yaml
```

### 2. Updates and Rollouts

```bash
# Rolling update
kubectl set image deployment/suggestion suggestion=ghcr.io/tethralai/tetheritall-suggestion:v1.1.0 -n iot

# Rollback if needed
kubectl rollout undo deployment/suggestion -n iot

# Check rollout status
kubectl rollout status deployment/suggestion -n iot
```

### 3. Health Checks

```bash
# Automated health checks
kubectl get pods -n iot -l app=suggestion -o wide

# Manual health check
curl -f http://localhost:8300/healthz

# Load testing
k6 run load-tests/suggestion-engine.js
```

### 4. Capacity Planning

Monitor these metrics for capacity planning:

- **Request Rate**: Requests per second
- **Response Time**: P95, P99 response times
- **Error Rate**: Percentage of failed requests
- **Resource Usage**: CPU, memory, disk usage
- **Database Performance**: Query times, connection pool usage

### 5. Disaster Recovery

1. **Multi-Region Deployment**
2. **Database Replication**
3. **Backup and Restore Procedures**
4. **Incident Response Plan**

## Support

For deployment issues:

1. Check the logs: `kubectl logs -n iot deployment/suggestion`
2. Review monitoring dashboards
3. Check the troubleshooting section above
4. Contact the development team with logs and metrics

## Security Checklist

- [ ] Network policies configured
- [ ] RBAC permissions set
- [ ] Secrets properly managed
- [ ] TLS certificates configured
- [ ] Audit logging enabled
- [ ] Privacy compliance verified
- [ ] Security scanning completed
- [ ] Penetration testing performed
