#!/bin/bash
set -e

echo "🚀 AURELIA AWS Deployment"

REGION="us-east-1"

# Create key pair
aws ec2 create-key-pair --key-name aurelia-key --region $REGION --query 'KeyMaterial' --output text > aurelia-key.pem
chmod 400 aurelia-key.pem

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name aurelia-sg \
    --description "AURELIA" \
    --region $REGION \
    --query 'GroupId' --output text)

# Open ports
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8501 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8080 --cidr 0.0.0.0/0

# Launch EC2
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55b34f8f229 \
    --instance-type t3.xlarge \
    --key-name aurelia-key \
    --security-group-ids $SG_ID \
    --region $REGION \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=aurelia}]' \
    --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo ""
echo "✅ EC2 Created: $PUBLIC_IP"
echo "Instance ID: $INSTANCE_ID"
echo ""
echo "Save these for cleanup:"
echo "export AURELIA_INSTANCE_ID=$INSTANCE_ID"
echo "export AURELIA_SG_ID=$SG_ID"
