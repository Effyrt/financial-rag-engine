#!/bin/bash
set -e

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git
sudo usermod -aG docker ubuntu
sudo systemctl start docker

# Extract project
tar -xzf aurelia.tar.gz

# Setup .env
echo "Add your OPENAI_API_KEY to .env:"
nano .env

# Start services
sudo docker-compose up -d

PUBLIC_IP=$(curl -s ifconfig.me)

echo ""
echo "✅ AURELIA Running!"
echo "API: http://$PUBLIC_IP:8000"
echo "Frontend: http://$PUBLIC_IP:8501"
