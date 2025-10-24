cat > DEPLOYMENT.md << 'ENDFILE'
# 🚀 AURELIA AWS Deployment Guide - Enterprise Edition

Complete guide for deploying AURELIA to AWS infrastructure.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Deployment](#quick-deployment)
3. [Manual Deployment](#manual-deployment)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Cleanup](#cleanup)

---

## Prerequisites

### Required Tools
- **AWS CLI** v2.x
- **Docker** 20.x+
- **Docker Compose** v2.x
- **Git**
- **jq** (for JSON parsing)

### AWS Requirements
- AWS account with credits
- IAM permissions:
  - EC2 (Full Access)
  - S3 (Full Access)
  - IAM (Read Access)
  - CloudWatch (Full Access)

### API Keys Required
- **OpenAI API Key** with credits ($5-10 recommended)
- **AWS Access Keys** (Access Key ID + Secret)

### Install Prerequisites (Mac)
```bash
# Install AWS CLI
brew install awscli

# Install jq
brew install jq

# Verify installations
aws --version
docker --version
docker-compose --version
jq --version
```

---

## Quick Deployment (Recommended)

**Total Time: 15-20 minutes**

### Step 1: Configure AWS Credentials
```bash
aws configure
# Enter: AWS Access Key ID
# Enter: AWS Secret Access Key  
# Region: us-east-1
# Format: json
```

### Step 2: Run Automated Deployment
```bash
cd deployment/aws
chmod +x deploy.sh
./deploy.sh
```

The script will:
- ✅ Create S3 bucket for data storage
- ✅ Create SSH key pair for EC2 access
- ✅ Create security group with proper ports
- ✅ Launch EC2 instance (t3.xlarge)
- ✅ Upload application code
- ✅ Provide access URLs

**Estimated time: 10 minutes**

### Step 3: Configure Environment on EC2

After deploy.sh completes, you'll see the public IP. SSH into the instance:
```bash
ssh -i aurelia-key.pem ubuntu@PUBLIC_IP
```

On the EC2 instance:
```bash
# Edit .env file
nano .env

# Add these REQUIRED values:
OPENAI_API_KEY=sk-your-actual-openai-key
AWS_S3_BUCKET=aurelia-data-XXXXX  # From deployment output
```

Save and exit (Ctrl+X, Y, Enter)

### Step 4: Start Services
```bash
sudo docker-compose up -d
```

Wait 2-3 minutes for services to start, then:
```bash
# Check health
curl http://localhost:8000/health | jq .

# View logs
sudo docker-compose logs -f
```

### Step 5: Access Your Application

From your browser:
- **Frontend**: `http://PUBLIC_IP:8501`
- **API Docs**: `http://PUBLIC_IP:8000/docs`
- **Airflow**: `http://PUBLIC_IP:8080` (user: admin, pass: admin)

---

## Manual Deployment

### 1. Create S3 Bucket
```bash
BUCKET_NAME="aurelia-data-$(date +%s)"
aws s3 mb s3://${BUCKET_NAME} --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# Create folder structure
aws s3api put-object --bucket ${BUCKET_NAME} --key raw/
aws s3api put-object --bucket ${BUCKET_NAME} --key processed/
aws s3api put-object --bucket ${BUCKET_NAME} --key concepts/
```

### 2. Create Security Group
```bash
SG_ID=$(aws ec2 create-security-group \
    --group-name aurelia-sg \
    --description "AURELIA Security Group" \
    --query 'GroupId' --output text)

# Open required ports
for PORT in 22 8000 8501 8080 9090; do
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port $PORT \
        --cidr 0.0.0.0/0
done
```

### 3. Create SSH Key
```bash
aws ec2 create-key-pair \
    --key-name aurelia-key \
    --query 'KeyMaterial' \
    --output text > aurelia-key.pem

chmod 400 aurelia-key.pem
```

### 4. Launch EC2 Instance
```bash
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55b34f8f229 \
    --instance-type t3.xlarge \
    --key-name aurelia-key \
    --security-group-ids $SG_ID \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":50}}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

# Wait for instance
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Instance ready at: $PUBLIC_IP"
```

### 5. Upload Code to EC2
```bash
# Package project
tar -czf aurelia.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    .

# Upload
scp -i aurelia-key.pem aurelia.tar.gz ubuntu@$PUBLIC_IP:~/

# SSH and extract
ssh -i aurelia-key.pem ubuntu@$PUBLIC_IP
tar -xzf aurelia.tar.gz
```

### 6. Install Docker on EC2
```bash
# On EC2 instance:
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git
sudo usermod -aG docker ubuntu

# Logout and login again for group to take effect
exit
ssh -i aurelia-key.pem ubuntu@$PUBLIC_IP
```

### 7. Configure and Start
```bash
# Configure environment
cp .env.example .env
nano .env  # Add your API keys

# Start services
sudo docker-compose up -d

# Verify
sudo docker-compose ps
curl http://localhost:8000/health
```

---

## Configuration

### Required Environment Variables
```bash
# .env file minimum required:
OPENAI_API_KEY=sk-xxxxx
AWS_S3_BUCKET=aurelia-data-xxxxx
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Optional Advanced Configuration
```bash
# Vector DB
VECTOR_DB_TYPE=chromadb  # or pinecone
PINECONE_API_KEY=xxxxx   # if using Pinecone

# Performance tuning
TOP_K_RETRIEVAL=5
CONFIDENCE_THRESHOLD=0.7
CHUNK_SIZE=1000
EMBEDDING_BATCH_SIZE=100

# Features
ENABLE_RERANKING=true
RETRIEVAL_STRATEGY=hybrid
ENABLE_WIKIPEDIA_FALLBACK=true
```

---

## Verification

### 1. Check Service Health
```bash
# API Health
curl http://PUBLIC_IP:8000/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "checks": {
#     "database": {"status": "healthy"},
#     "vector_db": {"status": "healthy"},
#     "api": {"status": "healthy"}
#   }
# }
```

### 2. Test API Endpoints
```bash
# Query a concept
curl -X POST "http://PUBLIC_IP:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"concept_name": "Sharpe Ratio"}' | jq .

# Check statistics
curl http://PUBLIC_IP:8000/stats | jq .
```

### 3. Access Frontend

Open browser: `http://PUBLIC_IP:8501`

Test by querying: "Sharpe Ratio", "Duration", "Black-Scholes"

### 4. Verify Airflow

Open browser: `http://PUBLIC_IP:8080`
- Username: admin
- Password: admin

Check DAGs:
- `fintbx_ingest_dag`
- `concept_seed_dag`

---

## Troubleshooting

### Services Not Starting
```bash
# Check logs
sudo docker-compose logs api
sudo docker-compose logs frontend

# Restart services
sudo docker-compose restart

# Full restart
sudo docker-compose down
sudo docker-compose up -d
```

### OpenAI API Errors
```bash
# Verify API key is set
sudo docker-compose exec api printenv | grep OPENAI

# If missing, edit .env and restart
nano .env
sudo docker-compose restart api
```

### Database Connection Issues
```bash
# Check PostgreSQL
sudo docker-compose exec postgres psql -U aurelia_user -d aurelia -c "SELECT 1;"

# Recreate database
sudo docker-compose down -v
sudo docker-compose up -d
```

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :8000

# Stop conflicting service or change port in docker-compose.yml
```

---

## Cleanup (After Demo)

### Stop Services
```bash
# On EC2
sudo docker-compose down

# Remove volumes (optional)
sudo docker-compose down -v
```

### Terminate AWS Resources
```bash
# From your local machine

# Terminate EC2
aws ec2 terminate-instances --instance-ids INSTANCE_ID

# Delete S3 bucket
aws s3 rb s3://BUCKET_NAME --force

# Delete security group
aws ec2 delete-security-group --group-id SG_ID

# Delete key pair
aws ec2 delete-key-pair --key-name aurelia-key
rm aurelia-key.pem
```

**Using deployment_info.json:**
```bash
# If you have deployment_info.json from deploy.sh:
INSTANCE_ID=$(jq -r .instance_id deployment_info.json)
BUCKET=$(jq -r .s3_bucket deployment_info.json)
SG_ID=$(jq -r .security_group_id deployment_info.json)

aws ec2 terminate-instances --instance-ids $INSTANCE_ID
aws s3 rb s3://$BUCKET --force
aws ec2 delete-security-group --group-id $SG_ID
aws ec2 delete-key-pair --key-name aurelia-key
```

---

## Cost Estimates

### Development/Demo Period (3-4 days)

| Resource | Cost |
|----------|------|
| EC2 t3.xlarge | $0.17/hour × 72 hours = ~$12 |
| S3 Storage | <$1 |
| Data Transfer | <$2 |
| **Total** | **~$15** |

### After Cleanup
**Total Cost: $15** (if terminated within 3-4 days)

---

## Support

For issues:
- Check logs: `sudo docker-compose logs -f`
- GitHub Issues: [Your repo issues page]
- Team: Om Raut, Rayudu Hemanth, PeiYing

---

**Built for DAMG7245 - Northeastern University**
ENDFILE