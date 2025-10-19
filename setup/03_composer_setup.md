# Phase 0.3: Cloud Composer (Airflow) Setup

**Duration:** 2-3 hours  
**Prerequisites:** GCP project configured, service account created

---

## Overview

Set up Google Cloud Composer (managed Apache Airflow) for orchestrating the RAG pipeline.

## Tasks

### 1. Create Cloud Composer Environment

```bash
# Set variables
export PROJECT_ID="financial-rag-engine"
export COMPOSER_ENV_NAME="financial-rag-composer"
export GCP_REGION="us-central1"
export COMPOSER_ZONE="us-central1-a"

# Create Composer environment (this takes 20-30 minutes)
gcloud composer environments create $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --zone $COMPOSER_ZONE \
    --machine-type n1-standard-4 \
    --node-count 3 \
    --python-version 3.10 \
    --disk-size 30 \
    --service-account financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Note: This is expensive! Consider using smaller machine types for development
# For dev: --machine-type n1-standard-1 --node-count 1
```

### 2. Get Composer Environment Details

```bash
# Get environment details
gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $GCP_REGION

# Get Airflow web UI URL
gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --format="get(config.airflowUri)"

# Get DAGs bucket
export DAGS_BUCKET=$(gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --format="get(config.dagGcsPrefix)")

echo "DAGs Bucket: $DAGS_BUCKET"

# Add to .env
cat >> .env << EOF
COMPOSER_ENV_NAME=$COMPOSER_ENV_NAME
COMPOSER_DAGS_BUCKET=$DAGS_BUCKET
AIRFLOW_UI_URL=$(gcloud composer environments describe $COMPOSER_ENV_NAME --location $GCP_REGION --format="get(config.airflowUri)")
EOF
```

### 3. Install Python Dependencies

```bash
# Upload requirements file to Composer
gcloud composer environments update $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --update-pypi-packages-from-file airflow/config/composer_requirements.txt
```

### 4. Set Environment Variables in Composer

```bash
# Set Airflow variables
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    variables set -- \
    gcp_project_id $PROJECT_ID

gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    variables set -- \
    gcs_raw_bucket ${PROJECT_ID}-raw-pdfs

gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    variables set -- \
    gcs_processed_bucket ${PROJECT_ID}-processed

# Set Airflow connections (add your API keys)
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    connections add openai_default -- \
    --conn-type http \
    --conn-host https://api.openai.com \
    --conn-password YOUR_OPENAI_API_KEY

gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    connections add pinecone_default -- \
    --conn-type http \
    --conn-host https://api.pinecone.io \
    --conn-password YOUR_PINECONE_API_KEY
```

### 5. Create Test DAG

Create a simple test DAG to verify setup:

```python
# airflow/dags/test_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'financial-rag-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def print_hello():
    print("Hello from Financial RAG Engine!")
    print("Composer setup is working!")
    return "success"

with DAG(
    'test_dag',
    default_args=default_args,
    description='Test DAG to verify Composer setup',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['test'],
) as dag:

    start = BashOperator(
        task_id='start',
        bash_command='echo "Starting test DAG"',
    )

    test_python = PythonOperator(
        task_id='test_python',
        python_callable=print_hello,
    )

    test_env = BashOperator(
        task_id='test_environment',
        bash_command='python --version && pip list | grep -E "(openai|pinecone|langchain)"',
    )

    end = BashOperator(
        task_id='end',
        bash_command='echo "Test DAG completed successfully!"',
    )

    start >> test_python >> test_env >> end
```

### 6. Upload Test DAG

```bash
# Upload DAG to Composer
gsutil cp airflow/dags/test_dag.py $DAGS_BUCKET/dags/

# Wait a few minutes for Airflow to pick up the DAG
sleep 120

# List DAGs
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    dags list
```

### 7. Trigger Test DAG

```bash
# Trigger the test DAG
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    dags trigger -- test_dag

# Check DAG status
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    dags list-runs -- --dag-id test_dag
```

### 8. Access Airflow Web UI

```bash
# Get Airflow UI URL
AIRFLOW_URL=$(gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --format="get(config.airflowUri)")

echo "Airflow UI: $AIRFLOW_URL"

# Open in browser (macOS)
open $AIRFLOW_URL

# Or copy URL and paste in browser
```

### 9. Configure Airflow Settings

```bash
# Set Airflow configurations
gcloud composer environments update $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --update-airflow-configs \
        core-dags_are_paused_at_creation=False,\
        core-load_examples=False,\
        webserver-expose_config=True,\
        scheduler-catchup_by_default=False
```

### 10. Set Up Logging

```bash
# Logs are automatically sent to Cloud Logging
# View logs
gcloud logging read "resource.type=cloud_composer_environment AND resource.labels.environment_name=$COMPOSER_ENV_NAME" \
    --limit 50 \
    --format json
```

## Verification Checklist

- [ ] Composer environment created successfully
- [ ] Environment is in RUNNING state
- [ ] Python dependencies installed
- [ ] Environment variables set
- [ ] Airflow connections configured
- [ ] Test DAG uploaded
- [ ] Test DAG runs successfully
- [ ] Can access Airflow web UI
- [ ] Logs visible in Cloud Logging

## Composer Environment Details

```yaml
Name: financial-rag-composer
Location: us-central1
Machine Type: n1-standard-4 (or n1-standard-1 for dev)
Node Count: 3 (or 1 for dev)
Python Version: 3.10
Disk Size: 30 GB
Service Account: financial-rag-sa
```

## Troubleshooting

### Issue: Environment creation takes too long
- Normal creation time: 20-30 minutes
- Check status: `gcloud composer environments list --locations=$GCP_REGION`
- View creation logs in Cloud Logging

### Issue: DAG not appearing
```bash
# Check if DAG file is in correct location
gsutil ls $DAGS_BUCKET/dags/

# Check DAG parsing errors
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    dags list-import-errors
```

### Issue: Dependencies not installing
```bash
# Check PyPI package installation status
gcloud composer environments describe $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --format="get(config.softwareConfig.pypiPackages)"

# Reinstall specific package
gcloud composer environments update $COMPOSER_ENV_NAME \
    --location $GCP_REGION \
    --update-pypi-package package-name==version
```

### Issue: Permission errors
```bash
# Grant service account necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:financial-rag-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/composer.worker"
```

## Cost Estimates

**Cloud Composer Costs (EXPENSIVE!):**
- Small environment (n1-standard-1, 1 node): ~$150-200/month
- Medium environment (n1-standard-4, 3 nodes): ~$400-500/month

**Cost Optimization Tips:**
1. Use smaller machine types for development
2. Reduce node count to 1 for testing
3. Delete environment when not in use
4. Consider using local Airflow for development

**Alternative for Development:**
```bash
# Run Airflow locally instead
pip install apache-airflow==2.7.0
airflow standalone
```

## Development Workflow

1. **Develop DAGs locally** in `airflow/dags/`
2. **Test locally** with Airflow standalone
3. **Upload to Composer** when ready:
   ```bash
   gsutil cp airflow/dags/*.py $DAGS_BUCKET/dags/
   ```
4. **Monitor in Airflow UI**

## Common Airflow CLI Commands

```bash
# List all DAGs
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION dags list

# Trigger a DAG
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION dags trigger -- DAG_ID

# Pause a DAG
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION dags pause -- DAG_ID

# Unpause a DAG
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION dags unpause -- DAG_ID

# View DAG runs
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION dags list-runs -- --dag-id DAG_ID

# View task logs
gcloud composer environments run $COMPOSER_ENV_NAME \
    --location $GCP_REGION tasks logs -- DAG_ID TASK_ID RUN_ID
```

## Next Steps

Proceed to `04_docling_test.md` to test PDF parsing with Docling.

## Resources

- [Cloud Composer Documentation](https://cloud.google.com/composer/docs)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Composer Best Practices](https://cloud.google.com/composer/docs/best-practices)
- [Airflow DAG Writing Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

