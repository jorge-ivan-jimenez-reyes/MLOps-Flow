# =============================================================================
# RDS Module (Postgres)
# =============================================================================

# -----------------------------------------------------------------------------
# Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name        = "${var.identifier}-sg"
  description = "Security group for RDS"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.identifier}-sg"
  }
}

# -----------------------------------------------------------------------------
# Subnet Group
# -----------------------------------------------------------------------------
resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.identifier}-subnet-group"
  }
}

# -----------------------------------------------------------------------------
# Random Password
# -----------------------------------------------------------------------------
resource "random_password" "db_password" {
  length  = 16
  special = false
}

# -----------------------------------------------------------------------------
# RDS Instance
# -----------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier = var.identifier

  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  multi_az               = false
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  tags = {
    Name        = var.identifier
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Store password in SSM Parameter Store
# -----------------------------------------------------------------------------
resource "aws_ssm_parameter" "db_password" {
  name        = "/${var.environment}/rds/${var.identifier}/password"
  description = "RDS password for ${var.identifier}"
  type        = "SecureString"
  value       = random_password.db_password.result

  tags = {
    Environment = var.environment
  }
}

