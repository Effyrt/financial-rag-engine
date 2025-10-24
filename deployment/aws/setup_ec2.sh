cat > deployment/aws/setup_ec2.sh << 'ENDFILE'
#!/bin/bash
set -e

# ============================================================================
# AURELIA EC2 Setup Script - Run on EC2 Instance
# ============================================================================

echo "🚀 AURELIA EC2 Setup Starting..."

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)
echo "Public IP: ${PUBLIC_IP}"

# Ensure Docker is ready
echo "Checking Docker installation..."
sudo systemctl status docker || sudo systemctl start docker

# Configure environment
echo ""
echo "📝 Configuring environment variables..."
echo ""
echo "⚠️  CRITICAL: You must add your OpenAI API key to the .env file"
echo ""
echo "Required environment variables:"
echo "  - OPENAI_API_KEY=sk-your-actual-key-here"
echo "  - AWS_S3_BUCKET=your-s3-bucket-name"
echo ""

if [ -f .env ]; then
    echo "✓ .env file exists"
else
    echo "Creating .env from template..."
    cp .env.example .env
fi

echo ""
echo "Opening .env file for editing..."
echo "Add your OPENAI_API_KEY and AWS credentials, then save and exit"
echo ""
read -p "Press Enter to open nano editor..." 

nano .env

echo ""
echo "Starting Docker services..."
sudo docker-compose pull
sudo docker-compose up -d --build

echo ""
echo "Waiting for services to initialize (60 seconds)..."
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""

# Check service health
echo ""
echo "🔍 Checking service health..."
echo ""

echo "PostgreSQL:"
sudo docker-compose ps postgres

echo ""
echo "Redis:"
sudo docker-compose ps redis

echo ""
echo "ChromaDB:"
sudo docker-compose ps chromadb

echo ""
echo "API:"
sudo docker-compose ps api
curl -s http://localhost:8000/health | jq '.' || echo "API still starting..."

echo ""
echo "Frontend:"
sudo docker-compose ps frontend

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                  AURELIA DEPLOYMENT COMPLETE                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access URLs:"
echo "  API:           http://${PUBLIC_IP}:8000"
echo "  API Docs:      http://${PUBLIC_IP}:8000/docs"
echo "  Frontend:      http://${PUBLIC_IP}:8501"
echo "  Airflow:       http://${PUBLIC_IP}:8080"
echo "  Metrics:       http://${PUBLIC_IP}:9090"
echo ""
echo "📊 View logs:"
echo "  API:           sudo docker-compose logs -f api"
echo "  Frontend:      sudo docker-compose logs -f frontend"
echo "  All services:  sudo docker-compose logs -f"
echo ""
echo "🔧 Useful commands:"
echo "  Restart API:        sudo docker-compose restart api"
echo "  Restart all:        sudo docker-compose restart"
echo "  Stop all:           sudo docker-compose down"
echo "  View containers:    sudo docker-compose ps"
echo ""
echo "✅ Setup complete! Test at http://${PUBLIC_IP}:8501"
echo ""
ENDFILE

chmod +x deployment/aws/setup_ec2.sh