# =============================================================================
# FHIR Automapper - MLOps Infrastructure
# Main Terraform Configuration
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "fhir-automapper"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# Local Values
# -----------------------------------------------------------------------------
locals {
  name            = "fhir-automapper-${var.environment}"
  cluster_name    = "${local.name}-eks"
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
}

# -----------------------------------------------------------------------------
# Modules
# -----------------------------------------------------------------------------

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  name               = local.name
  cidr               = var.vpc_cidr
  availability_zones = local.azs
  environment        = var.environment
}

# EKS Module
module "eks" {
  source = "./modules/eks"

  cluster_name       = local.cluster_name
  cluster_version    = var.eks_cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  environment        = var.environment

  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
}

# S3 Module (Para artefactos de MLflow)
module "s3" {
  source = "./modules/s3"

  bucket_name = "${local.name}-mlflow-artifacts"
  environment = var.environment
}

# RDS Module (Postgres para MLflow y App)
module "rds" {
  source = "./modules/rds"

  identifier         = "${local.name}-db"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [var.vpc_cidr]
  
  db_name            = var.db_name
  db_username        = var.db_username
  environment        = var.environment
}

# ECR Module (Container Repositories)
module "ecr" {
  source = "./modules/ecr"

  repository_names = [
    "fhir-automapper/gateway-api",
    "fhir-automapper/ml-inference",
    "fhir-automapper/ml-trainer",
    "fhir-automapper/frontend"
  ]
  environment = var.environment
}

