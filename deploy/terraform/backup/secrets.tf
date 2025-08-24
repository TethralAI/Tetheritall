# Tethral Secrets Management
# AWS Secrets Manager configuration for application secrets

# API Keys and Application Secrets
resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${local.name}/api/keys"
  description = "API keys and application secrets for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    # Core API Configuration
    API_TOKEN    = random_password.api_token.result
    JWT_SECRET   = random_password.jwt_secret.result
    JWT_AUDIENCE = "tethral-${var.environment}"
    
    # External Service API Keys (these would be set manually or via CI/CD)
    SMARTTHINGS_TOKEN        = ""
    TUYA_CLIENT_ID          = ""
    TUYA_CLIENT_SECRET      = ""
    FCM_SERVER_KEY          = ""
    OPENAI_API_KEY          = ""
    
    # Home Assistant Integration
    HOME_ASSISTANT_TOKEN    = ""
    
    # Google Nest SDM
    GOOGLE_NEST_ACCESS_TOKEN = ""
    
    # Philips Hue
    HUE_REMOTE_TOKEN        = ""
    
    # openHAB
    OPENHAB_TOKEN           = ""
    
    # Alexa Smart Home
    ALEXA_SKILL_SECRET      = ""
    
    # OAuth Configuration
    SMARTTHINGS_CLIENT_ID     = ""
    SMARTTHINGS_CLIENT_SECRET = ""
    TUYA_CLIENT_ID           = ""
    TUYA_CLIENT_SECRET       = ""
    SMARTCAR_CLIENT_ID       = ""
    SMARTCAR_CLIENT_SECRET   = ""
    
    # Wearables/Health APIs
    OURA_CLIENT_ID          = ""
    TERRA_API_KEY           = ""
    
    # Hubitat Integration
    HUBITAT_MAKER_TOKEN     = ""
  })
}

# Environment-specific Configuration
resource "aws_secretsmanager_secret" "app_config" {
  name        = "${local.name}/app/config"
  description = "Application configuration for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "app_config" {
  secret_id = aws_secretsmanager_secret.app_config.id
  secret_string = jsonencode({
    # Environment
    ENVIRONMENT = var.environment
    
    # AWS Configuration
    AWS_REGION     = var.aws_region
    AWS_S3_BUCKET  = aws_s3_bucket.app_storage.id
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = "120"
    RATE_LIMIT_PER_SECOND          = "2.0"
    
    # Request Configuration
    REQUEST_TIMEOUT_SECONDS    = "20"
    MAX_CONCURRENT_REQUESTS    = "10"
    
    # ML Configuration
    ML_LOCAL_ENABLED   = "true"
    ML_EDGE_ENABLED    = "true"
    ML_CLOUD_ENABLED   = "true"
    ML_DEFAULT_LOCATION = "local"
    
    # Security Configuration
    SECURITY_MONITORING_ENABLED      = "true"
    SECURITY_THREAT_DETECTION_ENABLED = "true"
    SECURITY_AUTO_BLOCK_ENABLED      = "false"
    
    # Orchestration Configuration
    ORCHESTRATION_MAX_WORKFLOWS            = "100"
    ORCHESTRATION_MAX_CONCURRENT_WORKFLOWS = "10"
    
    # Discovery Configuration
    DISCOVERY_SCAN_INTERVAL_SECONDS = "300"
    DISCOVERY_MAX_CONCURRENT_SCANS  = "5"
    
    # Edge Configuration
    EDGE_LAN_ONLY      = "false"
    TELEMETRY_OPT_IN   = "true"
    TELEMETRY_NAMESPACE = "tethral-${var.environment}"
    
    # Event Bus Configuration
    EVENT_BUS_BACKEND = "nats"
    EVENTS_MAXLEN     = "10000"
    
    # LLM Configuration
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    OPENAI_MODEL    = "gpt-4o-mini"
    LLM_DETERMINISTIC = "true"
    LLM_BUDGETS     = "default:1000"
    
    # Infrastructure
    OUTBOUND_ALLOWLIST = "integrations"
    
    # Proxy Configuration
    PROXY_CAPABILITIES_VIA_INTEGRATIONS = "true"
    INTEGRATIONS_BASE_URL              = "http://integrations:8100"
    PROXY_CANARY_PERCENT               = "0"
    
    # Caching
    CACHE_TTL_SECONDS = "60"
    
    # Feature Flags
    ENABLE_PROMETHEUS = var.enable_prometheus ? "true" : "false"
    ENABLE_GRAFANA    = var.enable_grafana ? "true" : "false"
    ENABLE_OCPI       = "false"
  })
}

# Network and Infrastructure Secrets
resource "aws_secretsmanager_secret" "infrastructure" {
  name        = "${local.name}/infrastructure/config"
  description = "Infrastructure configuration for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "infrastructure" {
  secret_id = aws_secretsmanager_secret.infrastructure.id
  secret_string = jsonencode({
    # Network Configuration
    VPC_ID             = aws_vpc.main.id
    PRIVATE_SUBNET_IDS = join(",", aws_subnet.private[*].id)
    PUBLIC_SUBNET_IDS  = join(",", aws_subnet.public[*].id)
    
    # Security Groups
    EKS_CLUSTER_SG_ID = aws_security_group.eks_cluster.id
    EKS_NODES_SG_ID   = aws_security_group.eks_nodes.id
    RDS_SG_ID         = aws_security_group.rds.id
    REDIS_SG_ID       = aws_security_group.elasticache.id
    ALB_SG_ID         = aws_security_group.alb.id
    
    # KMS Keys
    EKS_KMS_KEY_ARN        = aws_kms_key.eks.arn
    RDS_KMS_KEY_ARN        = aws_kms_key.rds.arn
    S3_KMS_KEY_ARN         = aws_kms_key.s3.arn
    APP_SECRETS_KMS_KEY_ARN = aws_kms_key.app_secrets.arn
    
    # Service Endpoints
    ECR_REPOSITORY_URL = aws_ecr_repository.app.repository_url
    SNS_ALERTS_TOPIC   = aws_sns_topic.alerts.arn
    
    # CloudWatch Log Groups
    APP_LOG_GROUP    = aws_cloudwatch_log_group.app_logs.name
    NGINX_LOG_GROUP  = aws_cloudwatch_log_group.nginx_logs.name
    SYSTEM_LOG_GROUP = aws_cloudwatch_log_group.system_logs.name
  })
}

# mTLS Certificates (if needed)
resource "aws_secretsmanager_secret" "mtls_certs" {
  count = var.environment == "prod" ? 1 : 0
  
  name        = "${local.name}/mtls/certificates"
  description = "mTLS certificates for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

# HCP Terraform Configuration (if using Terraform Cloud)
resource "aws_secretsmanager_secret" "terraform_cloud" {
  count = var.environment == "prod" ? 1 : 0
  
  name        = "${local.name}/terraform/cloud"
  description = "Terraform Cloud configuration for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "terraform_cloud" {
  count = var.environment == "prod" ? 1 : 0
  
  secret_id = aws_secretsmanager_secret.terraform_cloud[0].id
  secret_string = jsonencode({
    HCP_TERRAFORM_TOKEN        = ""  # Set manually
    HCP_TERRAFORM_ORG          = ""  # Set manually
    HCP_TERRAFORM_WORKSPACE_ID = ""  # Set manually
  })
}

# Backup Configuration
resource "aws_secretsmanager_secret" "backup_config" {
  name        = "${local.name}/backup/config"
  description = "Backup configuration for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "backup_config" {
  secret_id = aws_secretsmanager_secret.backup_config.id
  secret_string = jsonencode({
    # S3 Backup Configuration
    S3_BACKUP_BUCKET = aws_s3_bucket.backup_storage.id
    S3_ENDPOINT     = "https://s3.${var.aws_region}.amazonaws.com"
    
    # Database Backup
    PGUSER     = aws_db_instance.main.username
    PGHOST     = aws_db_instance.main.endpoint
    PGDATABASE = aws_db_instance.main.db_name
    PGPORT     = tostring(aws_db_instance.main.port)
    
    # Backup Schedule
    BACKUP_SCHEDULE = var.backup_schedule
    BACKUP_RETENTION_DAYS = tostring(var.db_backup_retention_period)
  })
}

# Monitoring and Alerting Configuration
resource "aws_secretsmanager_secret" "monitoring" {
  name        = "${local.name}/monitoring/config"
  description = "Monitoring and alerting configuration for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "monitoring" {
  secret_id = aws_secretsmanager_secret.monitoring.id
  secret_string = jsonencode({
    # OpenTelemetry Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT = "http://otel-collector.iot.svc.cluster.local:4318"
    OTEL_SERVICE_NAME           = "tethral-${var.environment}"
    OTEL_RESOURCE_ATTRIBUTES    = "service.name=tethral,service.version=1.0.0,deployment.environment=${var.environment}"
    
    # Prometheus Configuration
    PROMETHEUS_ENABLED = var.enable_prometheus ? "true" : "false"
    
    # CloudWatch Configuration
    CLOUDWATCH_NAMESPACE = "Tethral/IoT"
    CLOUDWATCH_REGION   = var.aws_region
    
    # Log Configuration
    LOG_LEVEL           = var.environment == "prod" ? "INFO" : "DEBUG"
    LOG_RETENTION_DAYS  = tostring(var.log_retention_days)
  })
}
