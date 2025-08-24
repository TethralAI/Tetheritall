# Tethral Storage Infrastructure
# S3 buckets, KMS keys, and storage policies

# Application Storage Bucket
resource "aws_s3_bucket" "app_storage" {
  bucket = "${var.s3_bucket_prefix}-${local.name}-app-storage"

  tags = merge(local.tags, {
    Name        = "${local.name}-app-storage"
    Purpose     = "Application data storage"
    Environment = var.environment
  })
}

resource "aws_s3_bucket_versioning" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_encryption" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    transition {
      days          = var.s3_lifecycle_transition_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.s3_lifecycle_transition_days * 2
      storage_class = "GLACIER"
    }

    expiration {
      days = var.s3_lifecycle_expiration_days
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 60
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Backup Storage Bucket
resource "aws_s3_bucket" "backup_storage" {
  bucket = "${var.s3_bucket_prefix}-${local.name}-backup-storage"

  tags = merge(local.tags, {
    Name        = "${local.name}-backup-storage"
    Purpose     = "Database and application backups"
    Environment = var.environment
  })
}

resource "aws_s3_bucket_versioning" "backup_storage" {
  bucket = aws_s3_bucket.backup_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "backup_storage" {
  bucket = aws_s3_bucket.backup_storage.id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backup_storage" {
  bucket = aws_s3_bucket.backup_storage.id

  rule {
    id     = "backup_lifecycle"
    status = "Enabled"

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    transition {
      days          = 90
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555  # 7 years
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backup_storage" {
  bucket = aws_s3_bucket.backup_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Logs Storage Bucket
resource "aws_s3_bucket" "logs_storage" {
  bucket = "${var.s3_bucket_prefix}-${local.name}-logs-storage"

  tags = merge(local.tags, {
    Name        = "${local.name}-logs-storage"
    Purpose     = "Application and infrastructure logs"
    Environment = var.environment
  })
}

resource "aws_s3_bucket_encryption" "logs_storage" {
  bucket = aws_s3_bucket.logs_storage.id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_storage" {
  bucket = aws_s3_bucket.logs_storage.id

  rule {
    id     = "logs_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs_storage" {
  bucket = aws_s3_bucket.logs_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Terraform State Bucket (for remote state)
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.s3_bucket_prefix}-${local.name}-terraform-state"

  tags = merge(local.tags, {
    Name        = "${local.name}-terraform-state"
    Purpose     = "Terraform state storage"
    Environment = var.environment
  })
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.terraform.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "${local.name}-terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.tags, {
    Name        = "${local.name}-terraform-locks"
    Purpose     = "Terraform state locking"
    Environment = var.environment
  })
}

# ECR Repository for application images
resource "aws_ecr_repository" "app" {
  name                 = "${local.name}/app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key        = aws_kms_key.ecr.arn
  }

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 production images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["prod"]
          countType     = "imageCountMoreThan"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 development images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev", "staging"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/tethral/${local.name}/application"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "nginx_logs" {
  name              = "/aws/tethral/${local.name}/nginx"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "system_logs" {
  name              = "/aws/tethral/${local.name}/system"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}
