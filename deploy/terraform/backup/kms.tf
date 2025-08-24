# Tethral KMS Keys for Encryption
# All encryption keys for different services

# EKS Encryption Key
resource "aws_kms_key" "eks" {
  description             = "EKS encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-eks-key"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# RDS Encryption Key
resource "aws_kms_key" "rds" {
  description             = "RDS encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-rds-key"
  })
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# ElastiCache Encryption Key
resource "aws_kms_key" "elasticache" {
  description             = "ElastiCache encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-elasticache-key"
  })
}

resource "aws_kms_alias" "elasticache" {
  name          = "alias/${local.name}-elasticache"
  target_key_id = aws_kms_key.elasticache.key_id
}

# S3 Encryption Key
resource "aws_kms_key" "s3" {
  description             = "S3 encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:ReEncrypt*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = merge(local.tags, {
    Name = "${local.name}-s3-key"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# CloudWatch Logs Encryption Key
resource "aws_kms_key" "cloudwatch" {
  description             = "CloudWatch Logs encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/tethral/*"
          }
        }
      }
    ]
  })

  tags = merge(local.tags, {
    Name = "${local.name}-cloudwatch-key"
  })
}

resource "aws_kms_alias" "cloudwatch" {
  name          = "alias/${local.name}-cloudwatch"
  target_key_id = aws_kms_key.cloudwatch.key_id
}

# Application Secrets Encryption Key
resource "aws_kms_key" "app_secrets" {
  description             = "Application secrets encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Secrets Manager"
        Effect = "Allow"
        Principal = {
          Service = "secretsmanager.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:ReEncrypt*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Sid    = "Allow EKS service account"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.tethral_app.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.tags, {
    Name = "${local.name}-app-secrets-key"
  })
}

resource "aws_kms_alias" "app_secrets" {
  name          = "alias/${local.name}-app-secrets"
  target_key_id = aws_kms_key.app_secrets.key_id
}

# EBS Encryption Key
resource "aws_kms_key" "ebs" {
  description             = "EBS encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-ebs-key"
  })
}

resource "aws_kms_alias" "ebs" {
  name          = "alias/${local.name}-ebs"
  target_key_id = aws_kms_key.ebs.key_id
}

# ECR Encryption Key
resource "aws_kms_key" "ecr" {
  description             = "ECR encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-ecr-key"
  })
}

resource "aws_kms_alias" "ecr" {
  name          = "alias/${local.name}-ecr"
  target_key_id = aws_kms_key.ecr.key_id
}

# SNS Encryption Key
resource "aws_kms_key" "sns" {
  description             = "SNS encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SNS service"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.tags, {
    Name = "${local.name}-sns-key"
  })
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${local.name}-sns"
  target_key_id = aws_kms_key.sns.key_id
}

# DynamoDB Encryption Key
resource "aws_kms_key" "dynamodb" {
  description             = "DynamoDB encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-dynamodb-key"
  })
}

resource "aws_kms_alias" "dynamodb" {
  name          = "alias/${local.name}-dynamodb"
  target_key_id = aws_kms_key.dynamodb.key_id
}

# Terraform State Encryption Key
resource "aws_kms_key" "terraform" {
  description             = "Terraform state encryption key for ${local.name}"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-terraform-key"
  })
}

resource "aws_kms_alias" "terraform" {
  name          = "alias/${local.name}-terraform"
  target_key_id = aws_kms_key.terraform.key_id
}
