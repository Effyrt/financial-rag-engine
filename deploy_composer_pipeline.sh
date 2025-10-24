#!/bin/bash

# Deploy Financial RAG Engine with Cloud Composer
# This script sets up the complete pipeline with orchestration

set -e

# Configuration
PROJECT_ID="financial-rag-engine"
REGION="us-central1"
COMPOSER_ENV="financial-rag-composer"
BUCKET_NAME="financial-rag-data"

echo "🚀 Deploying Financial RAG Engine with Cloud Composer..."

# Function to print status
print_status() {
    echo "✅ $1"
}

print_warning() {
    echo "⚠️  $1"
}

print_error() {
    echo "❌ $1"
}

# Step 1: Enable required APIs
print_status "Enabling required APIs..."
gcloud services enable composer.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable vertex.googleapis.com

# Step 2: Create Cloud Composer environment
print_status "Creating Cloud Composer environment..."
if gcloud composer environments describe $COMPOSER_ENV --location=$REGION &>/dev/null; then
    print_warning "Composer environment already exists"
else
    gcloud composer environments create $COMPOSER_ENV \
        --location=$REGION \
        --python-version=3 \
        --node-count=3
    print_status "Composer environment created"
fi

# Step 3: Build Vertex AI parsing image
print_status "Building Vertex AI parsing image..."
cd vertex_ai
gcloud builds submit --tag gcr.io/$PROJECT_ID/vertex-ai-parser:latest .
cd ..

# Step 4: Deploy DAGs to Composer
print_status "Deploying DAGs to Composer..."
COMPOSER_BUCKET=$(gcloud composer environments describe $COMPOSER_ENV --location=$REGION --format="value(config.dagGcsPrefix)")
COMPOSER_BUCKET=${COMPOSER_BUCKET%/*}

# Copy DAGs to Composer bucket
gsutil cp orchestration/dags/*.py $COMPOSER_BUCKET/dags/
print_status "DAGs deployed to Composer"

# Step 5: Deploy Gradio frontend
print_status "Deploying Gradio frontend..."
cd frontend
gcloud builds submit --tag gcr.io/$PROJECT_ID/gradio-frontend:latest .
gcloud run deploy gradio-frontend \
    --image gcr.io/$PROJECT_ID/gradio-frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 7860 \
    --memory 2Gi \
    --cpu 2
cd ..

# Step 6: Deploy FastAPI backend
print_status "Deploying FastAPI backend..."
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/fastapi-backend:latest .
gcloud run deploy fastapi-backend \
    --image gcr.io/$PROJECT_ID/fastapi-backend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8000 \
    --memory 4Gi \
    --cpu 2 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME"
cd ..

# Step 7: Set up Composer variables
print_status "Setting up Composer variables..."
gcloud composer environments run $COMPOSER_ENV --location=$REGION variables set -- project_id $PROJECT_ID
gcloud composer environments run $COMPOSER_ENV --location=$REGION variables set -- bucket_name $BUCKET_NAME
gcloud composer environments run $COMPOSER_ENV --location=$REGION variables set -- region $REGION

print_status "🎉 Deployment completed successfully!"

echo ""
echo "📋 Next Steps:"
echo "1. Upload a PDF to: gs://$BUCKET_NAME/pdf-files/"
echo "2. Trigger the pipeline in Composer UI"
echo "3. Access Gradio frontend at the provided URL"
echo "4. Start chatting with your documents!"

echo ""
echo "🔗 Useful Links:"
echo "- Composer UI: https://console.cloud.google.com/composer/environments"
echo "- Cloud Run: https://console.cloud.google.com/run"
echo "- Cloud Storage: https://console.cloud.google.com/storage"

print_status "Deployment script completed!"
