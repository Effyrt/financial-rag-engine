cat > deployment/aws/terraform/user_data.sh.tpl << 'ENDFILE'
#!/bin/bash
set -e

# ============================================================================
# EC2 User Data Script - AURELIA Initialization
# ============================================================================

echo "Starting AURELIA EC2 initialization..."

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install additional tools
apt-get install -y git curl wget vim htop jq

# Enable Docker service
systemctl enable docker
systemctl start docker

# Create application directory
mkdir -p /home/ubuntu/aurelia
chown -R ubuntu:ubuntu /home/ubuntu/aurelia

# Create log directory
mkdir -p /var/log/aurelia
chown -R ubuntu:ubuntu /var/log/aurelia

# Set environment variables
cat >> /home/ubuntu/.bashrc << 'BASHRC'
export AWS_S3_BUCKET="${s3_bucket}"
export AWS_REGION="${aws_region}"
export ENVIRONMENT="${environment}"
BASHRC

# Log completion
echo "EC2 initialization complete at $(date)" > /var/log/aurelia/init.log
echo "S3 Bucket: ${s3_bucket}" >> /var/log/aurelia/init.log
echo "Region: ${aws_region}" >> /var/log/aurelia/init.log

# Signal success
echo "AURELIA EC2 ready"
ENDFILE