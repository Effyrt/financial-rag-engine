"""
Airflow DAG for Concept Database Seeding - ENTERPRISE VERSION
Batch generates and caches concept notes for predefined financial concepts.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from datetime import datetime, timedelta
from loguru import logger
import sys
import os
import json

# Add src to path
sys.path.insert(0, '/opt/airflow/dags/repo/src')

from embeddings.embedding_service import EmbeddingService
from vectordb.pinecone_client import PineconeVectorDB
from vectordb.chromadb_client import ChromaVectorDB
from retrieval.rag_retriever import RAGRetriever
from retrieval.wikipedia_fallback import WikipediaFallback
from concept_generator.concept_note_generator import ConceptNoteGenerator
from concept_generator.instructor_models import ConceptNoteRequest
from database.postgres_client import PostgresClient
from database.models import ConceptSeedJob, SourceType

# ===== DAG Configuration =====
default_args = {
    'owner': 'aurelia',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

GCS_BUCKET = os.getenv('GCP_BUCKET_NAME', 'aurelia-artifacts')
CONCEPTS_LIST_PATH = 'config/financial_concepts.json'
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'pinecone')

# Default financial concepts to seed
DEFAULT_CONCEPTS = [
    "Sharpe Ratio", "Black-Scholes Model", "Duration", "Convexity",
    "Value at Risk", "Modern Portfolio Theory", "CAPM",
    "Beta Coefficient", "Alpha", "Treynor Ratio", "Sortino Ratio",
    "Options Greeks", "Implied Volatility", "Put-Call Parity",
    "Monte Carlo Simulation", "GARCH Model", "Efficient Frontier"
]


# ===== Task Functions =====

def load_concepts_list(**context):
    """Load list of concepts to seed from GCS or use default."""
    logger.info("Loading concepts list for seeding")
    
    try:
        gcs_hook = GCSHook()
        local_path = '/tmp/concepts_list.json'
        
        gcs_hook.download(
            bucket_name=GCS_BUCKET,
            object_name=CONCEPTS_LIST_PATH,
            filename=local_path
        )
        
        with open(local_path, 'r') as f:
            concepts_list = json.load(f)
        
        logger.info(f"Loaded {len(concepts_list)} concepts from GCS")
    
    except Exception as e:
        logger.warning(f"Could not load from GCS: {e}. Using default list.")
        concepts_list = DEFAULT_CONCEPTS
    
    # Push to XCom
    context['ti'].xcom_push(key='concepts_list', value=concepts_list)
    context['ti'].xcom_push(key='total_concepts', value=len(concepts_list))
    
    logger.info(f"✓ Will seed {len(concepts_list)} concepts")
    return concepts_list


def initialize_seed_job(**context):
    """Create seed job record in database for tracking."""
    logger.info("Initializing seed job in database")
    
    concepts_list = context['ti'].xcom_pull(key='concepts_list')
    dag_run_id = context['dag_run'].run_id
    execution_date = context['execution_date']
    
    # Create job record
    db_client = PostgresClient()
    
    with db_client.get_session() as session:
        seed_job = ConceptSeedJob(
            dag_run_id=dag_run_id,
            execution_date=execution_date,
            concepts_list=concepts_list,
            total_concepts=len(concepts_list),
            status='running'
        )
        session.add(seed_job)
        session.flush()
        
        job_id = seed_job.id
    
    context['ti'].xcom_push(key='seed_job_id', value=job_id)
    logger.info(f"✓ Created seed job {job_id} for {len(concepts_list)} concepts")
    
    return job_id


def process_concepts(**context):
    """Process each concept: retrieve context and generate note."""
    logger.info("Processing concepts - main generation loop")
    
    concepts_list = context['ti'].xcom_pull(key='concepts_list')
    seed_job_id = context['ti'].xcom_pull(key='seed_job_id')
    
    # Initialize services
    embedding_service = EmbeddingService()
    
    if VECTOR_DB_TYPE == 'pinecone':
        vector_db = PineconeVectorDB()
    else:
        vector_db = ChromaVectorDB()
    
    wikipedia_fallback = WikipediaFallback()
    
    retriever = RAGRetriever(
        vector_db=vector_db,
        embedding_service=embedding_service,
        wikipedia_fallback=wikipedia_fallback,
        top_k=5,
        confidence_threshold=0.7,
        enable_fallback=True
    )
    
    generator = ConceptNoteGenerator(
        model="gpt-4-turbo-preview",
        temperature=0.3
    )
    
    db_client = PostgresClient()
    
    # Track results
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    # Process each concept
    for idx, concept_name in enumerate(concepts_list, 1):
        logger.info(f"Processing {idx}/{len(concepts_list)}: {concept_name}")
        
        try:
            # Check if already exists
            existing = db_client.get_concept_note(concept_name)
            if existing:
                logger.info(f"Concept '{concept_name}' already cached, skipping")
                results['skipped'].append(concept_name)
                
                # Update job progress
                with db_client.get_session() as session:
                    job = session.query(ConceptSeedJob).filter(
                        ConceptSeedJob.id == seed_job_id
                    ).first()
                    if job:
                        job.processed_count = idx
                        job.skipped_count = len(results['skipped'])
                
                continue
            
            # Retrieve context
            retrieval_result = retriever.retrieve(concept_name)
            
            # Generate concept note
            request = ConceptNoteRequest(
                concept_name=concept_name,
                context=retrieval_result.contexts,
                source=retrieval_result.source.value,
                include_code_examples=True,
                target_length="comprehensive"
            )
            
            concept_note = generator.generate(request)
            
            # Cache in database
            db_client.cache_concept_note(concept_note)
            
            logger.info(
                f"✓ Successfully generated and cached: {concept_name} "
                f"(confidence: {concept_note.confidence_score:.2f})"
            )
            results['success'].append(concept_name)
            
            # Update job progress
            with db_client.get_session() as session:
                job = session.query(ConceptSeedJob).filter(
                    ConceptSeedJob.id == seed_job_id
                ).first()
                if job:
                    job.processed_count = idx
                    job.success_count = len(results['success'])
        
        except Exception as e:
            logger.error(f"✗ Failed to process '{concept_name}': {e}")
            results['failed'].append({
                'concept': concept_name,
                'error': str(e)
            })
            
            # Update job with failure
            with db_client.get_session() as session:
                job = session.query(ConceptSeedJob).filter(
                    ConceptSeedJob.id == seed_job_id
                ).first()
                if job:
                    job.processed_count = idx
                    job.failed_count = len(results['failed'])
    
    # Push results to XCom
    context['ti'].xcom_push(key='seed_results', value=results)
    
    logger.info(
        f"✓ Seeding complete: "
        f"{len(results['success'])} success, "
        f"{len(results['failed'])} failed, "
        f"{len(results['skipped'])} skipped"
    )
    
    return results


def finalize_seed_job(**context):
    """Finalize seed job and update status in database."""
    logger.info("Finalizing seed job")
    
    seed_job_id = context['ti'].xcom_pull(key='seed_job_id')
    results = context['ti'].xcom_pull(key='seed_results')
    
    db_client = PostgresClient()
    
    with db_client.get_session() as session:
        job = session.query(ConceptSeedJob).filter(
            ConceptSeedJob.id == seed_job_id
        ).first()
        
        if job:
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int((job.completed_at - job.started_at).total_seconds())
            job.status = 'completed' if not results['failed'] else 'completed_with_errors'
            
            if results['failed']:
                failed_concepts = [f['concept'] for f in results['failed']]
                job.error_message = f"Failed concepts: {', '.join(failed_concepts)}"
    
    logger.info(f"✓ Seed job {seed_job_id} finalized (duration: {job.duration_seconds}s)")


def upload_results_to_gcs(**context):
    """Upload seeding results to GCS for audit trail."""
    logger.info("Uploading seed results to GCS")
    
    results = context['ti'].xcom_pull(key='seed_results')
    execution_date = context['execution_date'].strftime('%Y%m%d_%H%M%S')
    
    results_file = f'/tmp/seed_results_{execution_date}.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    gcs_hook = GCSHook()
    gcs_hook.upload(
        bucket_name=GCS_BUCKET,
        object_name=f"concepts/seed_results_{execution_date}.json",
        filename=results_file
    )
    
    logger.info(f"✓ Results uploaded to GCS")


def send_completion_summary(**context):
    """Send comprehensive completion summary."""
    results = context['ti'].xcom_pull(key='seed_results')
    total_concepts = context['ti'].xcom_pull(key='total_concepts')
    
    success_rate = len(results['success']) / total_concepts * 100 if total_concepts > 0 else 0
    
    message = f"""
    ✅ CONCEPT SEEDING DAG COMPLETED
    
    📊 Results:
    - Total Concepts: {total_concepts}
    - ✓ Successfully Generated: {len(results['success'])}
    - ⊘ Skipped (Already Exist): {len(results['skipped'])}
    - ✗ Failed: {len(results['failed'])}
    
    📈 Success Rate: {success_rate:.1f}%
    
    📅 Execution Date: {context['execution_date']}
    """
    
    if results['failed']:
        message += f"\n\n⚠️ Failed Concepts:\n"
        for failure in results['failed'][:5]:
            message += f"  - {failure['concept']}: {failure['error'][:100]}\n"
    
    logger.info(message)
    return message


# ===== Create DAG =====
with DAG(
    'concept_seed_dag',
    default_args=default_args,
    description='Seed concept database with pre-generated notes',
    schedule_interval=None,  # Manual trigger or on-demand
    catchup=False,
    tags=['aurelia', 'concept-seeding', 'caching', 'production'],
    doc_md=__doc__
) as dag:
    
    load_task = PythonOperator(
        task_id='load_concepts_list',
        python_callable=load_concepts_list,
        provide_context=True
    )
    
    init_task = PythonOperator(
        task_id='initialize_seed_job',
        python_callable=initialize_seed_job,
        provide_context=True
    )
    
    process_task = PythonOperator(
        task_id='process_concepts',
        python_callable=process_concepts,
        provide_context=True,
        execution_timeout=timedelta(hours=2)
    )
    
    finalize_task = PythonOperator(
        task_id='finalize_seed_job',
        python_callable=finalize_seed_job,
        provide_context=True
    )
    
    upload_task = PythonOperator(
        task_id='upload_results_to_gcs',
        python_callable=upload_results_to_gcs,
        provide_context=True
    )
    
    notify_task = PythonOperator(
        task_id='send_completion_summary',
        python_callable=send_completion_summary,
        provide_context=True
    )
    
    # ===== Define Dependencies =====
    (load_task >> init_task >> process_task >> 
     finalize_task >> upload_task >> notify_task)