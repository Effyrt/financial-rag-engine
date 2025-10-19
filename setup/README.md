# Setup Guides

This directory contains step-by-step guides for setting up the infrastructure for the Financial RAG Engine.

## 📋 Setup Order

Follow these guides in order:

1. **[01_gcp_setup.md](01_gcp_setup.md)** - Google Cloud Platform configuration
   - Create GCP project
   - Enable APIs
   - Set up service accounts
   - Create storage buckets
   - Configure billing and budgets

2. **[02_pinecone_setup.md](02_pinecone_setup.md)** - Vector database setup
   - Create Pinecone account
   - Configure index
   - Test vector operations
   - Set up metadata schema

3. **[03_composer_setup.md](03_composer_setup.md)** - Airflow orchestration
   - Create Cloud Composer environment
   - Install dependencies
   - Configure connections
   - Deploy test DAG

4. **[04_docling_test.md](04_docling_test.md)** - PDF parsing validation
   - Install Docling
   - Test PDF parsing
   - Evaluate chunking strategies
   - Generate quality report

## ⏱️ Estimated Time

- **Total time:** 4-7 hours
- **GCP Setup:** 1-2 hours
- **Pinecone Setup:** 30-45 minutes
- **Composer Setup:** 2-3 hours (includes environment creation time)
- **Docling Test:** 1-2 hours

## 💰 Cost Considerations

### Free Tier / Low Cost
- **Pinecone:** Free tier available (100K vectors)
- **GCP Storage:** ~$0.02/GB/month
- **OpenAI API:** Pay per use

### Significant Costs
- **Cloud Composer:** $150-500/month
  - Consider using local Airflow for development
  - Delete environment when not actively using
  
### Cost Optimization Tips
1. Use smaller machine types during development
2. Delete Composer environment when not in use
3. Use local Airflow for DAG development
4. Monitor spending with budget alerts

## 🔑 Required Accounts

Before starting, ensure you have:

- [ ] Google Cloud Platform account (with billing enabled)
- [ ] Pinecone account (free tier available)
- [ ] OpenAI API account (for embeddings)
- [ ] GitHub account (for version control)

## 📝 Environment Variables

After completing all setup guides, your `.env` file should contain:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Pinecone
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-central1-gcp
PINECONE_INDEX_NAME=financial-concepts

# GCP
GCP_PROJECT_ID=financial-rag-engine
GCS_BUCKET_NAME=financial-rag-engine-raw-pdfs
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Cloud Composer
COMPOSER_ENV_NAME=financial-rag-composer
COMPOSER_DAGS_BUCKET=gs://...
AIRFLOW_UI_URL=https://...

# Database
DATABASE_URL=postgresql://user:password@host:5432/finrag

# API URLs
BACKEND_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8501
```

## ✅ Verification

After completing all guides, verify:

```bash
# Check GCP authentication
gcloud auth list

# Check GCS buckets
gsutil ls

# Test Pinecone connection
python scripts/test_pinecone.py

# Check Composer environment
gcloud composer environments list

# Verify Docling installation
python -c "import docling; print('Docling installed successfully')"
```

## 🆘 Getting Help

If you encounter issues:

1. Check the **Troubleshooting** section in each guide
2. Review error messages carefully
3. Consult the **Resources** links provided
4. Check GCP/Pinecone/Airflow documentation
5. Ask team members or course instructors

## 🔄 Alternative: Local Development Setup

For cost-effective development, consider:

```bash
# Use local Airflow instead of Composer
pip install apache-airflow==2.7.0
airflow standalone

# Use local vector store for testing
pip install chromadb  # Free, local alternative to Pinecone

# Use local PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
```

## 📚 Additional Resources

- [GCP Documentation](https://cloud.google.com/docs)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Docling GitHub](https://github.com/DS4SD/docling)

## Next Steps

After completing Phase 0 (Infrastructure Setup), proceed to:
- **Phase 1:** PDF Corpus Construction (see `ROADMAP.md`)

