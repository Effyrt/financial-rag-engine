#!/bin/bash
# Deploy Cloud Run Jobs for Financial RAG Engine

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
BUCKET_NAME="${BUCKET_NAME:-financial-rag-artifacts}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Financial RAG Engine Cloud Run Jobs${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Bucket: $BUCKET_NAME"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command_exists gcloud; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Set project
echo -e "${YELLOW}🔧 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔌 Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudscheduler.googleapis.com

# Create GCS bucket if it doesn't exist
echo -e "${YELLOW}🪣 Creating GCS bucket...${NC}"
if ! gsutil ls -b gs://$BUCKET_NAME >/dev/null 2>&1; then
    gsutil mb -l $REGION gs://$BUCKET_NAME
    echo -e "${GREEN}✅ Created bucket: gs://$BUCKET_NAME${NC}"
else
    echo -e "${GREEN}✅ Bucket already exists: gs://$BUCKET_NAME${NC}"
fi

# Create service account if it doesn't exist
echo -e "${YELLOW}👤 Creating service account...${NC}"
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT >/dev/null 2>&1; then
    gcloud iam service-accounts create financial-rag-sa \
        --display-name="Financial RAG Service Account" \
        --description="Service account for Financial RAG Engine Cloud Run Jobs"
    echo -e "${GREEN}✅ Created service account: $SERVICE_ACCOUNT${NC}"
else
    echo -e "${GREEN}✅ Service account already exists: $SERVICE_ACCOUNT${NC}"
fi

# Grant necessary permissions
echo -e "${YELLOW}🔐 Granting permissions...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker"

echo -e "${GREEN}✅ Permissions granted${NC}"

# Build and push Docker images
echo -e "${YELLOW}🐳 Building Docker images...${NC}"

# Build fintbx-ingest image
echo "Building fintbx-ingest image..."
docker build -t gcr.io/$PROJECT_ID/fintbx-ingest:latest \
    -f cloud_run_jobs/Dockerfile.ingest \
    .

docker push gcr.io/$PROJECT_ID/fintbx-ingest:latest

# Build concept-seed image
echo "Building concept-seed image..."
docker build -t gcr.io/$PROJECT_ID/concept-seed:latest \
    -f cloud_run_jobs/Dockerfile.concept \
    .

docker push gcr.io/$PROJECT_ID/concept-seed:latest

echo -e "${GREEN}✅ Docker images built and pushed${NC}"

# Deploy Cloud Run Jobs
echo -e "${YELLOW}🚀 Deploying Cloud Run Jobs...${NC}"

# Deploy fintbx-ingest job
echo "Deploying fintbx-ingest job..."
gcloud run jobs create fintbx-ingest \
    --image=gcr.io/$PROJECT_ID/fintbx-ingest:latest \
    --region=$REGION \
    --service-account=$SERVICE_ACCOUNT \
    --memory=4Gi \
    --cpu=2 \
    --max-retries=3 \
    --parallelism=1 \
    --task-count=1 \
    --task-timeout=3600 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME"

# Deploy concept-seed job
echo "Deploying concept-seed job..."
gcloud run jobs create concept-seed \
    --image=gcr.io/$PROJECT_ID/concept-seed:latest \
    --region=$REGION \
    --service-account=$SERVICE_ACCOUNT \
    --memory=2Gi \
    --cpu=1 \
    --max-retries=3 \
    --parallelism=1 \
    --task-count=1 \
    --task-timeout=1800 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME"

echo -e "${GREEN}✅ Cloud Run Jobs deployed${NC}"

# Create Cloud Scheduler jobs
echo -e "${YELLOW}⏰ Creating Cloud Scheduler jobs...${NC}"

# Weekly PDF ingestion
gcloud scheduler jobs create http fintbx-weekly-ingest \
    --schedule="0 2 * * 0" \
    --time-zone="UTC" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/fintbx-ingest:run" \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --headers="Content-Type=application/json" \
    --message-body='{"overrides":{"spec":{"template":{"spec":{"containers":[{"env":[{"name":"PAGES","value":"500"}]}]}}}}}'

# Daily concept seeding
gcloud scheduler jobs create http concept-daily-seed \
    --schedule="0 3 * * *" \
    --time-zone="UTC" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/concept-seed:run" \
    --http-method=POST \
    --oauth-service-account-email=$SERVICE_ACCOUNT \
    --headers="Content-Type=application/json" \
    --message-body='{"overrides":{"spec":{"template":{"spec":{"containers":[{"env":[{"name":"MODE","value":"update"}]}]}}}}}'

echo -e "${GREEN}✅ Cloud Scheduler jobs created${NC}"

# Create secrets in Secret Manager
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"

# Create secrets file template
cat > secrets_template.json << EOF
{
  "OPENAI_API_KEY": "your_openai_api_key_here",
  "PINECONE_API_KEY": "your_pinecone_api_key_here",
  "PINECONE_ENVIRONMENT": "your_pinecone_environment_here"
}
EOF

echo -e "${YELLOW}⚠️  Please update secrets_template.json with your actual API keys${NC}"
echo -e "${YELLOW}   Then run: gcloud secrets create financial-rag-secrets --data-file=secrets_template.json${NC}"

# Test jobs
echo -e "${YELLOW}🧪 Testing jobs...${NC}"

# Test fintbx-ingest job
echo "Testing fintbx-ingest job..."
gcloud run jobs execute fintbx-ingest \
    --region=$REGION \
    --args="--project-id=$PROJECT_ID,--pages=10,--use-chromadb" \
    --wait

# Test concept-seed job
echo "Testing concept-seed job..."
gcloud run jobs execute concept-seed \
    --region=$REGION \
    --args="--project-id=$PROJECT_ID,--mode=generate,--use-chromadb" \
    --wait

echo -e "${GREEN}✅ Jobs tested successfully${NC}"

# Summary
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "  • Project ID: $PROJECT_ID"
echo "  • Region: $REGION"
echo "  • Bucket: gs://$BUCKET_NAME"
echo "  • Service Account: $SERVICE_ACCOUNT"
echo ""
echo -e "${BLUE}🚀 Deployed Jobs:${NC}"
echo "  • fintbx-ingest: PDF processing and vector store update"
echo "  • concept-seed: Financial concept seeding"
echo ""
echo -e "${BLUE}⏰ Scheduled Jobs:${NC}"
echo "  • fintbx-weekly-ingest: Every Sunday at 2 AM UTC"
echo "  • concept-daily-seed: Every day at 3 AM UTC"
echo ""
echo -e "${BLUE}🔧 Next Steps:${NC}"
echo "  1. Update secrets in Secret Manager"
echo "  2. Upload your PDF to gs://$BUCKET_NAME/data/raw/"
echo "  3. Test the jobs manually"
echo "  4. Monitor job execution in Cloud Console"
echo ""
echo -e "${GREEN}✅ All done!${NC}"
