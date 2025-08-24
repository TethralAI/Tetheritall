# Tethral Infrastructure Outputs
# Key information needed by other systems and applications

# Cluster Information
output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

# Network Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "database_subnets" {
  description = "List of IDs of database subnets"
  value       = aws_subnet.database[*].id
}

output "nat_gateway_ids" {
  description = "List of IDs of the NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

# Database Information
output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "db_instance_name" {
  description = "RDS instance name"
  value       = aws_db_instance.main.db_name
}

output "db_instance_username" {
  description = "RDS instance root username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_subnet_group_id" {
  description = "RDS subnet group ID"
  value       = aws_db_subnet_group.main.id
}

output "db_parameter_group_id" {
  description = "RDS parameter group ID"
  value       = aws_db_parameter_group.main.id
}

# Redis Information
output "redis_cluster_id" {
  description = "ElastiCache Redis cluster ID"
  value       = aws_elasticache_replication_group.redis.id
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

# Storage Information
output "s3_bucket_app_storage" {
  description = "S3 bucket for application storage"
  value       = aws_s3_bucket.app_storage.id
}

output "s3_bucket_backup_storage" {
  description = "S3 bucket for backup storage"
  value       = aws_s3_bucket.backup_storage.id
}

output "s3_bucket_logs_storage" {
  description = "S3 bucket for logs storage"
  value       = aws_s3_bucket.logs_storage.id
}

output "s3_bucket_terraform_state" {
  description = "S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

# Security Information
output "security_group_eks_cluster" {
  description = "Security group ID for EKS cluster"
  value       = aws_security_group.eks_cluster.id
}

output "security_group_eks_nodes" {
  description = "Security group ID for EKS nodes"
  value       = aws_security_group.eks_nodes.id
}

output "security_group_rds" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "security_group_elasticache" {
  description = "Security group ID for ElastiCache"
  value       = aws_security_group.elasticache.id
}

output "security_group_alb" {
  description = "Security group ID for Application Load Balancer"
  value       = aws_security_group.alb.id
}

# IAM Information
output "eks_cluster_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_group_role_arn" {
  description = "EKS node group IAM role ARN"
  value       = aws_iam_role.eks_node_group.arn
}

output "tethral_app_role_arn" {
  description = "Tethral application IAM role ARN"
  value       = aws_iam_role.tethral_app.arn
}

output "aws_load_balancer_controller_role_arn" {
  description = "AWS Load Balancer Controller IAM role ARN"
  value       = aws_iam_role.aws_load_balancer_controller.arn
}

# KMS Information
output "kms_key_eks_arn" {
  description = "EKS KMS key ARN"
  value       = aws_kms_key.eks.arn
}

output "kms_key_rds_arn" {
  description = "RDS KMS key ARN"
  value       = aws_kms_key.rds.arn
}

output "kms_key_s3_arn" {
  description = "S3 KMS key ARN"
  value       = aws_kms_key.s3.arn
}

output "kms_key_app_secrets_arn" {
  description = "Application secrets KMS key ARN"
  value       = aws_kms_key.app_secrets.arn
}

# Secrets Manager
output "db_credentials_secret_arn" {
  description = "Database credentials secret ARN"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "redis_credentials_secret_arn" {
  description = "Redis credentials secret ARN"
  value       = aws_secretsmanager_secret.redis_credentials.arn
}

output "api_keys_secret_arn" {
  description = "API keys secret ARN"
  value       = aws_secretsmanager_secret.api_keys.arn
}

# CloudWatch
output "cloudwatch_log_group_app" {
  description = "CloudWatch log group for application"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "cloudwatch_log_group_eks" {
  description = "CloudWatch log group for EKS"
  value       = aws_cloudwatch_log_group.eks_cluster.name
}

# SNS
output "sns_topic_alerts_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

# Environment Configuration for Applications
output "environment_config" {
  description = "Environment configuration for applications"
  value = {
    # Database
    DATABASE_URL = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}?sslmode=require"
    
    # Redis
    REDIS_URL = aws_elasticache_replication_group.redis.primary_endpoint_address != "" ? (
      var.enable_encryption ? 
        "redis://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:${aws_elasticache_replication_group.redis.port}/0" :
        "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:${aws_elasticache_replication_group.redis.port}/0"
    ) : ""
    
    # AWS Configuration
    AWS_REGION                = var.aws_region
    AWS_S3_BUCKET            = aws_s3_bucket.app_storage.id
    AWS_BACKUP_BUCKET        = aws_s3_bucket.backup_storage.id
    AWS_LOGS_BUCKET          = aws_s3_bucket.logs_storage.id
    
    # Secrets Manager
    DB_CREDENTIALS_SECRET    = aws_secretsmanager_secret.db_credentials.name
    REDIS_CREDENTIALS_SECRET = aws_secretsmanager_secret.redis_credentials.name
    API_KEYS_SECRET          = aws_secretsmanager_secret.api_keys.name
    
    # CloudWatch
    LOG_GROUP_APP           = aws_cloudwatch_log_group.app_logs.name
    LOG_GROUP_NGINX         = aws_cloudwatch_log_group.nginx_logs.name
    LOG_GROUP_SYSTEM        = aws_cloudwatch_log_group.system_logs.name
    
    # Monitoring
    SNS_ALERTS_TOPIC        = aws_sns_topic.alerts.arn
    
    # Container Registry
    ECR_REPOSITORY          = aws_ecr_repository.app.repository_url
  }
  sensitive = true
}

# Kubectl Configuration Command
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.name}"
}

# Useful URLs and Endpoints
output "useful_commands" {
  description = "Useful commands for managing the infrastructure"
  value = {
    # EKS
    kubectl_config        = "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.name}"
    get_nodes            = "kubectl get nodes"
    get_pods             = "kubectl get pods --all-namespaces"
    
    # Database
    connect_to_db        = "psql ${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name} -U ${aws_db_instance.main.username}"
    
    # ECR
    ecr_login           = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}"
    
    # Logs
    view_app_logs       = "aws logs tail ${aws_cloudwatch_log_group.app_logs.name} --follow"
    view_eks_logs       = "aws logs tail ${aws_cloudwatch_log_group.eks_cluster.name} --follow"
  }
}
