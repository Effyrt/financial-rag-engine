cat > deployment/aws/terraform/main.tf << 'ENDFILE'
# ============================================================================
# AURELIA Terraform Configuration - AWS Infrastructure
# ============================================================================
# Provisions complete AWS infrastructure for AURELIA deployment
# - EC2 instance for application hosting
# - S3 bucket for data storage
# - Security groups and IAM roles
# - CloudWatch monitoring
# ============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# Provider Configuration
# ============================================================================

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "AURELIA"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Course      = "DAMG7245"
      Team        = "Effyrt"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================================
# S3 Bucket for Data Storage
# ============================================================================

resource "aws_s3_bucket" "aurelia_data" {
  bucket = "aurelia-data-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "AURELIA Data Bucket"
    Description = "Storage for PDFs, chunks, embeddings, and results"
  }
}

resource "aws_s3_bucket_versioning" "aurelia_versioning" {
  bucket = aws_s3_bucket.aurelia_data.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "aurelia_encryption" {
  bucket = aws_s3_bucket.aurelia_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "aurelia_lifecycle" {
  bucket = aws_s3_bucket.aurelia_data.id
  
  rule {
    id     = "delete-old-versions"
    status = "Enabled"
    
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
  
  rule {
    id     = "cleanup-temp-files"
    status = "Enabled"
    
    filter {
      prefix = "tmp/"
    }
    
    expiration {
      days = 7
    }
  }
}

# ============================================================================
# Security Group
# ============================================================================

resource "aws_security_group" "aurelia_sg" {
  name        = "aurelia-sg-${var.environment}"
  description = "Security group for AURELIA application services"
  
  # SSH Access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
    description = "SSH access"
  }
  
  # FastAPI
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "FastAPI REST API"
  }
  
  # Streamlit Frontend
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Streamlit UI"
  }
  
  # Airflow Web UI
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Airflow Web Interface"
  }
  
  # Prometheus Metrics
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Prometheus Metrics"
  }
  
  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = {
    Name = "AURELIA Security Group"
  }
}

# ============================================================================
# IAM Role for EC2 Instance
# ============================================================================

resource "aws_iam_role" "aurelia_ec2_role" {
  name = "aurelia-ec2-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "AURELIA EC2 Role"
  }
}

# Attach S3 access policy
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.aurelia_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Attach CloudWatch access
resource "aws_iam_role_policy_attachment" "cloudwatch_access" {
  role       = aws_iam_role.aurelia_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Create instance profile
resource "aws_iam_instance_profile" "aurelia_profile" {
  name = "aurelia-instance-profile-${var.environment}"
  role = aws_iam_role.aurelia_ec2_role.name
}

# ============================================================================
# EC2 Key Pair
# ============================================================================

resource "aws_key_pair" "aurelia_key" {
  key_name   = "aurelia-key-${var.environment}"
  public_key = file(var.public_key_path)
}

# ============================================================================
# EC2 Instance
# ============================================================================

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "aurelia_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.aurelia_key.key_name
  vpc_security_group_ids = [aws_security_group.aurelia_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.aurelia_profile.name
  
  root_block_device {
    volume_size           = 50
    volume_type           = "gp3"
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
    encrypted             = true
  }
  
  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    s3_bucket        = aws_s3_bucket.aurelia_data.id
    aws_region       = var.aws_region
    environment      = var.environment
  })
  
  tags = {
    Name        = "AURELIA Production Server"
    Application = "Financial RAG Engine"
  }
  
  monitoring = true
  
  lifecycle {
    create_before_destroy = false
  }
}

# Elastic IP (optional - for stable IP)
resource "aws_eip" "aurelia_eip" {
  count    = var.use_elastic_ip ? 1 : 0
  instance = aws_instance.aurelia_server.id
  domain   = "vpc"
  
  tags = {
    Name = "AURELIA Elastic IP"
  }
}

# ============================================================================
# CloudWatch Log Group
# ============================================================================

resource "aws_cloudwatch_log_group" "aurelia_logs" {
  name              = "/aws/ec2/aurelia-${var.environment}"
  retention_in_days = 7
  
  tags = {
    Name = "AURELIA Application Logs"
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.aurelia_server.id
}

output "instance_public_ip" {
  description = "EC2 Public IP Address"
  value       = aws_instance.aurelia_server.public_ip
}

output "instance_public_dns" {
  description = "EC2 Public DNS"
  value       = aws_instance.aurelia_server.public_dns
}

output "s3_bucket_name" {
  description = "S3 Bucket Name"
  value       = aws_s3_bucket.aurelia_data.id
}

output "s3_bucket_arn" {
  description = "S3 Bucket ARN"
  value       = aws_s3_bucket.aurelia_data.arn
}

output "security_group_id" {
  description = "Security Group ID"
  value       = aws_security_group.aurelia_sg.id
}

output "api_url" {
  description = "AURELIA API URL"
  value       = "http://${aws_instance.aurelia_server.public_ip}:8000"
}

output "frontend_url" {
  description = "AURELIA Frontend URL"
  value       = "http://${aws_instance.aurelia_server.public_ip}:8501"
}

output "api_docs_url" {
  description = "API Documentation URL"
  value       = "http://${aws_instance.aurelia_server.public_ip}:8000/docs"
}

output "airflow_url" {
  description = "Airflow Web UI URL"
  value       = "http://${aws_instance.aurelia_server.public_ip}:8080"
}

output "ssh_command" {
  description = "SSH Command to connect to instance"
  value       = "ssh -i aurelia-key.pem ubuntu@${aws_instance.aurelia_server.public_ip}"
}

output "deployment_summary" {
  description = "Complete deployment information"
  value = {
    instance_id     = aws_instance.aurelia_server.id
    public_ip       = aws_instance.aurelia_server.public_ip
    s3_bucket       = aws_s3_bucket.aurelia_data.id
    security_group  = aws_security_group.aurelia_sg.id
    region          = var.aws_region
    instance_type   = var.instance_type
    deployment_date = timestamp()
  }
}
ENDFILE