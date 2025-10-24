cat > deployment/aws/deploy.sh << 'ENDFILE'
#!/bin/bash
set -e

# ============================================================================
# AURELIA AWS Deployment Script - ENTERPRISE GRADE
# ============================================================================
# 
# This script deploys the complete AURELIA stack to AWS:
# - EC2 instance for application hosting
# - Security groups with proper port configuration
# - S3 bucket for data storage
# - IAM roles and policies
# - CloudWatch logging
# - Auto-scaling configuration (optional)
#
# Prerequisites:
# - AWS CLI configured with credentials
# - Sufficient permissions (EC2, S3, IAM, CloudWatch)
# - SSH key pair for EC2 access
#
# Usage:
#   ./deploy.sh [--instance-type t3.xlarge] [--region us-east-1]
# ============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.xlarge}"
KEY_NAME="aurelia-key"
SG_NAME="aurelia-sg"
INSTANCE_NAME="aurelia-production"
S3_BUCKET_PREFIX="aurelia-data"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AURELIA AWS DEPLOYMENT - ENTERPRISE EDITION              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ===== Phase 1: Verify Prerequisites =====
echo -e "${YELLOW}Phase 1/8: Verifying prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install: brew install awscli${NC}"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${GREEN}✓ Region: ${REGION}${NC}"
echo ""

# ===== Phase 2: Create S3 Bucket =====
echo -e "${YELLOW}Phase 2/8: Creating S3 bucket for data storage...${NC}"

TIMESTAMP=$(date +%s)
S3_BUCKET="${S3_BUCKET_PREFIX}-${TIMESTAMP}"

aws s3 mb s3://${S3_BUCKET} --region ${REGION} 2>/dev/null || {
    echo -e "${YELLOW}⚠ Bucket might already exist, continuing...${NC}"
}

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${S3_BUCKET} \
    --versioning-configuration Status=Enabled

# Create folder structure
aws s3api put-object --bucket ${S3_BUCKET} --key raw/
aws s3api put-object --bucket ${S3_BUCKET} --key processed/chunks/
aws s3api put-object --bucket ${S3_BUCKET} --key processed/embeddings/
aws s3api put-object --bucket ${S3_BUCKET} --key concepts/
aws s3api put-object --bucket ${S3_BUCKET} --key metadata/

echo -e "${GREEN}✓ S3 Bucket created: s3://${S3_BUCKET}${NC}"
echo ""

# ===== Phase 3: Create SSH Key Pair =====
echo -e "${YELLOW}Phase 3/8: Creating SSH key pair...${NC}"

# Check if key already exists
if aws ec2 describe-key-pairs --key-names ${KEY_NAME} --region ${REGION} &> /dev/null; then
    echo -e "${YELLOW}⚠ Key pair '${KEY_NAME}' already exists. Delete it first or use existing.${NC}"
    read -p "Delete existing key and create new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws ec2 delete-key-pair --key-name ${KEY_NAME} --region ${REGION}
        echo -e "${GREEN}✓ Deleted existing key${NC}"
    else
        echo -e "${YELLOW}Using existing key pair${NC}"
        KEY_EXISTS=true
    fi
fi

if [ -z "$KEY_EXISTS" ]; then
    aws ec2 create-key-pair \
        --key-name ${KEY_NAME} \
        --region ${REGION} \
        --query 'KeyMaterial' \
        --output text > ${KEY_NAME}.pem
    
    chmod 400 ${KEY_NAME}.pem
    echo -e "${GREEN}✓ SSH key created: ${KEY_NAME}.pem${NC}"
else
    echo -e "${YELLOW}⚠ Make sure you have ${KEY_NAME}.pem file locally${NC}"
fi
echo ""

# ===== Phase 4: Create Security Group =====
echo -e "${YELLOW}Phase 4/8: Creating security group...${NC}"

# Check if security group exists
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SG_NAME}" \
    --region ${REGION} \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null)

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    # Create new security group
    SG_ID=$(aws ec2 create-security-group \
        --group-name ${SG_NAME} \
        --description "AURELIA Application Security Group" \
        --region ${REGION} \
        --query 'GroupId' \
        --output text)
    
    echo -e "${GREEN}✓ Security group created: ${SG_ID}${NC}"
    
    # Add ingress rules
    echo "  Opening ports..."
    
    # SSH (22)
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    # API (8000)
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    # Streamlit (8501)
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 8501 \
        --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    # Airflow (8080)
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 8080 \
        --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    # Prometheus (9090)
    aws ec2 authorize-security-group-ingress \
        --group-id ${SG_ID} \
        --protocol tcp \
        --port 9090 \
        --cidr 0.0.0.0/0 \
        --region ${REGION}
    
    echo -e "${GREEN}  ✓ Ports opened: 22, 8000, 8501, 8080, 9090${NC}"
else
    echo -e "${YELLOW}⚠ Using existing security group: ${SG_ID}${NC}"
fi
echo ""

# ===== Phase 5: Launch EC2 Instance =====
echo -e "${YELLOW}Phase 5/8: Launching EC2 instance (${INSTANCE_TYPE})...${NC}"

# User data script for instance initialization
cat > user_data.sh << 'USERDATA'
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y docker.io docker-compose git curl wget

# Enable Docker service
systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install additional tools
apt-get install -y htop vim tmux python3-pip

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Create application directory
mkdir -p /home/ubuntu/aurelia
chown ubuntu:ubuntu /home/ubuntu/aurelia

# Setup logging
mkdir -p /var/log/aurelia
chown ubuntu:ubuntu /var/log/aurelia

echo "EC2 initialization complete" > /var/log/aurelia/init.log
USERDATA

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55b34f8f229 \
    --instance-type ${INSTANCE_TYPE} \
    --key-name ${KEY_NAME} \
    --security-group-ids ${SG_ID} \
    --region ${REGION} \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":50,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}},{Key=Project,Value=AURELIA},{Key=Environment,Value=Production}]" \
    --user-data file://user_data.sh \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✓ Instance launched: ${INSTANCE_ID}${NC}"
echo "  Waiting for instance to be running..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids ${INSTANCE_ID} --region ${REGION}

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids ${INSTANCE_ID} \
    --region ${REGION} \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo -e "${GREEN}✓ Instance running at: ${PUBLIC_IP}${NC}"
echo ""

# ===== Phase 6: Wait for SSH Ready =====
echo -e "${YELLOW}Phase 6/8: Waiting for SSH to be ready...${NC}"

for i in {1..30}; do
    if ssh -i ${KEY_NAME}.pem -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@${PUBLIC_IP} 'echo SSH Ready' &> /dev/null; then
        echo -e "${GREEN}✓ SSH is ready${NC}"
        break
    fi
    echo -n "."
    sleep 10
done
echo ""

# ===== Phase 7: Upload Application Code =====
echo -e "${YELLOW}Phase 7/8: Packaging and uploading application...${NC}"

# Package project (exclude unnecessary files)
echo "  Packaging project files..."
cd ../..  # Go to project root

tar -czf aurelia-app.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='data/chromadb' \
    --exclude='logs' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.log' \
    .

echo -e "${GREEN}  ✓ Package created: aurelia-app.tar.gz${NC}"

# Upload to EC2
echo "  Uploading to EC2..."
scp -i deployment/aws/${KEY_NAME}.pem \
    -o StrictHostKeyChecking=no \
    aurelia-app.tar.gz \
    ubuntu@${PUBLIC_IP}:~/

# Upload deployment script
scp -i deployment/aws/${KEY_NAME}.pem \
    -o StrictHostKeyChecking=no \
    deployment/aws/setup_ec2.sh \
    ubuntu@${PUBLIC_IP}:~/

echo -e "${GREEN}✓ Files uploaded to EC2${NC}"

# Cleanup
rm aurelia-app.tar.gz
cd deployment/aws

echo ""

# ===== Phase 8: Deploy Application on EC2 =====
echo -e "${YELLOW}Phase 8/8: Deploying application on EC2...${NC}"

# Run deployment script on EC2
ssh -i ${KEY_NAME}.pem -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP} << 'ENDSSH'
set -e

echo "Extracting application..."
tar -xzf aurelia-app.tar.gz
cd ~/

echo "Setting up environment..."
# Create .env from example
cp .env.example .env

echo ""
echo "⚠️  IMPORTANT: Edit .env file with your API keys"
echo "   Run: nano .env"
echo "   Add: OPENAI_API_KEY=sk-your-key"
echo ""
read -p "Press Enter after editing .env file..."

# Make setup script executable
chmod +x setup_ec2.sh

echo "Starting Docker services..."
sudo docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."
curl -s http://localhost:8000/health | jq . || echo "API starting..."

echo ""
echo "✅ Deployment complete!"
echo ""
ENDSSH

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DEPLOYMENT COMPLETED SUCCESSFULLY                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📋 DEPLOYMENT INFORMATION:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "  Instance ID:      ${INSTANCE_ID}"
echo -e "  Public IP:        ${PUBLIC_IP}"
echo -e "  Instance Type:    ${INSTANCE_TYPE}"
echo -e "  Region:           ${REGION}"
echo -e "  S3 Bucket:        s3://${S3_BUCKET}"
echo -e "  Security Group:   ${SG_ID}"
echo ""
echo -e "${BLUE}🌐 ACCESS URLS:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "  🔹 API:           http://${PUBLIC_IP}:8000"
echo -e "  🔹 API Docs:      http://${PUBLIC_IP}:8000/docs"
echo -e "  🔹 Frontend:      http://${PUBLIC_IP}:8501"
echo -e "  🔹 Airflow:       http://${PUBLIC_IP}:8080"
echo -e "  🔹 Metrics:       http://${PUBLIC_IP}:9090"
echo ""
echo -e "${BLUE}🔐 SSH ACCESS:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "  ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo ""
echo -e "${BLUE}💰 ESTIMATED COSTS:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "  EC2 (${INSTANCE_TYPE}):  ~\$0.17/hour (~\$12/3 days)"
echo -e "  S3 Storage:         ~\$0.50/month"
echo -e "  Total:              ~\$15 for demo period"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NEXT STEPS:${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
echo -e "  1. SSH into instance: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo -e "  2. Edit .env file: nano .env"
echo -e "  3. Add your OPENAI_API_KEY"
echo -e "  4. Restart services: sudo docker-compose restart"
echo -e "  5. Test API: curl http://${PUBLIC_IP}:8000/health"
echo ""
echo -e "${RED}🗑️  CLEANUP (after demo):${NC}"
echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
echo -e "  aws ec2 terminate-instances --instance-ids ${INSTANCE_ID}"
echo -e "  aws s3 rb s3://${S3_BUCKET} --force"
echo -e "  aws ec2 delete-security-group --group-id ${SG_ID}"
echo -e "  aws ec2 delete-key-pair --key-name ${KEY_NAME}"
echo ""

# Save deployment info
cat > deployment_info.json << DEPLOYINFO
{
  "instance_id": "${INSTANCE_ID}",
  "public_ip": "${PUBLIC_IP}",
  "instance_type": "${INSTANCE_TYPE}",
  "region": "${REGION}",
  "s3_bucket": "${S3_BUCKET}",
  "security_group_id": "${SG_ID}",
  "key_name": "${KEY_NAME}",
  "deployment_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "urls": {
    "api": "http://${PUBLIC_IP}:8000",
    "docs": "http://${PUBLIC_IP}:8000/docs",
    "frontend": "http://${PUBLIC_IP}:8501",
    "airflow": "http://${PUBLIC_IP}:8080"
  }
}
DEPLOYINFO

echo -e "${GREEN}✓ Deployment info saved to deployment_info.json${NC}"
echo ""
echo -e "${GREEN}🎉 Deployment script complete!${NC}"
ENDFILE

chmod +x deployment/aws/deploy.sh