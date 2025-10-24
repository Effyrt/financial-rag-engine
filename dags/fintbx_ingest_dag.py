from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from google.cloud import storage

BUCKET_NAME = "financial-rag-artifacts"

def list_pdfs_in_gcs():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    blobs = bucket.list_blobs(prefix="raw/")
    print("📂 Files currently in GCS 'raw/' folder:")
    found = False
    for blob in blobs:
        print(f" - {blob.name}")
        found = True
    if not found:
        print("⚠️ No files found in 'raw/' folder.")

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fintbx_ingest_dag",
    default_args=default_args,
    description="List PDF files already uploaded to GCS bucket",
    start_date=datetime(2025, 10, 1),
    schedule_interval="@weekly",  
    catchup=False,
) as dag:

    list_task = PythonOperator(
        task_id="list_existing_pdfs",
        python_callable=list_pdfs_in_gcs,
    )
