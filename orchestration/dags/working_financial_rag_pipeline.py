#!/usr/bin/env python3
"""
Working Financial RAG Pipeline DAG
Uses correct Vertex AI operators and Cloud Run jobs
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import os
import logging

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "financial-rag-engine")
REGION = os.environ.get("GCP_REGION", "us-central1")
BUCKET_NAME = os.environ.get("GCP_BUCKET_NAME", "financial-rag-data")

# DAG Configuration
default_args = {
    'owner': 'financial-rag-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def _start_pipeline_log():
    """Log pipeline start"""
    logging.info("🚀 Starting Working Financial RAG Pipeline")
    logging.info(f"   Project: {PROJECT_ID}")
    logging.info(f"   Region: {REGION}")
    logging.info(f"   Bucket: {BUCKET_NAME}")

def _end_pipeline_log():
    """Log pipeline completion"""
    logging.info("✅ Working Financial RAG Pipeline completed successfully")

# Removed unused function - now using real Cloud Run jobs

# Create DAG
with DAG(
    dag_id='working_financial_rag_pipeline',
    default_args=default_args,
    description='Working Financial RAG Pipeline with Vertex AI and Cloud Run',
    schedule_interval=None,  # Manual trigger
    catchup=False,
    tags=['financial', 'rag', 'vertex_ai', 'working', 'composer'],
) as dag:

    # Start pipeline
    start_pipeline = PythonOperator(
        task_id='start_pipeline_log',
        python_callable=_start_pipeline_log,
    )

    # Step 1: Parse and process PDF with Vertex AI (50 pages) - REAL CLOUD RUN JOB
    pdf_processing = BashOperator(
        task_id="pdf_processing",
        bash_command=f"""
        gcloud run jobs execute pdf-processor \
            --region={REGION} \
            --project={PROJECT_ID} \
            --args="python,fintbx_ingest_dag.py,--project-id,{PROJECT_ID},--pdf-path,gs://{BUCKET_NAME}/pdf-files/fintbx.pdf,--start-page,1,--end-page,50,--use-chromadb" \
            --wait
        """,
    )

    # Step 2: Run concept seeding - REAL CLOUD RUN JOB  
    concept_seeding = BashOperator(
        task_id="concept_seeding",
        bash_command=f"""
        gcloud run jobs execute pdf-processor \
            --region={REGION} \
            --project={PROJECT_ID} \
            --args="python,concept_seed_dag.py,--project-id,{PROJECT_ID},--mode,generate,--use-chromadb" \
            --wait
        """,
    )

    # End pipeline
    end_pipeline = PythonOperator(
        task_id='end_pipeline_log',
        python_callable=_end_pipeline_log,
    )

    # Define task dependencies (correct flow: PDF processing → Concept seeding)
    start_pipeline >> pdf_processing >> concept_seeding >> end_pipeline
