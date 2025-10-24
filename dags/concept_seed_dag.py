from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from google.cloud import storage
import json

BUCKET_NAME = "financial-rag-artifacts"

def upload_concept_seed():
    """upload seed JSON to GCS bucket's seeds/ file"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    seed_data = {
        "concepts": [
            "Revenue",
            "Operating Income",
            "EPS (Earnings Per Share)",
            "Dividend",
            "Cash Flow",
            "Operating Margin",
            "Net Income"
        ],
        "version": "v1.0",
        "source": "financial-rag-lab2"
    }

    blob = bucket.blob("seeds/concept_seed_v1.json")
    blob.upload_from_string(json.dumps(seed_data, indent=2))
    print("✅ Uploaded concept_seed_v1.json to GCS 'seeds/' folder")

with DAG(
    dag_id="concept_seed_dag",
    description="Upload concept seed JSON to GCS",
    start_date=datetime(2025, 10, 1),
    schedule_interval=None,  
    catchup=False,
) as dag:

    seed_task = PythonOperator(
        task_id="upload_concept_seed",
        python_callable=upload_concept_seed,
    )
