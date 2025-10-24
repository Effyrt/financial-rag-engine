cat > deployment/aws/terraform/variables.tf << 'ENDFILE'
# ============================================================================
# Terraform Variables for AURELIA AWS Deployment
# ============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development"
  }
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.xlarge"
  
  validation {
    condition     = can(regex("^t[2-3]\\.(micro|small|medium|large|xlarge|2xlarge)$", var.instance_type))
    error_message = "Instance type must be a valid t2 or t3 instance type"
  }
}

variable "public_key_path" {
  description = "Path to SSH public key for EC2 access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_cidr" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "use_elastic_ip" {
  description = "Whether to use Elastic IP for stable IP address"
  type        = bool
  default     = false
}

variable "enable_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
ENDFILE