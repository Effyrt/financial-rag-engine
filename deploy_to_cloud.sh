#!/bin/bash

# Cloud Deployment Script for Financial RAG Engine
# This script deploys the entire system to GCP

set -e

echo "🚀 Deploying Financial RAG Engine to GCP"
echo "========================================"

# Configuration
PROJECT_ID="financial-rag-engine"
REGION="us-central1"
BUCKET_NAME="financial-rag-data"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set project
print_status "Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable APIs
print_status "Enabling required APIs"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    cloudresourcemanager.googleapis.com

# Create bucket if it doesn't exist
print_status "Creating Cloud Storage bucket"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME || true

# Create bucket structure
print_status "Creating bucket folder structure"
gsutil mkdir gs://$BUCKET_NAME/pdf-files || true
gsutil mkdir gs://$BUCKET_NAME/processed-data || true
gsutil mkdir gs://$BUCKET_NAME/embeddings || true

# Upload PDF file if it exists locally
if [ -f "fintbx.pdf" ]; then
    print_status "Uploading PDF file to Cloud Storage"
    gsutil cp fintbx.pdf gs://$BUCKET_NAME/pdf-files/
else
    print_warning "fintbx.pdf not found locally. Please upload it manually to gs://$BUCKET_NAME/pdf-files/"
fi

# Create secrets
print_status "Setting up secrets in Secret Manager"

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OPENAI_API_KEY environment variable not set."
    echo "Please enter your OpenAI API key:"
    read -s OPENAI_API_KEY
fi

# Create OpenAI API key secret
echo $OPENAI_API_KEY | gcloud secrets create openai-api-key --data-file=- || true

# Build Docker images
print_status "Building Docker images"

# Build PDF processor image
print_status "Building PDF processor image"
gcloud builds submit --tag gcr.io/$PROJECT_ID/pdf-processor . -f cloud_run_jobs/Dockerfile.pdf-processor

# Build backend image
print_status "Building backend image"
gcloud builds submit --tag gcr.io/$PROJECT_ID/financial-rag-backend . -f backend/Dockerfile

# Build frontend image
print_status "Building frontend image"
gcloud builds submit --tag gcr.io/$PROJECT_ID/financial-rag-frontend . -f frontend/Dockerfile

# Deploy Cloud Run Jobs
print_status "Deploying Cloud Run Jobs"

# PDF Processing Job
gcloud run jobs create pdf-processor \
    --image gcr.io/$PROJECT_ID/pdf-processor \
    --region $REGION \
    --memory 4Gi \
    --cpu 2 \
    --max-retries 3 \
    --parallelism 1 \
    --task-count 1 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME,PAGES=all" \
    --service-account="financial-rag-sa@$PROJECT_ID.iam.gserviceaccount.com" || true

# Deploy Cloud Run Services
print_status "Deploying Cloud Run Services"

# Backend Service
gcloud run deploy financial-rag-backend \
    --image gcr.io/$PROJECT_ID/financial-rag-backend \
    --region $REGION \
    --memory 2Gi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 1 \
    --port 8000 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME" \
    --allow-unauthenticated || true

# Frontend Service
BACKEND_URL=$(gcloud run services describe financial-rag-backend --region=$REGION --format="value(status.url)")
gcloud run deploy financial-rag-frontend \
    --image gcr.io/$PROJECT_ID/financial-rag-frontend \
    --region $REGION \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5 \
    --min-instances 1 \
    --port 8501 \
    --set-env-vars="BACKEND_URL=$BACKEND_URL" \
    --allow-unauthenticated || true

# Get service URLs
BACKEND_URL=$(gcloud run services describe financial-rag-backend --region=$REGION --format="value(status.url)")
FRONTEND_URL=$(gcloud run services describe financial-rag-frontend --region=$REGION --format="value(status.url)")

print_status "Deployment completed successfully!"
echo ""
echo "🔗 Service URLs:"
echo "  Backend: $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""
echo "📁 Cloud Storage:"
echo "  Bucket: gs://$BUCKET_NAME"
echo "  PDF Files: gs://$BUCKET_NAME/pdf-files/"
echo "  Processed Data: gs://$BUCKET_NAME/processed-data/"
echo ""
echo "🚀 Next Steps:"
echo "  1. Upload fintbx.pdf to gs://$BUCKET_NAME/pdf-files/ if not already done"
echo "  2. Run PDF processing job:"
echo "     gcloud run jobs execute pdf-processor --region=$REGION"
echo "  3. Access the frontend at: $FRONTEND_URL"
echo "  4. Test the RAG system with sample queries"
echo ""
print_warning "Note: The first PDF processing run may take 30-60 minutes for the full 3000-page document."
