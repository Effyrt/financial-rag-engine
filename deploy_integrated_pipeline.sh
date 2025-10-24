#!/bin/bash

# Integrated Financial RAG Pipeline Deployment Script
# Deploys existing DAGs with Vertex AI parsing integration

# Configuration
PROJECT_ID="financial-rag-engine"
REGION="us-central1"
COMPOSER_ENV_NAME="financial-rag-composer"
SERVICE_ACCOUNT="773470655851-compute@developer.gserviceaccount.com" # Replace with your actual service account

# --- Helper Functions ---
print_status() {
    echo -e "\n\033[1;34mSTATUS: $1\033[0m"
}

print_success() {
    echo -e "\n\033[1;32mSUCCESS: $1\033[0m"
}

print_error() {
    echo -e "\n\033[1;31mERROR: $1\033[0m"
    exit 1
}

# --- 1. Enable Required APIs ---
print_status "Enabling required Google Cloud APIs..."
gcloud services enable \
    composer.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    containerregistry.googleapis.com \
    aiplatform.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID || print_error "Failed to enable APIs."
print_success "All required APIs enabled."

# --- 2. Create Cloud Composer Environment ---
print_status "Creating Cloud Composer environment (this may take 20-30 minutes)..."
gcloud composer environments create $COMPOSER_ENV_NAME \
    --location $REGION \
    --image-version composer-2.14.4-airflow-2.9.3 \
    --service-account $SERVICE_ACCOUNT \
    --project=$PROJECT_ID || print_error "Failed to create Composer environment."
print_success "Cloud Composer environment created."

# --- 3. Build and Deploy Vertex AI Parsing Service ---
print_status "Building Vertex AI parsing service Docker image..."
cd vertex_ai || print_error "Failed to change to vertex_ai directory."
gcloud builds submit --tag gcr.io/$PROJECT_ID/vertex-ai-parser:latest . \
    --project=$PROJECT_ID || print_error "Failed to build Vertex AI parser image."
print_success "Vertex AI parsing service image built."
cd ..

# --- 4. Build and Deploy PDF Processor (with existing DAGs) ---
print_status "Building PDF processor with existing DAGs..."
cd cloud_run_jobs || print_error "Failed to change to cloud_run_jobs directory."
gcloud builds submit --tag gcr.io/$PROJECT_ID/pdf-processor:latest . \
    --project=$PROJECT_ID || print_error "Failed to build PDF processor image."
print_success "PDF processor image built."
cd ..

# --- 5. Build and Deploy Gradio Frontend ---
print_status "Building Gradio frontend Docker image..."
cd frontend || print_error "Failed to change to frontend directory."
gcloud builds submit --tag gcr.io/$PROJECT_ID/gradio-frontend:latest . \
    --project=$PROJECT_ID || print_error "Failed to build Gradio frontend image."
print_success "Gradio frontend image built."

print_status "Deploying Gradio frontend to Cloud Run..."
gcloud run deploy gradio-frontend \
    --image gcr.io/$PROJECT_ID/gradio-frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --cpu 2 \
    --memory 4Gi \
    --set-env-vars="BACKEND_URL=http://fastapi-backend.svc.default.run.app" \
    --project=$PROJECT_ID || print_error "Failed to deploy Gradio frontend."
print_success "Gradio frontend deployed."
cd ..

# --- 6. Build and Deploy FastAPI Backend ---
print_status "Building FastAPI backend Docker image..."
cd backend || print_error "Failed to change to backend directory."
gcloud builds submit --tag gcr.io/$PROJECT_ID/fastapi-backend:latest . \
    --project=$PROJECT_ID || print_error "Failed to build FastAPI backend image."
print_success "FastAPI backend image built."

print_status "Deploying FastAPI backend to Cloud Run..."
gcloud run deploy fastapi-backend \
    --image gcr.io/$PROJECT_ID/fastapi-backend:latest \
    --platform managed \
    --region $REGION \
    --no-allow-unauthenticated \
    --cpu 2 \
    --memory 4Gi \
    --project=$PROJECT_ID || print_error "Failed to deploy FastAPI backend."
print_success "FastAPI backend deployed."
cd ..

# --- 7. Upload Airflow DAGs to Composer Bucket ---
print_status "Uploading Airflow DAGs to Composer bucket..."
COMPOSER_BUCKET=$(gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $REGION \
    --project=$PROJECT_ID \
    --format="value(config.dagGcsPrefix)") || print_error "Failed to get Composer bucket."

# Upload new orchestration DAGs
gsutil cp orchestration/dags/*.py $COMPOSER_BUCKET/dags/ || print_error "Failed to upload orchestration DAGs."

# Upload existing DAGs (as reference/backup)
gsutil cp cloud_run_jobs/fintbx_ingest_dag.py $COMPOSER_BUCKET/dags/ || print_error "Failed to upload fintbx_ingest_dag.py."
gsutil cp cloud_run_jobs/concept_seed_dag.py $COMPOSER_BUCKET/dags/ || print_error "Failed to upload concept_seed_dag.py."

print_success "All DAGs uploaded to Composer bucket."

# --- 8. Create Cloud Run Jobs for existing DAGs ---
print_status "Creating Cloud Run jobs for existing DAGs..."

# Create concept seeding job
gcloud run jobs create concept-seed-dag \
    --image gcr.io/$PROJECT_ID/pdf-processor:latest \
    --region $REGION \
    --args="python,concept_seed_dag.py,--project-id,$PROJECT_ID,--mode,generate,--use-chromadb" \
    --set-env-vars="OPENAI_API_KEY=$$(gcloud secrets versions access latest --secret=financial-rag-secrets --project=$PROJECT_ID | jq -r '.OPENAI_API_KEY')" \
    --project=$PROJECT_ID || print_error "Failed to create concept seeding job."

# Create PDF ingestion job
gcloud run jobs create fintbx-ingest-dag \
    --image gcr.io/$PROJECT_ID/pdf-processor:latest \
    --region $REGION \
    --args="python,fintbx_ingest_dag.py,--project-id,$PROJECT_ID,--pdf-path,gs://financial-rag-data/pdf-files/fintbx.pdf,--start-page,1,--end-page,50,--use-chromadb" \
    --set-env-vars="OPENAI_API_KEY=$$(gcloud secrets versions access latest --secret=financial-rag-secrets --project=$PROJECT_ID | jq -r '.OPENAI_API_KEY')" \
    --project=$PROJECT_ID || print_error "Failed to create PDF ingestion job."

print_success "Cloud Run jobs created for existing DAGs."

print_status "🎉 Integrated Financial RAG Pipeline Deployment Complete!"
echo ""
echo "📊 Deployment Summary:"
echo "   ✅ Cloud Composer Environment: $COMPOSER_ENV_NAME"
echo "   ✅ Vertex AI Parser: gcr.io/$PROJECT_ID/vertex-ai-parser:latest"
echo "   ✅ PDF Processor: gcr.io/$PROJECT_ID/pdf-processor:latest"
echo "   ✅ Gradio Frontend: Deployed to Cloud Run"
echo "   ✅ FastAPI Backend: Deployed to Cloud Run"
echo "   ✅ DAGs: Uploaded to Composer bucket"
echo "   ✅ Cloud Run Jobs: Created for existing DAGs"
echo ""
echo "🔗 Access Points:"
echo "   Cloud Composer: https://console.cloud.google.com/composer/environments/$REGION/$COMPOSER_ENV_NAME?project=$PROJECT_ID"
echo "   Cloud Run Services: https://console.cloud.google.com/run/services?project=$PROJECT_ID"
echo "   Vertex AI Custom Jobs: https://console.cloud.google.com/vertex-ai/custom-jobs?project=$PROJECT_ID"
echo "   Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
echo ""
echo "🚀 Next Steps:"
echo "   1. Go to Cloud Composer UI and trigger the 'financial_rag_orchestration' DAG"
echo "   2. Monitor the pipeline execution"
echo "   3. Check Vertex AI custom jobs for parsing progress"
echo "   4. Access Gradio frontend when ready"
