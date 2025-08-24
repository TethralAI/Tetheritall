# Tethral Database Infrastructure
# RDS PostgreSQL with high availability, backups, and monitoring

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  family = "postgres15"
  name   = "${local.name}-db-params"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_lock_waits"
    value = "1"
  }

  parameter {
    name  = "log_temp_files"
    value = "0"  # Log all temp files
  }

  parameter {
    name  = "log_autovacuum_min_duration"
    value = "0"  # Log all autovacuum activity
  }

  tags = local.tags
}

# DB Option Group
resource "aws_db_option_group" "main" {
  name                     = "${local.name}-db-options"
  option_group_description = "Option group for ${local.name} PostgreSQL"
  engine_name              = "postgres"
  major_engine_version     = "15"

  tags = local.tags
}

# Main RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${local.name}-db"

  # Engine configuration
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  # Storage configuration
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = var.enable_encryption
  kms_key_id           = var.enable_encryption ? aws_kms_key.rds.arn : null

  # Database configuration
  db_name  = "tethral"
  username = "tethral_admin"
  password = random_password.db_password.result
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup configuration
  backup_retention_period = var.db_backup_retention_period
  backup_window          = var.db_backup_window
  maintenance_window     = var.db_maintenance_window
  copy_tags_to_snapshot  = true
  delete_automated_backups = false

  # Monitoring and logging
  monitoring_interval                   = 60
  monitoring_role_arn                  = aws_iam_role.rds_enhanced_monitoring.arn
  performance_insights_enabled         = true
  performance_insights_kms_key_id      = aws_kms_key.rds.arn
  performance_insights_retention_period = 7
  enabled_cloudwatch_logs_exports      = ["postgresql", "upgrade"]

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.main.name
  option_group_name    = aws_db_option_group.main.name

  # Maintenance and updates
  auto_minor_version_upgrade = true
  allow_major_version_upgrade = false
  apply_immediately          = false

  # Deletion protection
  deletion_protection = var.environment == "prod" ? true : false
  skip_final_snapshot = var.environment == "prod" ? false : true
  final_snapshot_identifier = var.environment == "prod" ? "${local.name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  tags = merge(local.tags, {
    Name = "${local.name}-database"
  })

  depends_on = [aws_cloudwatch_log_group.rds_postgresql]
}

# Read Replica (for production environments)
resource "aws_db_instance" "read_replica" {
  count = var.environment == "prod" ? 1 : 0

  identifier = "${local.name}-db-replica"

  # Replica configuration
  replicate_source_db = aws_db_instance.main.identifier
  instance_class      = var.db_instance_class

  # Network configuration
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Monitoring
  monitoring_interval                   = 60
  monitoring_role_arn                  = aws_iam_role.rds_enhanced_monitoring.arn
  performance_insights_enabled         = true
  performance_insights_kms_key_id      = aws_kms_key.rds.arn
  performance_insights_retention_period = 7

  # Maintenance
  auto_minor_version_upgrade = true
  apply_immediately         = false

  tags = merge(local.tags, {
    Name = "${local.name}-database-replica"
  })
}

# CloudWatch Log Groups for RDS
resource "aws_cloudwatch_log_group" "rds_postgresql" {
  name              = "/aws/rds/instance/${local.name}-db/postgresql"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "rds_upgrade" {
  name              = "/aws/rds/instance/${local.name}-db/upgrade"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

# Enhanced Monitoring IAM Role
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${local.name}-rds-enhanced-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${local.name}-redis"
  description                  = "Redis cluster for ${local.name}"

  # Engine configuration
  engine               = "redis"
  engine_version       = "7.0"
  node_type           = var.redis_node_type
  parameter_group_name = var.redis_parameter_group_name
  port                = var.redis_port

  # Cluster configuration
  num_cache_clusters = var.redis_num_cache_nodes
  
  # Network configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  # Security
  at_rest_encryption_enabled = var.enable_encryption
  transit_encryption_enabled = var.enable_encryption
  auth_token                 = var.enable_encryption ? random_password.redis_auth.result : null
  kms_key_id                = var.enable_encryption ? aws_kms_key.elasticache.arn : null

  # Backup configuration
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  # Notifications
  notification_topic_arn = aws_sns_topic.alerts.arn

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = local.tags
}

# Redis auth token (when encryption is enabled)
resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/redis/${local.name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

# Database credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.name}/database/credentials"
  description = "Database credentials for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = aws_db_instance.main.username
    password = aws_db_instance.main.password
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
    url      = "postgresql://${aws_db_instance.main.username}:${aws_db_instance.main.password}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}?sslmode=require"
  })
}

# Redis credentials in Secrets Manager
resource "aws_secretsmanager_secret" "redis_credentials" {
  name        = "${local.name}/redis/credentials"
  description = "Redis credentials for ${local.name}"
  kms_key_id  = aws_kms_key.app_secrets.arn

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    host     = aws_elasticache_replication_group.redis.primary_endpoint_address
    port     = aws_elasticache_replication_group.redis.port
    auth_token = var.enable_encryption ? random_password.redis_auth.result : ""
    url      = var.enable_encryption ? "redis://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:${aws_elasticache_replication_group.redis.port}/0" : "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:${aws_elasticache_replication_group.redis.port}/0"
  })
}

# Database CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${local.name}-database-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${local.name}-database-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS connection count"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = local.tags
}

# SNS Topic for Database Alerts
resource "aws_sns_topic" "alerts" {
  name         = "${local.name}-database-alerts"
  display_name = "Tethral Database Alerts"
  kms_master_key_id = aws_kms_key.sns.arn

  tags = local.tags
}
