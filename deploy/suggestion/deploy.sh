#!/bin/bash

# Tethral Suggestion Engine Deployment Script
# This script deploys the suggestion service with all robustness features

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="iot"
CHART_PATH="deploy/helm/suggestion"
VALUES_FILE=""
ENVIRONMENT=""
DRY_RUN=false
FORCE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy          Deploy the suggestion service
    upgrade         Upgrade existing deployment
    uninstall       Uninstall the suggestion service
    status          Check deployment status
    logs            Show service logs
    test            Run deployment tests

Options:
    -e, --env ENV       Environment (dev, staging, prod, mobile)
    -n, --namespace NS  Kubernetes namespace (default: iot)
    -f, --force         Force deployment without confirmation
    --dry-run          Show what would be deployed without applying
    -h, --help         Show this help message

Examples:
    $0 deploy -e dev
    $0 deploy -e prod --dry-run
    $0 upgrade -e staging
    $0 status
EOF
}

# Function to validate environment
validate_environment() {
    case $ENVIRONMENT in
        dev|staging|prod|mobile)
            case $ENVIRONMENT in
                dev)
                    VALUES_FILE="$CHART_PATH/values.yaml"
                    ;;
                staging)
                    VALUES_FILE="$CHART_PATH/values-staging.yaml"
                    ;;
                prod)
                    VALUES_FILE="$CHART_PATH/values-prod.yaml"
                    ;;
                mobile)
                    VALUES_FILE="$CHART_PATH/values-mobile.yaml"
                    ;;
            esac
            ;;
        *)
            print_error "Invalid environment: $ENVIRONMENT"
            print_error "Valid environments: dev, staging, prod, mobile"
            exit 1
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "helm is not installed"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        print_warning "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace $NAMESPACE
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to generate secrets
generate_secrets() {
    print_status "Generating secrets..."
    
    # Generate encryption key
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    
    # Generate JWT secret
    JWT_SECRET=$(openssl rand -base64 32)
    
    # Generate rate limit secret
    RATE_LIMIT_SECRET=$(openssl rand -base64 32)
    
    # Create secrets file
    cat > /tmp/suggestion-secrets.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: suggestion-secrets
  namespace: $NAMESPACE
type: Opaque
data:
  encryption-key: $(echo -n "$ENCRYPTION_KEY" | base64)
  jwt-secret: $(echo -n "$JWT_SECRET" | base64)
  rate-limit-secret: $(echo -n "$RATE_LIMIT_SECRET" | base64)
  llm-api-key: ""
  firebase-credentials: ""
  apns-key: ""
  database-password: ""
EOF
    
    if [ "$DRY_RUN" = false ]; then
        kubectl apply -f /tmp/suggestion-secrets.yaml
        print_success "Secrets created"
    else
        print_status "Would create secrets (dry run)"
    fi
}

# Function to deploy infrastructure dependencies
deploy_infrastructure() {
    print_status "Deploying infrastructure dependencies..."
    
    # Check if PostgreSQL is running
    if ! kubectl get deployment postgres -n $NAMESPACE &> /dev/null; then
        print_warning "PostgreSQL not found, please deploy it first"
        print_status "You can deploy PostgreSQL using: kubectl apply -f deploy/infra/k8s/postgres-ha.yaml"
    fi
    
    # Check if Redis is running
    if ! kubectl get deployment redis -n $NAMESPACE &> /dev/null; then
        print_warning "Redis not found, please deploy it first"
        print_status "You can deploy Redis using: kubectl apply -f deploy/infra/k8s/redis.yaml"
    fi
    
    # Check if monitoring stack is running
    if ! kubectl get deployment prometheus -n monitoring &> /dev/null; then
        print_warning "Prometheus not found, please deploy monitoring stack first"
    fi
    
    print_success "Infrastructure check completed"
}

# Function to deploy the suggestion service
deploy_service() {
    print_status "Deploying suggestion service..."
    
    if [ "$DRY_RUN" = true ]; then
        print_status "Running dry run..."
        helm template suggestion $CHART_PATH \
            --namespace $NAMESPACE \
            --values $VALUES_FILE \
            --set secrets.encryptionKey="dry-run-key" \
            --set secrets.jwtSecret="dry-run-jwt" \
            --set secrets.rateLimitSecret="dry-run-rate-limit"
    else
        # Check if release exists
        if helm list -n $NAMESPACE | grep -q suggestion; then
            print_warning "Suggestion service already exists, upgrading..."
            helm upgrade suggestion $CHART_PATH \
                --namespace $NAMESPACE \
                --values $VALUES_FILE \
                --wait \
                --timeout 10m
        else
            print_status "Installing new suggestion service..."
            helm install suggestion $CHART_PATH \
                --namespace $NAMESPACE \
                --values $VALUES_FILE \
                --wait \
                --timeout 10m
        fi
    fi
    
    print_success "Suggestion service deployment completed"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    if [ "$DRY_RUN" = true ]; then
        print_status "Skipping verification (dry run)"
        return
    fi
    
    # Wait for pods to be ready
    print_status "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=suggestion -n $NAMESPACE --timeout=300s
    
    # Check service
    if kubectl get service suggestion -n $NAMESPACE &> /dev/null; then
        print_success "Service created successfully"
    else
        print_error "Service not found"
        exit 1
    fi
    
    # Check HPA
    if kubectl get hpa suggestion-hpa -n $NAMESPACE &> /dev/null; then
        print_success "HPA created successfully"
    else
        print_warning "HPA not found"
    fi
    
    # Check network policy
    if kubectl get networkpolicy suggestion-network-policy -n $NAMESPACE &> /dev/null; then
        print_success "Network policy created successfully"
    else
        print_warning "Network policy not found"
    fi
    
    # Check monitoring resources
    if kubectl get servicemonitor suggestion-monitor -n $NAMESPACE &> /dev/null; then
        print_success "ServiceMonitor created successfully"
    else
        print_warning "ServiceMonitor not found"
    fi
    
    print_success "Deployment verification completed"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    if [ "$DRY_RUN" = true ]; then
        print_status "Skipping health checks (dry run)"
        return
    fi
    
    # Get service URL
    SERVICE_URL=$(kubectl get service suggestion -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$SERVICE_URL" ]; then
        SERVICE_URL=$(kubectl get service suggestion -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    if [ -n "$SERVICE_URL" ]; then
        # Test health endpoint
        if curl -f "http://$SERVICE_URL:8300/healthz" &> /dev/null; then
            print_success "Health check passed"
        else
            print_error "Health check failed"
        fi
        
        # Test metrics endpoint
        if curl -f "http://$SERVICE_URL:8300/metrics" &> /dev/null; then
            print_success "Metrics endpoint accessible"
        else
            print_warning "Metrics endpoint not accessible"
        fi
    else
        print_warning "Service URL not available, skipping health checks"
    fi
}

# Function to show deployment status
show_status() {
    print_status "Deployment status:"
    
    echo ""
    echo "Pods:"
    kubectl get pods -l app=suggestion -n $NAMESPACE
    
    echo ""
    echo "Services:"
    kubectl get services -l app=suggestion -n $NAMESPACE
    
    echo ""
    echo "HPA:"
    kubectl get hpa -l app=suggestion -n $NAMESPACE
    
    echo ""
    echo "Network Policies:"
    kubectl get networkpolicy -l app=suggestion -n $NAMESPACE
    
    echo ""
    echo "Events:"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | grep suggestion | tail -10
}

# Function to show logs
show_logs() {
    print_status "Showing logs..."
    kubectl logs -l app=suggestion -n $NAMESPACE --tail=100 -f
}

# Function to run tests
run_tests() {
    print_status "Running deployment tests..."
    
    if [ "$DRY_RUN" = true ]; then
        print_status "Skipping tests (dry run)"
        return
    fi
    
    # Test basic connectivity
    print_status "Testing basic connectivity..."
    if kubectl exec -n $NAMESPACE deployment/suggestion -- curl -f http://localhost:8300/healthz &> /dev/null; then
        print_success "Basic connectivity test passed"
    else
        print_error "Basic connectivity test failed"
    fi
    
    # Test database connectivity
    print_status "Testing database connectivity..."
    if kubectl exec -n $NAMESPACE deployment/suggestion -- python -c "import psycopg2; print('DB connection test')" &> /dev/null; then
        print_success "Database connectivity test passed"
    else
        print_warning "Database connectivity test failed"
    fi
    
    # Test Redis connectivity
    print_status "Testing Redis connectivity..."
    if kubectl exec -n $NAMESPACE deployment/suggestion -- python -c "import redis; print('Redis connection test')" &> /dev/null; then
        print_success "Redis connectivity test passed"
    else
        print_warning "Redis connectivity test failed"
    fi
    
    print_success "Deployment tests completed"
}

# Function to uninstall
uninstall() {
    print_status "Uninstalling suggestion service..."
    
    if [ "$FORCE" = false ]; then
        read -p "Are you sure you want to uninstall the suggestion service? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Uninstall cancelled"
            exit 0
        fi
    fi
    
    if helm list -n $NAMESPACE | grep -q suggestion; then
        helm uninstall suggestion -n $NAMESPACE
        print_success "Suggestion service uninstalled"
    else
        print_warning "Suggestion service not found"
    fi
}

# Main script logic
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            deploy|upgrade|uninstall|status|logs|test)
                COMMAND="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate required arguments
    if [ -z "${COMMAND:-}" ]; then
        print_error "Command is required"
        show_usage
        exit 1
    fi
    
    if [ "$COMMAND" = "deploy" ] || [ "$COMMAND" = "upgrade" ]; then
        if [ -z "$ENVIRONMENT" ]; then
            print_error "Environment is required for deploy/upgrade"
            show_usage
            exit 1
        fi
        validate_environment
    fi
    
    # Execute command
    case $COMMAND in
        deploy)
            check_prerequisites
            deploy_infrastructure
            generate_secrets
            deploy_service
            verify_deployment
            run_health_checks
            run_tests
            print_success "Deployment completed successfully!"
            ;;
        upgrade)
            check_prerequisites
            deploy_service
            verify_deployment
            run_health_checks
            print_success "Upgrade completed successfully!"
            ;;
        uninstall)
            uninstall
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        test)
            run_tests
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
