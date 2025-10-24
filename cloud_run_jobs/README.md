# Financial RAG Engine - Cloud Run Jobs

This directory contains the Cloud Run Jobs implementation for the Financial RAG Engine, providing scalable, serverless processing of PDF documents and concept seeding.

## 🏗️ Architecture

### DAGs Overview

1. **`fintbx_ingest_dag.py`** - PDF Ingestion Pipeline
   - Downloads PDF from GCS
   - Processes with Docling parser
   - Generates embeddings
   - Updates vector store (ChromaDB/Pinecone)
   - Uploads artifacts to GCS

2. **`concept_seed_dag.py`** - Concept Seeding Pipeline
   - Generates financial concepts
   - Updates existing embeddings
   - Seeds vector store with domain knowledge

### Cloud Storage Configuration

- **GCS Bucket**: `financial-rag-artifacts`
  - `data/raw/` - Source PDFs
  - `data/processed/` - Parsed data, chunks, embeddings
  - `artifacts/` - Job run artifacts and metadata
  - `concept_artifacts/` - Concept seeding artifacts

### Parameterized Schedules

| Schedule | Frequency | Description | Parameters |
|----------|-----------|-------------|------------|
| `fintbx-weekly-ingest` | Every Sunday 2 AM UTC | Weekly PDF processing | 500 pages, ChromaDB |
| `concept-daily-seed` | Daily 3 AM UTC | Concept updates | Update mode, ChromaDB |
| `monthly-full-refresh` | First Sunday 1 AM UTC | Full PDF processing | All pages, ChromaDB |

## 🚀 Quick Start

### Prerequisites

1. **GCP Project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed
4. **API Keys** for OpenAI and Pinecone (if using)

### 1. Deploy Jobs

```bash
# Set environment variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export BUCKET_NAME="financial-rag-artifacts"

# Make deployment script executable
chmod +x cloud_run_jobs/deploy_jobs.sh

# Deploy everything
./cloud_run_jobs/deploy_jobs.sh
```

### 2. Configure Secrets

```bash
# Create secrets file
cat > secrets.json << EOF
{
  "OPENAI_API_KEY": "your_openai_api_key_here",
  "PINECONE_API_KEY": "your_pinecone_api_key_here",
  "PINECONE_ENVIRONMENT": "your_pinecone_environment_here"
}
EOF

# Upload to Secret Manager
gcloud secrets create financial-rag-secrets --data-file=secrets.json
```

### 3. Upload PDF

```bash
# Upload your PDF to GCS
gsutil cp fintbx.pdf gs://financial-rag-artifacts/data/raw/
```

### 4. Test Jobs

```bash
# Test PDF ingestion (10 pages)
gcloud run jobs execute fintbx-ingest \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--pages=10,--use-chromadb" \
  --wait

# Test concept seeding
gcloud run jobs execute concept-seed \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--mode=generate,--use-chromadb" \
  --wait
```

## 📋 Job Parameters

### Fintbx Ingest DAG

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--project-id` | string | required | GCP Project ID |
| `--pdf-path` | string | `data/raw/fintbx.pdf` | PDF path in GCS |
| `--pages` | int | null | Number of pages to process |
| `--start-page` | int | null | Start page for range |
| `--end-page` | int | null | End page for range |
| `--use-chromadb` | flag | false | Use ChromaDB instead of Pinecone |
| `--region` | string | `us-central1` | GCP Region |
| `--bucket` | string | `financial-rag-artifacts` | GCS Bucket name |

### Concept Seed DAG

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--project-id` | string | required | GCP Project ID |
| `--mode` | string | `generate` | `generate` or `update` |
| `--concept-file-path` | string | null | Path to concept file (update mode) |
| `--use-chromadb` | flag | false | Use ChromaDB instead of Pinecone |
| `--region` | string | `us-central1` | GCP Region |
| `--bucket` | string | `financial-rag-artifacts` | GCS Bucket name |

## 🔧 Manual Execution

### Run PDF Ingestion

```bash
# Process specific page range
gcloud run jobs execute fintbx-ingest \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--start-page=1,--end-page=100,--use-chromadb" \
  --wait

# Process all pages
gcloud run jobs execute fintbx-ingest \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--use-chromadb" \
  --wait
```

### Run Concept Seeding

```bash
# Generate new concepts
gcloud run jobs execute concept-seed \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--mode=generate,--use-chromadb" \
  --wait

# Update existing concepts
gcloud run jobs execute concept-seed \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--mode=update,--concept-file-path=concept_artifacts/latest/concepts.json,--use-chromadb" \
  --wait
```

## 📊 Monitoring

### View Job Logs

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_job" --limit=50

# View specific job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=fintbx-ingest" --limit=20
```

### Check Job Status

```bash
# List jobs
gcloud run jobs list --region=us-central1

# Get job details
gcloud run jobs describe fintbx-ingest --region=us-central1

# List executions
gcloud run jobs executions list --job=fintbx-ingest --region=us-central1
```

### Monitor Artifacts

```bash
# List artifacts in GCS
gsutil ls gs://financial-rag-artifacts/artifacts/

# Download latest artifacts
gsutil -m cp -r gs://financial-rag-artifacts/artifacts/latest/ ./artifacts/
```

## 🔄 Scheduling

### View Schedules

```bash
# List all schedules
gcloud scheduler jobs list

# Get schedule details
gcloud scheduler jobs describe fintbx-weekly-ingest
```

### Modify Schedules

```bash
# Update schedule frequency
gcloud scheduler jobs update fintbx-weekly-ingest \
  --schedule="0 1 * * 0"  # Change to 1 AM UTC

# Pause a schedule
gcloud scheduler jobs pause fintbx-weekly-ingest

# Resume a schedule
gcloud scheduler jobs resume fintbx-weekly-ingest
```

## 🛠️ Troubleshooting

### Common Issues

1. **Job Timeout**
   - Increase `--task-timeout` in deployment
   - Process smaller page ranges

2. **Memory Issues**
   - Increase `--memory` allocation
   - Use `--pages` to limit processing

3. **Permission Errors**
   - Check service account permissions
   - Verify Secret Manager access

4. **ChromaDB Issues**
   - Ensure ChromaDB is installed
   - Check collection name conflicts

### Debug Mode

```bash
# Run with debug logging
gcloud run jobs execute fintbx-ingest \
  --region=us-central1 \
  --args="--project-id=$PROJECT_ID,--pages=5,--use-chromadb" \
  --set-env-vars="LOG_LEVEL=DEBUG" \
  --wait
```

## 📈 Performance Tuning

### Resource Allocation

| Job Type | Memory | CPU | Timeout | Parallelism |
|----------|--------|-----|---------|-------------|
| PDF Ingest | 4Gi | 2 | 3600s | 1 |
| Concept Seed | 2Gi | 1 | 1800s | 1 |

### Batch Processing

- **Small batches**: 50-100 pages for testing
- **Medium batches**: 200-500 pages for regular updates
- **Large batches**: 1000+ pages for full processing

### Cost Optimization

- Use ChromaDB for unlimited namespaces
- Process during off-peak hours
- Use preemptible instances for non-critical jobs
- Implement incremental updates

## 🔐 Security

### Service Account Permissions

- `roles/storage.admin` - GCS access
- `roles/secretmanager.secretAccessor` - Secret access
- `roles/run.invoker` - Job execution

### Secret Management

- Store API keys in Secret Manager
- Use least-privilege access
- Rotate keys regularly
- Monitor access logs

## 📚 Additional Resources

- [Cloud Run Jobs Documentation](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [ChromaDB Documentation](https://docs.trychroma.com/)
