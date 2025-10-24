"""
Airflow DAG for PDF Ingestion and Vector Database Population - ENTERPRISE VERSION
Complete pipeline for parsing, chunking, embedding, and storing Financial Toolbox PDF.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from datetime import datetime, timedelta
from loguru import logger
import sys
import os
import json

# Add src to path for imports
sys.path.insert(0, '/opt/airflow/dags/repo/src')

from parsers.advanced_pdf_parser import FinancialToolboxParser
from parsers.chunking_strategy import FinancialChunkingStrategy
from embeddings.embedding_service import EmbeddingService
from vectordb.pinecone_client import PineconeVectorDB
from vectordb.chromadb_client import ChromaVectorDB
from database.postgres_client import PostgresClient
from database.models import VectorIndexMetadata

# ===== DAG Configuration =====
default_args = {
    'owner': 'aurelia',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Environment variables
GCS_BUCKET = os.getenv('GCP_BUCKET_NAME', 'aurelia-artifacts')
PDF_PATH = 'raw/fintbx.pdf'
CHUNKS_OUTPUT_PATH = 'processed/chunks/'
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'pinecone')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))


# ===== Task Functions =====

def download_pdf_from_gcs(**context):
    """Download PDF from GCS to local temp storage."""
    logger.info(f"Downloading PDF from gs://{GCS_BUCKET}/{PDF_PATH}")
    
    gcs_hook = GCSHook()
    local_path = '/tmp/fintbx.pdf'
    
    gcs_hook.download(
        bucket_name=GCS_BUCKET,
        object_name=PDF_PATH,
        filename=local_path
    )
    
    # Push local path to XCom
    context['ti'].xcom_push(key='pdf_local_path', value=local_path)
    logger.info(f"✓ PDF downloaded to {local_path}")
    
    return local_path


def parse_pdf(**context):
    """Parse PDF and extract all elements with advanced parser."""
    logger.info("Starting PDF parsing with enterprise parser")
    
    # Get PDF path from XCom
    pdf_path = context['ti'].xcom_pull(key='pdf_local_path')
    
    # Initialize advanced parser
    parser = FinancialToolboxParser(
        extract_images=True,
        extract_tables=True,
        ocr_enabled=True,
        parallel_processing=True,
        max_workers=4,
        quality_threshold=0.7
    )
    
    # Parse PDF
    parsed_doc = parser.parse(pdf_path)
    
    # Save parsed elements to temp location
    output_path = '/tmp/parsed_elements.json'
    parser.export_to_json(parsed_doc, output_path)
    
    # Push to XCom
    context['ti'].xcom_push(key='parsed_elements_path', value=output_path)
    context['ti'].xcom_push(key='total_elements', value=len(parsed_doc.elements))
    context['ti'].xcom_push(key='quality_metrics', value=parsed_doc.quality_metrics)
    
    logger.info(
        f"✓ Parsed {len(parsed_doc.elements)} elements from {parsed_doc.total_pages} pages "
        f"(avg confidence: {parsed_doc.quality_metrics['avg_confidence']:.2%})"
    )
    
    return output_path


def chunk_elements(**context):
    """Chunk parsed elements using advanced strategy."""
    logger.info("Starting intelligent chunking process")
    
    # Get parsed elements path
    parsed_path = context['ti'].xcom_pull(key='parsed_elements_path')
    
    # Load parsed elements
    import json
    from parsers.advanced_pdf_parser import ParsedElement
    
    with open(parsed_path, 'r') as f:
        data = json.load(f)
    
    # Reconstruct ParsedElement objects
    elements = []
    for elem_dict in data['elements']:
        element = ParsedElement(
            content=elem_dict['content'],
            element_type=elem_dict['element_type'],
            page_number=elem_dict['page_number'],
            section_title=elem_dict['section_title'],
            subsection_title=elem_dict['subsection_title'],
            bounding_box=tuple(elem_dict['bounding_box']) if elem_dict.get('bounding_box') else None,
            metadata=elem_dict['metadata']
        )
        elements.append(element)
    
    # Initialize chunking strategy
    chunker = FinancialChunkingStrategy(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        preserve_code=True,
        preserve_formulas=True,
        respect_sections=True
    )
    
    # Chunk elements
    chunks = chunker.chunk_parsed_document(elements)
    
    # Save chunks
    chunks_output = '/tmp/chunks.json'
    from dataclasses import asdict
    
    with open(chunks_output, 'w') as f:
        json.dump([asdict(chunk) for chunk in chunks], f)
    
    # Get statistics
    stats = chunker.get_chunking_stats(chunks)
    
    # Push to XCom
    context['ti'].xcom_push(key='chunks_path', value=chunks_output)
    context['ti'].xcom_push(key='total_chunks', value=len(chunks))
    context['ti'].xcom_push(key='chunking_stats', value=stats)
    
    logger.info(
        f"✓ Created {len(chunks)} chunks "
        f"(avg size: {stats['avg_chunk_size']:.0f} chars, "
        f"code: {stats['code_chunks']}, formulas: {stats['formula_chunks']})"
    )
    
    return chunks_output


def generate_embeddings(**context):
    """Generate embeddings for all chunks using OpenAI."""
    logger.info("Generating embeddings with OpenAI text-embedding-3-large")
    
    # Get chunks path
    chunks_path = context['ti'].xcom_pull(key='chunks_path')
    
    # Load chunks
    from parsers.chunking_strategy import Chunk
    
    with open(chunks_path, 'r') as f:
        chunk_dicts = json.load(f)
    
    # Reconstruct Chunk objects
    chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
    
    # Initialize embedding service
    embedding_service = EmbeddingService(
        model="text-embedding-3-large",
        batch_size=100,
        max_workers=5
    )
    
    # Generate embeddings
    embedding_results = embedding_service.embed_chunks(chunks)
    embeddings = [result.embedding for result in embedding_results]
    
    # Save embeddings with chunks
    output_data = {
        'chunks': chunk_dicts,
        'embeddings': embeddings
    }
    
    embeddings_output = '/tmp/chunks_with_embeddings.json'
    with open(embeddings_output, 'w') as f:
        json.dump(output_data, f)
    
    # Get cost summary
    cost_summary = embedding_service.get_cost_summary()
    
    # Push to XCom
    context['ti'].xcom_push(key='embeddings_path', value=embeddings_output)
    context['ti'].xcom_push(key='embedding_cost', value=cost_summary)
    
    logger.info(
        f"✓ Generated {len(embeddings)} embeddings "
        f"(cost: ${cost_summary['total_cost_usd']:.4f})"
    )
    
    return embeddings_output


def upsert_to_vector_db(**context):
    """Upsert chunks and embeddings to vector database."""
    logger.info(f"Upserting to vector DB (type: {VECTOR_DB_TYPE})")
    
    # Get embeddings path
    embeddings_path = context['ti'].xcom_pull(key='embeddings_path')
    
    # Load data
    from parsers.chunking_strategy import Chunk
    
    with open(embeddings_path, 'r') as f:
        data = json.load(f)
    
    chunks = [Chunk(**c) for c in data['chunks']]
    embeddings = data['embeddings']
    
    # Initialize vector DB
    if VECTOR_DB_TYPE == 'pinecone':
        vector_db = PineconeVectorDB()
        namespace = "financial-toolbox"
    else:
        vector_db = ChromaVectorDB()
        namespace = None
    
    # Upsert
    result = vector_db.upsert_chunks(chunks=chunks, embeddings=embeddings, namespace=namespace)
    
    # Update metadata in PostgreSQL
    db_client = PostgresClient()
    
    with db_client.get_session() as session:
        metadata = VectorIndexMetadata(
            index_name=result.get('index_name', 'aurelia-financial-concepts'),
            namespace=result.get('namespace', ''),
            vector_db_type=VECTOR_DB_TYPE,
            total_vectors=result['upserted_count'],
            dimension=3072,
            update_source='airflow_fintbx_ingest_dag',
            chunks_added=result['upserted_count']
        )
        session.add(metadata)
    
    logger.info(f"✓ Upserted {result['upserted_count']} vectors to {VECTOR_DB_TYPE}")
    
    return result


def upload_artifacts_to_gcs(**context):
    """Upload processed artifacts back to GCS."""
    logger.info("Uploading artifacts to GCS")
    
    gcs_hook = GCSHook()
    
    # Upload chunks
    chunks_path = context['ti'].xcom_pull(key='chunks_path')
    execution_date = context['execution_date'].strftime('%Y%m%d_%H%M%S')
    
    gcs_hook.upload(
        bucket_name=GCS_BUCKET,
        object_name=f"{CHUNKS_OUTPUT_PATH}chunks_{execution_date}.json",
        filename=chunks_path
    )
    
    # Upload embeddings
    embeddings_path = context['ti'].xcom_pull(key='embeddings_path')
    gcs_hook.upload(
        bucket_name=GCS_BUCKET,
        object_name=f"{CHUNKS_OUTPUT_PATH}embeddings_{execution_date}.json",
        filename=embeddings_path
    )
    
    logger.info(f"✓ Uploaded artifacts to gs://{GCS_BUCKET}/{CHUNKS_OUTPUT_PATH}")


def send_completion_notification(**context):
    """Send completion notification with comprehensive stats."""
    total_chunks = context['ti'].xcom_pull(key='total_chunks')
    chunking_stats = context['ti'].xcom_pull(key='chunking_stats')
    embedding_cost = context['ti'].xcom_pull(key='embedding_cost')
    quality_metrics = context['ti'].xcom_pull(key='quality_metrics')
    
    message = f"""
    ✅ FINTBX PDF INGESTION DAG COMPLETED SUCCESSFULLY
    
    📊 Statistics:
    - Total Chunks: {total_chunks}
    - Avg Chunk Size: {chunking_stats.get('avg_chunk_size', 0):.0f} chars
    - Code Chunks: {chunking_stats.get('code_chunks', 0)}
    - Formula Chunks: {chunking_stats.get('formula_chunks', 0)}
    - Table Chunks: {chunking_stats.get('table_chunks', 0)}
    
    🎯 Quality Metrics:
    - Avg Confidence: {quality_metrics.get('avg_confidence', 0):.2%}
    - Elements/Page: {quality_metrics.get('elements_per_page', 0):.1f}
    
    💰 Embedding Cost:
    - Total Tokens: {embedding_cost.get('total_tokens', 0):,}
    - Total Cost: ${embedding_cost.get('total_cost_usd', 0):.4f}
    - Model: {embedding_cost.get('model', 'N/A')}
    
    📅 Execution Date: {context['execution_date']}
    ⏱️  DAG Run ID: {context['dag_run'].run_id}
    """
    
    logger.info(message)
    # In production, send via email/Slack/PagerDuty
    return message


# ===== Create DAG =====
with DAG(
    'fintbx_ingest_dag',
    default_args=default_args,
    description='Ingest and vectorize Financial Toolbox PDF with enterprise features',
    schedule_interval='@weekly',  # Run every week
    catchup=False,
    tags=['aurelia', 'pdf-ingestion', 'vectorization', 'production'],
    doc_md=__doc__
) as dag:
    
    # Task 1: Download PDF from GCS
    download_task = PythonOperator(
        task_id='download_pdf_from_gcs',
        python_callable=download_pdf_from_gcs,
        provide_context=True,
        doc_md="Download fintbx.pdf from Google Cloud Storage"
    )
    
    # Task 2: Parse PDF with advanced parser
    parse_task = PythonOperator(
        task_id='parse_pdf',
        python_callable=parse_pdf,
        provide_context=True,
        doc_md="Parse PDF using enterprise multi-strategy parser"
    )
    
    # Task 3: Chunk elements intelligently
    chunk_task = PythonOperator(
        task_id='chunk_elements',
        python_callable=chunk_elements,
        provide_context=True,
        doc_md="Chunk parsed elements with section-aware strategy"
    )
    
    # Task 4: Generate embeddings
    embed_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings,
        provide_context=True,
        doc_md="Generate embeddings using OpenAI text-embedding-3-large"
    )
    
    # Task 5: Upsert to vector database
    upsert_task = PythonOperator(
        task_id='upsert_to_vector_db',
        python_callable=upsert_to_vector_db,
        provide_context=True,
        doc_md="Upsert embeddings to Pinecone/ChromaDB"
    )
    
    # Task 6: Upload artifacts to GCS
    upload_task = PythonOperator(
        task_id='upload_artifacts_to_gcs',
        python_callable=upload_artifacts_to_gcs,
        provide_context=True,
        doc_md="Upload processed artifacts back to GCS"
    )
    
    # Task 7: Send completion notification
    notify_task = PythonOperator(
        task_id='send_completion_notification',
        python_callable=send_completion_notification,
        provide_context=True,
        doc_md="Send completion notification with stats"
    )
    
    # ===== Define Task Dependencies =====
    (download_task >> parse_task >> chunk_task >> 
     embed_task >> upsert_task >> upload_task >> notify_task)