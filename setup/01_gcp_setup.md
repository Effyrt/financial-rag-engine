# Phase 0.1: Google Cloud Platform Setup

**Duration:** 1-2 hours  
**Prerequisites:** Google account, Credit card for GCP billing

---

## Overview

Set up Google Cloud Platform infrastructure for the Financial RAG Engine project.

## Tasks

### 1. Create GCP Project

```bash
# Set project variables
export PROJECT_ID="financial-rag-engine"
export PROJECT_NAME="Financial RAG Engine"
export BILLING_ACCOUNT_ID="your-billing-account-id"

# Create project
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"

# Link billing account
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID

# Set as default project
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable all necessary APIs
gcloud services enable \
    composer.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    compute.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create financial-rag-sa \
    --display-name="Financial RAG Service Account" \
    --description="Service account for Financial RAG Engine"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/composer.worker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Create and download key
gcloud iam service-accounts keys create ~/financial-rag-sa-key.json \
    --iam-account=financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### 4. Create Cloud Storage Buckets

```bash
# Set region
export GCP_REGION="us-central1"

# Create buckets
gsutil mb -l $GCP_REGION gs://${PROJECT_ID}-raw-pdfs
gsutil mb -l $GCP_REGION gs://${PROJECT_ID}-processed
gsutil mb -l $GCP_REGION gs://${PROJECT_ID}-airflow-dags

# Set bucket lifecycle (optional - delete old files after 90 days)
cat > lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://${PROJECT_ID}-processed
```

### 5. Set Up Budget Alerts

```bash
# Create budget alert (adjust amount as needed)
gcloud billing budgets create \
    --billing-account=$BILLING_ACCOUNT_ID \
    --display-name="Financial RAG Budget" \
    --budget-amount=100USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

### 6. Configure Local Environment

```bash
# Add to your .env file
cat >> .env << EOF
GCP_PROJECT_ID=$PROJECT_ID
GCS_BUCKET_NAME=${PROJECT_ID}-raw-pdfs
GCP_REGION=$GCP_REGION
GOOGLE_APPLICATION_CREDENTIALS=$HOME/financial-rag-sa-key.json
EOF

# Set environment variable for current session
export GOOGLE_APPLICATION_CREDENTIALS=$HOME/financial-rag-sa-key.json
```

### 7. Verify Setup

```bash
# Test authentication
gcloud auth application-default login

# Verify project access
gcloud projects describe $PROJECT_ID

# List enabled services
gcloud services list --enabled

# List buckets
gsutil ls

# Test bucket access
echo "test" > test.txt
gsutil cp test.txt gs://${PROJECT_ID}-raw-pdfs/
gsutil rm gs://${PROJECT_ID}-raw-pdfs/test.txt
rm test.txt
```

## Verification Checklist

- [ ] GCP project created and billing enabled
- [ ] All required APIs enabled
- [ ] Service account created with proper roles
- [ ] Service account key downloaded
- [ ] Three GCS buckets created (raw-pdfs, processed, airflow-dags)
- [ ] Budget alerts configured
- [ ] Local environment configured with credentials
- [ ] Can authenticate and access GCP resources

## Troubleshooting

### Issue: Billing not enabled
```bash
# Check billing status
gcloud beta billing projects describe $PROJECT_ID

# Link billing account
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID
```

### Issue: Permission denied errors
```bash
# Check current account
gcloud auth list

# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### Issue: API not enabled
```bash
# Check enabled APIs
gcloud services list --enabled

# Enable specific API
gcloud services enable <api-name>.googleapis.com
```

## Cost Estimates

- **Cloud Storage:** ~$0.02/GB/month
- **Cloud Composer:** ~$300-500/month (we'll set this up next)
- **Cloud Run:** Pay per use, ~$0.40/million requests
- **Cloud SQL:** ~$10-50/month depending on instance size

**Total estimated monthly cost:** $350-600 (can be optimized)

## Next Steps

Proceed to `02_pinecone_setup.md` to configure the vector database.

## Resources

- [GCP Free Tier](https://cloud.google.com/free)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)

