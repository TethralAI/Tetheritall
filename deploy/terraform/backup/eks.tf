# Tethral EKS Cluster Configuration
# Amazon EKS cluster with managed node groups

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = local.name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_cidr_blocks
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
    aws_cloudwatch_log_group.eks_cluster,
  ]

  tags = local.tags
}

# CloudWatch Log Group for EKS
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${local.name}/cluster"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = local.tags
}

# EKS Managed Node Group - Primary
resource "aws_eks_node_group" "primary" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name}-primary"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.node_instance_types

  scaling_config {
    desired_size = var.node_desired_capacity
    max_size     = var.node_max_capacity
    min_size     = var.node_min_capacity
  }

  update_config {
    max_unavailable_percentage = 25
  }

  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling.
  # Otherwise, EKS will not be able to properly delete EC2 Instances and Elastic Network Interfaces.
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_readonly,
  ]

  # Optional: Launch template for advanced configuration
  launch_template {
    id      = aws_launch_template.eks_nodes.id
    version = aws_launch_template.eks_nodes.latest_version
  }

  tags = merge(local.tags, {
    Name = "${local.name}-primary-node-group"
  })
}

# Launch Template for EKS Nodes
resource "aws_launch_template" "eks_nodes" {
  name_prefix   = "${local.name}-node-template"
  image_id      = data.aws_ssm_parameter.eks_ami_release_version.value
  instance_type = var.node_instance_types[0]

  vpc_security_group_ids = [aws_security_group.eks_nodes.id]

  user_data = base64encode(templatefile("${path.module}/templates/userdata.sh", {
    cluster_name        = local.name
    cluster_endpoint    = aws_eks_cluster.main.endpoint
    cluster_ca          = aws_eks_cluster.main.certificate_authority[0].data
    bootstrap_arguments = "--container-runtime containerd"
  }))

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 50
      volume_type           = "gp3"
      iops                  = 3000
      throughput            = 125
      encrypted             = var.enable_encryption
      kms_key_id            = var.enable_encryption ? aws_kms_key.ebs.arn : null
      delete_on_termination = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  monitoring {
    enabled = true
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.tags, {
      Name = "${local.name}-node"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.tags, {
      Name = "${local.name}-node-volume"
    })
  }

  tags = local.tags
}

# Spot Instance Node Group (Optional)
resource "aws_eks_node_group" "spot" {
  count = var.enable_spot_instances ? 1 : 0

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name}-spot"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.spot_instance_types
  capacity_type   = "SPOT"

  scaling_config {
    desired_size = 1
    max_size     = var.node_max_capacity
    min_size     = 0
  }

  update_config {
    max_unavailable_percentage = 50
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_readonly,
  ]

  tags = merge(local.tags, {
    Name = "${local.name}-spot-node-group"
  })
}

# Data source for EKS AMI
data "aws_ssm_parameter" "eks_ami_release_version" {
  name = "/aws/service/eks/optimized-ami/${var.cluster_version}/amazon-linux-2/recommended/image_id"
}

# EKS Add-ons
resource "aws_eks_addon" "coredns" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "coredns"
  addon_version            = data.aws_eks_addon_version.coredns.version
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = aws_iam_role.eks_addon_coredns.arn

  depends_on = [aws_eks_node_group.primary]

  tags = local.tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name      = aws_eks_cluster.main.name
  addon_name        = "kube-proxy"
  addon_version     = data.aws_eks_addon_version.kube_proxy.version
  resolve_conflicts = "OVERWRITE"

  depends_on = [aws_eks_node_group.primary]

  tags = local.tags
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "vpc-cni"
  addon_version            = data.aws_eks_addon_version.vpc_cni.version
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = aws_iam_role.eks_addon_vpc_cni.arn

  depends_on = [aws_eks_node_group.primary]

  tags = local.tags
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = data.aws_eks_addon_version.ebs_csi.version
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = aws_iam_role.eks_addon_ebs_csi.arn

  depends_on = [aws_eks_node_group.primary]

  tags = local.tags
}

# Data sources for addon versions
data "aws_eks_addon_version" "coredns" {
  addon_name         = "coredns"
  kubernetes_version = var.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "kube_proxy" {
  addon_name         = "kube-proxy"
  kubernetes_version = var.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "vpc_cni" {
  addon_name         = "vpc-cni"
  kubernetes_version = var.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "ebs_csi" {
  addon_name         = "aws-ebs-csi-driver"
  kubernetes_version = var.cluster_version
  most_recent        = true
}

# Configure kubectl access
resource "null_resource" "kubectl_config" {
  depends_on = [aws_eks_cluster.main]

  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.name} --alias ${local.name}"
  }

  triggers = {
    cluster_name = aws_eks_cluster.main.name
    endpoint     = aws_eks_cluster.main.endpoint
  }
}
