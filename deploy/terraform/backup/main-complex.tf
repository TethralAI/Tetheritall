# Tethral Infrastructure - Local Terraform Configuration
# Complete AWS infrastructure for the Tethral IoT platform

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  # Use local state storage for initial deployment
  # We'll migrate to S3 backend later
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Tethral"
      Environment = var.environment
      ManagedBy   = "Terraform"
      GitRepo     = "Tetheritall"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Random password for databases
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Random API tokens
resource "random_password" "api_token" {
  length  = 64
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# Local values
locals {
  name = "tethral-${var.environment}"
  
  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)
  
  tags = {
    Project     = "Tethral"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
