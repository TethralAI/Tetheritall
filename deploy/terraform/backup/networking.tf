# Tethral Networking Infrastructure
# VPC, Subnets, Security Groups, and Network ACLs

# VPC
resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support

  tags = merge(local.tags, {
    Name = "${local.name}-vpc"
    "kubernetes.io/cluster/${local.name}" = "shared"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.name}-igw"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(local.azs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(local.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name = "${local.name}-public-${local.azs[count.index]}"
    "kubernetes.io/cluster/${local.name}" = "shared"
    "kubernetes.io/role/elb" = "1"
  })
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(local.azs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(local.vpc_cidr, 8, count.index + 10)
  availability_zone = local.azs[count.index]

  tags = merge(local.tags, {
    Name = "${local.name}-private-${local.azs[count.index]}"
    "kubernetes.io/cluster/${local.name}" = "shared"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

# Database Subnets
resource "aws_subnet" "database" {
  count = length(local.azs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(local.vpc_cidr, 8, count.index + 20)
  availability_zone = local.azs[count.index]

  tags = merge(local.tags, {
    Name = "${local.name}-database-${local.azs[count.index]}"
  })
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(local.azs)) : 0

  domain = "vpc"
  
  depends_on = [aws_internet_gateway.main]

  tags = merge(local.tags, {
    Name = "${local.name}-nat-eip-${count.index + 1}"
  })
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(local.azs)) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.tags, {
    Name = "${local.name}-nat-${count.index + 1}"
  })
}

# Route Tables - Public
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.tags, {
    Name = "${local.name}-public-rt"
  })
}

# Route Tables - Private
resource "aws_route_table" "private" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(local.azs)) : length(local.azs)

  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.main[0].id : aws_nat_gateway.main[count.index].id
    }
  }

  tags = merge(local.tags, {
    Name = "${local.name}-private-rt-${count.index + 1}"
  })
}

# Route Tables - Database
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.name}-database-rt"
  })
}

# Route Table Associations - Public
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Route Table Associations - Private
resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[count.index].id
}

# Route Table Associations - Database
resource "aws_route_table_association" "database" {
  count = length(aws_subnet.database)

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

# Database Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = merge(local.tags, {
    Name = "${local.name}-db-subnet-group"
  })
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = local.tags
}

# Security Groups

# EKS Cluster Security Group
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${local.name}-eks-cluster"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS inbound from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-eks-cluster-sg"
  })
}

# EKS Node Group Security Group
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${local.name}-eks-nodes"
  vpc_id      = aws_vpc.main.id

  # Allow nodes to communicate with each other
  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    self      = true
  }

  # Allow nodes to receive communication from cluster
  ingress {
    from_port                = 1025
    to_port                  = 65535
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.eks_cluster.id
  }

  # Allow HTTPS from cluster
  ingress {
    from_port                = 443
    to_port                  = 443
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.eks_cluster.id
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-eks-nodes-sg"
  })
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name_prefix = "${local.name}-rds"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL from EKS nodes
  ingress {
    from_port                = 5432
    to_port                  = 5432
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.eks_nodes.id
  }

  # Allow PostgreSQL from bastion (if needed)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-rds-sg"
  })
}

# ElastiCache Security Group
resource "aws_security_group" "elasticache" {
  name_prefix = "${local.name}-elasticache"
  vpc_id      = aws_vpc.main.id

  # Allow Redis from EKS nodes
  ingress {
    from_port                = var.redis_port
    to_port                  = var.redis_port
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.eks_nodes.id
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-elasticache-sg"
  })
}

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${local.name}-alb"
  vpc_id      = aws_vpc.main.id

  # Allow HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-alb-sg"
  })
}

# VPC Endpoints for private connectivity to AWS services
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  
  tags = merge(local.tags, {
    Name = "${local.name}-s3-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  
  tags = merge(local.tags, {
    Name = "${local.name}-ecr-api-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  
  tags = merge(local.tags, {
    Name = "${local.name}-ecr-dkr-endpoint"
  })
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${local.name}-vpc-endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-vpc-endpoints-sg"
  })
}
