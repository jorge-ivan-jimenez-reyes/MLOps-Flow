# =============================================================================
# Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# VPC
# -----------------------------------------------------------------------------
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

# -----------------------------------------------------------------------------
# EKS
# -----------------------------------------------------------------------------
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_certificate" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# -----------------------------------------------------------------------------
# S3
# -----------------------------------------------------------------------------
output "mlflow_bucket_name" {
  description = "S3 bucket for MLflow artifacts"
  value       = module.s3.bucket_name
}

output "mlflow_bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.s3.bucket_arn
}

# -----------------------------------------------------------------------------
# RDS
# -----------------------------------------------------------------------------
output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "rds_port" {
  description = "RDS port"
  value       = module.rds.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.database_name
}

# -----------------------------------------------------------------------------
# ECR
# -----------------------------------------------------------------------------
output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value       = module.ecr.repository_urls
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

