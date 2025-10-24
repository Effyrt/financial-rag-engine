# AURELIA AWS Deployment Guide

## Prerequisites
- AWS account with EC2 permissions
- AWS CLI installed and configured
- OpenAI API key with credits

## Quick Deploy
```bash
cat > DEPLOYMENT.md << 'ENDFILE'
# AURELIA AWS Deployment Guide

## Prerequisites
- AWS account with EC2 permissions
- AWS CLI installed and configured
- OpenAI API key with credits

## Quick Deploy
```bash
cd deployment/aws
./deploy.sh
```

After script completes, you'll get the EC2 public IP.

Then:
```bash
# Package code
tar -czf aurelia.tar.gz ../.. --exclude='venv' --exclude='__pycache__'

# Upload to EC2
scp -i aurelia-key.pem aurelia.tar.gz ubuntu@PUBLIC_IP:~/

# SSH to EC2
ssh -i aurelia-key.pem ubuntu@PUBLIC_IP

# On EC2:
tar -xzf aurelia.tar.gz
cd project-aurelia
nano .env  # Add OPENAI_API_KEY
docker-compose up -d
```

## Access
- API: http://PUBLIC_IP:8000
- Frontend: http://PUBLIC_IP:8501
- Docs: http://PUBLIC_IP:8000/docs

## Cost: ~$15 for demo
