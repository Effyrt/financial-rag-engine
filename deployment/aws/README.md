# AWS Deployment Instructions

## Step 1: Deploy EC2
```bash
cd deployment/aws
./deploy.sh
```

## Step 2: Upload Code
```bash
tar -czf aurelia.tar.gz ../.. --exclude='venv' --exclude='__pycache__'
scp -i aurelia-key.pem aurelia.tar.gz ubuntu@PUBLIC_IP:~/
scp -i aurelia-key.pem setup.sh ubuntu@PUBLIC_IP:~/
```

## Step 3: Setup on EC2
```bash
ssh -i aurelia-key.pem ubuntu@PUBLIC_IP
bash setup.sh
```

## Access
- API: http://PUBLIC_IP:8000
- Frontend: http://PUBLIC_IP:8501

## Cleanup
```bash
aws ec2 terminate-instances --instance-ids INSTANCE_ID
```

Cost: ~$15 for demo
