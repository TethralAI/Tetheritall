#!/bin/bash

# Tethral Infrastructure Deployment Script
# This script deploys all foundational infrastructure components

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
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

# Usage function
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  deploy     - Deploy all infrastructure components"
    echo "  upgrade    - Upgrade existing infrastructure"
    echo "  uninstall  - Remove all infrastructure components"
    echo "  status     - Show deployment status"
    echo "  logs       - Show logs for all components"
    echo "  test       - Run infrastructure tests"
    echo ""
    echo "Options:"
    echo "  --namespace NAMESPACE  - Kubernetes namespace (default: iot)"
    echo "  --environment ENV      - Environment (dev/staging/prod, default: dev)"
    echo "  --skip-monitoring      - Skip monitoring stack deployment"
    echo "  --skip-ingress         - Skip ingress controller deployment"
    echo "  --skip-cert-manager    - Skip cert-manager deployment"
    echo "  --dry-run              - Show what would be deployed without applying"
    echo "  --help                 - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy --environment prod"
    echo "  $0 status"
    echo "  $0 uninstall"
}

# Default values
NAMESPACE="iot"
ENVIRONMENT="dev"
SKIP_MONITORING=false
SKIP_INGRESS=false
SKIP_CERT_MANAGER=false
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        deploy|upgrade|uninstall|status|logs|test)
            COMMAND="$1"
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-monitoring)
            SKIP_MONITORING=true
            shift
            ;;
        --skip-ingress)
            SKIP_INGRESS=true
            shift
            ;;
        --skip-cert-manager)
            SKIP_CERT_MANAGER=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate command
if [[ -z "${COMMAND:-}" ]]; then
    print_error "No command specified"
    usage
    exit 1
fi

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "helm is not installed. Please install helm first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create namespaces
create_namespaces() {
    print_info "Creating namespaces..."
    
    local namespaces=("$NAMESPACE" "monitoring" "ingress-nginx" "cert-manager" "chaos-testing")
    
    for ns in "${namespaces[@]}"; do
        if kubectl get namespace "$ns" &> /dev/null; then
            print_info "Namespace $ns already exists"
        else
            if [[ "$DRY_RUN" == "true" ]]; then
                print_info "Would create namespace: $ns"
            else
                kubectl create namespace "$ns"
                print_success "Created namespace: $ns"
            fi
        fi
    done
}

# Function to deploy complete infrastructure
deploy_complete_infrastructure() {
    print_info "Deploying complete infrastructure..."
    
    local manifest_file="deploy/infra/k8s/complete-infrastructure.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Infrastructure manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply infrastructure manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied infrastructure manifest"
    fi
}

# Function to deploy PostgreSQL
deploy_postgres() {
    print_info "Deploying PostgreSQL..."
    
    local manifest_file="deploy/infra/k8s/postgres-ha.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "PostgreSQL manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply PostgreSQL manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied PostgreSQL manifest"
    fi
}

# Function to deploy monitoring stack
deploy_monitoring() {
    if [[ "$SKIP_MONITORING" == "true" ]]; then
        print_info "Skipping monitoring stack deployment"
        return
    fi
    
    print_info "Deploying monitoring stack..."
    
    local manifest_file="deploy/infra/k8s/monitoring-stack.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Monitoring manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply monitoring manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied monitoring manifest"
    fi
}

# Function to deploy ingress controller
deploy_ingress() {
    if [[ "$SKIP_INGRESS" == "true" ]]; then
        print_info "Skipping ingress controller deployment"
        return
    fi
    
    print_info "Deploying Nginx Ingress Controller..."
    
    local manifest_file="deploy/infra/k8s/ingress-controller.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Ingress manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply ingress manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied ingress manifest"
    fi
}

# Function to deploy cert-manager
deploy_cert_manager() {
    if [[ "$SKIP_CERT_MANAGER" == "true" ]]; then
        print_info "Skipping cert-manager deployment"
        return
    fi
    
    print_info "Deploying cert-manager..."
    
    local manifest_file="deploy/infra/k8s/cert-manager.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Cert-manager manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply cert-manager manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied cert-manager manifest"
    fi
}

# Function to deploy storage classes
deploy_storage() {
    print_info "Deploying storage classes..."
    
    local manifest_file="deploy/infra/k8s/storage-class.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Storage manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply storage manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied storage manifest"
    fi
}

# Function to deploy load balancers
deploy_load_balancers() {
    print_info "Deploying load balancers..."
    
    local manifest_file="deploy/infra/k8s/load-balancer.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Load balancer manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply load balancer manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied load balancer manifest"
    fi
}

# Function to deploy backup jobs
deploy_backup_jobs() {
    print_info "Deploying backup jobs..."
    
    local manifest_file="deploy/infra/k8s/backup-cronjob.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Backup manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply backup manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied backup manifest"
    fi
}

# Function to deploy chaos engineering
deploy_chaos_engineering() {
    print_info "Deploying chaos engineering components..."
    
    local manifest_file="deploy/infra/k8s/chaos-engineering.yaml"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Chaos engineering manifest not found: $manifest_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Would apply chaos engineering manifest (dry run)"
        kubectl apply -f "$manifest_file" --dry-run=client
    else
        kubectl apply -f "$manifest_file"
        print_success "Applied chaos engineering manifest"
    fi
}

# Function to wait for deployments
wait_for_deployments() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Skipping deployment wait (dry run)"
        return
    fi
    
    print_info "Waiting for deployments to be ready..."
    
    # Wait for PostgreSQL
    print_info "Waiting for PostgreSQL..."
    kubectl wait --for=condition=available --timeout=300s deployment/postgres -n "$NAMESPACE" || {
        print_warning "PostgreSQL deployment not ready within timeout"
    }
    
    # Wait for Redis
    print_info "Waiting for Redis..."
    kubectl wait --for=condition=available --timeout=300s statefulset/redis -n "$NAMESPACE" || {
        print_warning "Redis deployment not ready within timeout"
    }
    
    # Wait for monitoring components
    if [[ "$SKIP_MONITORING" == "false" ]]; then
        print_info "Waiting for monitoring components..."
        kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring || {
            print_warning "Prometheus deployment not ready within timeout"
        }
        kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring || {
            print_warning "Grafana deployment not ready within timeout"
        }
    fi
    
    # Wait for ingress controller
    if [[ "$SKIP_INGRESS" == "false" ]]; then
        print_info "Waiting for ingress controller..."
        kubectl wait --for=condition=available --timeout=300s deployment/nginx-ingress-controller -n ingress-nginx || {
            print_warning "Ingress controller deployment not ready within timeout"
        }
    fi
    
    print_success "Deployment wait completed"
}

# Function to verify deployment
verify_deployment() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "Skipping deployment verification (dry run)"
        return
    fi
    
    print_info "Verifying deployment..."
    
    # Check if all pods are running
    local failed_pods=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded | grep -v "NAMESPACE" | wc -l)
    
    if [[ "$failed_pods" -gt 0 ]]; then
        print_warning "Found $failed_pods pods not in Running state"
        kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded
    else
        print_success "All pods are running"
    fi
    
    # Check services
    print_info "Checking services..."
    kubectl get services -n "$NAMESPACE"
    
    # Check persistent volumes
    print_info "Checking persistent volumes..."
    kubectl get pv,pvc -n "$NAMESPACE"
}

# Function to show status
show_status() {
    print_info "Infrastructure deployment status:"
    echo ""
    
    # Show namespaces
    print_info "Namespaces:"
    kubectl get namespaces | grep -E "(iot|monitoring|ingress-nginx|cert-manager|chaos-testing)" || true
    echo ""
    
    # Show deployments
    print_info "Deployments:"
    kubectl get deployments --all-namespaces | grep -E "(iot|monitoring|ingress-nginx|cert-manager)" || true
    echo ""
    
    # Show services
    print_info "Services:"
    kubectl get services --all-namespaces | grep -E "(iot|monitoring|ingress-nginx|cert-manager)" || true
    echo ""
    
    # Show persistent volumes
    print_info "Persistent Volumes:"
    kubectl get pv,pvc --all-namespaces | grep -E "(iot|monitoring)" || true
    echo ""
    
    # Show pods status
    print_info "Pod Status:"
    kubectl get pods --all-namespaces | grep -E "(iot|monitoring|ingress-nginx|cert-manager)" || true
}

# Function to show logs
show_logs() {
    print_info "Showing logs for infrastructure components..."
    
    # PostgreSQL logs
    print_info "PostgreSQL logs:"
    kubectl logs -n "$NAMESPACE" -l app=postgres --tail=50 || true
    echo ""
    
    # Redis logs
    print_info "Redis logs:"
    kubectl logs -n "$NAMESPACE" -l app=redis --tail=50 || true
    echo ""
    
    # Monitoring logs
    if [[ "$SKIP_MONITORING" == "false" ]]; then
        print_info "Prometheus logs:"
        kubectl logs -n monitoring -l app=prometheus --tail=50 || true
        echo ""
        
        print_info "Grafana logs:"
        kubectl logs -n monitoring -l app=grafana --tail=50 || true
        echo ""
    fi
    
    # Ingress logs
    if [[ "$SKIP_INGRESS" == "false" ]]; then
        print_info "Ingress controller logs:"
        kubectl logs -n ingress-nginx -l app=nginx-ingress --tail=50 || true
        echo ""
    fi
}

# Function to run tests
run_tests() {
    print_info "Running infrastructure tests..."
    
    # Test database connectivity
    print_info "Testing PostgreSQL connectivity..."
    kubectl exec -n "$NAMESPACE" deployment/postgres -- pg_isready -h localhost || {
        print_error "PostgreSQL connectivity test failed"
        return 1
    }
    
    # Test Redis connectivity
    print_info "Testing Redis connectivity..."
    kubectl exec -n "$NAMESPACE" statefulset/redis -- redis-cli ping || {
        print_error "Redis connectivity test failed"
        return 1
    }
    
    # Test monitoring endpoints
    if [[ "$SKIP_MONITORING" == "false" ]]; then
        print_info "Testing monitoring endpoints..."
        kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/-/healthy || {
            print_error "Prometheus health check failed"
            return 1
        }
    fi
    
    print_success "All infrastructure tests passed"
}

# Function to uninstall
uninstall() {
    print_warning "This will remove ALL infrastructure components. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Uninstall cancelled"
        exit 0
    fi
    
    print_info "Uninstalling infrastructure components..."
    
    # Delete chaos engineering
    print_info "Removing chaos engineering components..."
    kubectl delete -f deploy/infra/k8s/chaos-engineering.yaml --ignore-not-found=true || true
    
    # Delete backup jobs
    print_info "Removing backup jobs..."
    kubectl delete -f deploy/infra/k8s/backup-cronjob.yaml --ignore-not-found=true || true
    
    # Delete load balancers
    print_info "Removing load balancers..."
    kubectl delete -f deploy/infra/k8s/load-balancer.yaml --ignore-not-found=true || true
    
    # Delete storage classes
    print_info "Removing storage classes..."
    kubectl delete -f deploy/infra/k8s/storage-class.yaml --ignore-not-found=true || true
    
    # Delete cert-manager
    if [[ "$SKIP_CERT_MANAGER" == "false" ]]; then
        print_info "Removing cert-manager..."
        kubectl delete -f deploy/infra/k8s/cert-manager.yaml --ignore-not-found=true || true
    fi
    
    # Delete ingress controller
    if [[ "$SKIP_INGRESS" == "false" ]]; then
        print_info "Removing ingress controller..."
        kubectl delete -f deploy/infra/k8s/ingress-controller.yaml --ignore-not-found=true || true
    fi
    
    # Delete monitoring stack
    if [[ "$SKIP_MONITORING" == "false" ]]; then
        print_info "Removing monitoring stack..."
        kubectl delete -f deploy/infra/k8s/monitoring-stack.yaml --ignore-not-found=true || true
    fi
    
    # Delete PostgreSQL
    print_info "Removing PostgreSQL..."
    kubectl delete -f deploy/infra/k8s/postgres-ha.yaml --ignore-not-found=true || true
    
    # Delete complete infrastructure
    print_info "Removing complete infrastructure..."
    kubectl delete -f deploy/infra/k8s/complete-infrastructure.yaml --ignore-not-found=true || true
    
    # Delete namespaces
    print_info "Removing namespaces..."
    kubectl delete namespace chaos-testing --ignore-not-found=true || true
    kubectl delete namespace cert-manager --ignore-not-found=true || true
    kubectl delete namespace ingress-nginx --ignore-not-found=true || true
    kubectl delete namespace monitoring --ignore-not-found=true || true
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true || true
    
    print_success "Infrastructure uninstalled successfully"
}

# Main deployment function
deploy() {
    print_info "Starting infrastructure deployment..."
    print_info "Environment: $ENVIRONMENT"
    print_info "Namespace: $NAMESPACE"
    print_info "Dry run: $DRY_RUN"
    
    check_prerequisites
    create_namespaces
    deploy_complete_infrastructure
    deploy_postgres
    deploy_monitoring
    deploy_ingress
    deploy_cert_manager
    deploy_storage
    deploy_load_balancers
    deploy_backup_jobs
    deploy_chaos_engineering
    wait_for_deployments
    verify_deployment
    
    print_success "Infrastructure deployment completed successfully!"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        echo ""
        print_info "Next steps:"
        echo "1. Verify all components are running: $0 status"
        echo "2. Check logs if needed: $0 logs"
        echo "3. Run tests: $0 test"
        echo "4. Deploy the suggestion service: ./deploy/suggestion/deploy.sh deploy"
    fi
}

# Main script logic
case "$COMMAND" in
    deploy)
        deploy
        ;;
    upgrade)
        print_info "Upgrading infrastructure..."
        deploy
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
        usage
        exit 1
        ;;
esac
