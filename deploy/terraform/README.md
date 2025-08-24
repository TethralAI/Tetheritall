# Tethral Terraform Infrastructure

Complete AWS infrastructure setup for the Tethral IoT platform using Terraform.

## 🏗️ Architecture

This Terraform configuration creates:

- **EKS Cluster**: Managed Kubernetes cluster with auto-scaling node groups
- **VPC**: Multi-AZ networking with public/private/database subnets
- **RDS PostgreSQL**: High-availability database with automated backups
- **ElastiCache Redis**: In-memory caching and session storage
- **S3 Buckets**: Application storage, backups, logs, and Terraform state
- **KMS Keys**: Encryption at rest for all services
- **IAM Roles**: Least-privilege access for all components
- **CloudWatch**: Centralized logging and monitoring
- **Secrets Manager**: Secure credential storage

## 📋 Prerequisites

### Required Tools

```bash
# Terraform
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# kubectl
curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.29.0/2024-01-04/bin/linux/amd64/kubectl
chmod +x ./kubectl && sudo mv ./kubectl /usr/local/bin

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

### Required AWS Permissions

Your AWS user/role needs these permissions:
- `AdministratorAccess` (for initial setup)
- Or specific permissions for: EC2, EKS, RDS, S3, IAM, KMS, VPC, CloudWatch, Secrets Manager

## 🚀 Quick Start

### 1. Initialize Remote State (First Time Only)

```bash
# Create S3 bucket and DynamoDB table for state
aws s3 mb s3://tethral-terraform-state --region us-east-1
aws dynamodb create-table \
    --table-name tethral-terraform-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

### 2. Configure Variables

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration for your environment
nano terraform.tfvars
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply
```

### 4. Configure kubectl

```bash
# Get cluster credentials
aws eks update-kubeconfig --region us-east-1 --name tethral-dev

# Verify connection
kubectl get nodes
```

## 📊 Environments

### Development Environment

```bash
# terraform.tfvars for development
environment = "dev"
node_instance_types = ["t3.medium"]
node_desired_capacity = 2
db_instance_class = "db.t3.micro"
redis_node_type = "cache.t3.micro"
single_nat_gateway = true
enable_spot_instances = true
```

### Production Environment

```bash
# terraform.tfvars for production
environment = "prod"
node_instance_types = ["m5.large", "m5.xlarge"]
node_desired_capacity = 6
node_min_capacity = 3
node_max_capacity = 20
db_instance_class = "db.r5.xlarge"
redis_node_type = "cache.r5.large"
single_nat_gateway = false
enable_encryption = true
allowed_cidr_blocks = ["10.0.0.0/8"]  # Your corporate networks
```

## 🔧 Configuration

### Key Variables

| Variable | Description | Default | Production Recommendation |
|----------|-------------|---------|--------------------------|
| `environment` | Environment name | `dev` | `prod` |
| `aws_region` | AWS region | `us-east-1` | `us-east-1` |
| `node_instance_types` | EKS node types | `["t3.medium"]` | `["m5.large", "m5.xlarge"]` |
| `db_instance_class` | RDS instance type | `db.t3.micro` | `db.r5.xlarge` |
| `redis_node_type` | ElastiCache type | `cache.t3.micro` | `cache.r5.large` |
| `enable_encryption` | Enable encryption | `true` | `true` |
| `single_nat_gateway` | Use single NAT | `true` | `false` |

### Security Configuration

```hcl
# Restrict access to your networks
allowed_cidr_blocks = [
  "10.0.0.0/8",     # Corporate network
  "1.2.3.4/32"      # Your IP address
]

# Enable encryption for all services
enable_encryption = true

# Configure backup retention
db_backup_retention_period = 30  # days
```

## 📱 Application Deployment

After infrastructure is ready, deploy the Tethral application:

### 1. Build and Push Images

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# Build and tag image
docker build -t tethral-app .
docker tag tethral-app:latest $(terraform output -raw ecr_repository_url):latest

# Push to ECR
docker push $(terraform output -raw ecr_repository_url):latest
```

### 2. Deploy Kubernetes Resources

```bash
# Deploy from existing manifests
kubectl apply -f ../k8s/

# Or use Helm
helm install tethral ../helm/umbrella/
```

### 3. Configure Application Secrets

```bash
# Set API keys in Secrets Manager
aws secretsmanager update-secret \
    --secret-id $(terraform output -raw api_keys_secret_arn) \
    --secret-string '{
        "SMARTTHINGS_TOKEN": "your-token",
        "OPENAI_API_KEY": "your-key"
    }'
```

## 🔍 Monitoring

### CloudWatch Logs

```bash
# View application logs
aws logs tail $(terraform output -raw cloudwatch_log_group_app) --follow

# View EKS cluster logs
aws logs tail $(terraform output -raw cloudwatch_log_group_eks) --follow
```

### Database Monitoring

```bash
# Check RDS performance
aws rds describe-db-instances --db-instance-identifier $(terraform output -raw db_instance_id)

# View database logs
aws logs tail "/aws/rds/instance/$(terraform output -raw db_instance_id)/postgresql" --follow
```

### Application Health

```bash
# Check pod status
kubectl get pods -n iot

# Check services
kubectl get svc -n iot

# View application logs
kubectl logs -f deployment/api -n iot
```

## 🔄 Updates and Maintenance

### Updating Infrastructure

```bash
# Check for changes
terraform plan

# Apply updates
terraform apply

# Update EKS add-ons
aws eks describe-addon-versions --kubernetes-version 1.29
```

### Scaling

```bash
# Scale node group
aws eks update-nodegroup-config \
    --cluster-name $(terraform output -raw cluster_id) \
    --nodegroup-name primary \
    --scaling-config minSize=5,maxSize=15,desiredSize=8
```

### Database Maintenance

```bash
# Create manual snapshot
aws rds create-db-snapshot \
    --db-instance-identifier $(terraform output -raw db_instance_id) \
    --db-snapshot-identifier manual-snapshot-$(date +%Y%m%d)

# Check backup status
aws rds describe-db-snapshots \
    --db-instance-identifier $(terraform output -raw db_instance_id)
```

## 🛠️ Troubleshooting

### Common Issues

#### EKS Nodes Not Joining
```bash
# Check node group status
aws eks describe-nodegroup --cluster-name CLUSTER_NAME --nodegroup-name primary

# Check IAM roles
aws iam list-attached-role-policies --role-name ROLE_NAME
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
    psql -h $(terraform output -raw db_instance_endpoint) -U postgres
```

#### Application Pods Failing
```bash
# Check pod events
kubectl describe pod POD_NAME -n iot

# Check secrets
kubectl get secrets -n iot
```

### Logs and Debugging

```bash
# Terraform debug logs
export TF_LOG=DEBUG
terraform apply

# AWS CLI debug
aws --debug eks describe-cluster --name CLUSTER_NAME
```

## 💰 Cost Optimization

### Development Environment
- Use `t3.micro` instances
- Enable spot instances
- Single NAT gateway
- Shorter log retention (7 days)

### Production Environment
- Use reserved instances for predictable workloads
- Enable S3 lifecycle policies
- Monitor with AWS Cost Explorer
- Set up billing alerts

### Cost Monitoring

```bash
# Check current costs
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

## 🧹 Cleanup

### Destroy Infrastructure

```bash
# Remove Kubernetes resources first
kubectl delete namespace iot

# Wait for ELBs to be deleted
sleep 60

# Destroy Terraform resources
terraform destroy
```

### Manual Cleanup

Some resources may need manual cleanup:
- EBS volumes from terminated nodes
- ENIs from deleted load balancers
- S3 buckets with objects

## 📚 Additional Resources

- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
