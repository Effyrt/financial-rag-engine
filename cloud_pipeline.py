"""
Cloud-optimized PDF processing pipeline for GCP Cloud Run Jobs.

This version is designed to run efficiently on cloud infrastructure with:
- Cloud Storage for file I/O
- Secret Manager for API keys
- Cloud SQL for metadata
- Optimized for parallel processing
"""

import logging
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import argparse
import tempfile

# Cloud dependencies
from google.cloud import storage
from google.cloud import secretmanager

# Local imports
from pipeline.pdf_parser_docling_fixed import DoclingPDFParserFixed
from pipeline.chunker_strategies import CodeAwareStrategy
from pipeline.embedder import EmbeddingGenerator
from pipeline.vector_store_chroma import ChromaVectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manages file operations with Google Cloud Storage."""
    
    def __init__(self, bucket_name: str):
        """Initialize Cloud Storage manager."""
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        logger.info(f"CloudStorageManager initialized with bucket: {bucket_name}")
    
    def download_file(self, blob_name: str, local_path: str) -> bool:
        """Download file from Cloud Storage."""
        try:
            blob = self.bucket.blob(blob_name)
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded {blob_name} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {blob_name}: {e}")
            return False
    
    def upload_file(self, local_path: str, blob_name: str) -> bool:
        """Upload file to Cloud Storage."""
        try:
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            logger.info(f"Uploaded {local_path} to {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def upload_directory(self, local_dir: str, remote_prefix: str) -> bool:
        """Upload entire directory to Cloud Storage."""
        try:
            local_path = Path(local_dir)
            for file_path in local_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(local_path)
                    blob_name = f"{remote_prefix}/{relative_path}"
                    self.upload_file(str(file_path), blob_name)
            logger.info(f"Uploaded directory {local_dir} to {remote_prefix}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload directory {local_dir}: {e}")
            return False


class SecretManager:
    """Manages secrets from Google Secret Manager."""
    
    def __init__(self, project_id: str):
        """Initialize Secret Manager."""
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        logger.info(f"SecretManager initialized for project: {project_id}")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret value from Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Retrieved secret: {secret_name}")
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            return None


class CloudPipelineRunner:
    """Runs the PDF processing pipeline on cloud infrastructure."""
    
    def __init__(self, project_id: str, bucket_name: str):
        """Initialize cloud pipeline runner."""
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_manager = CloudStorageManager(bucket_name)
        self.secret_manager = SecretManager(project_id)
        
        # Initialize components
        self.embedder = EmbeddingGenerator()
        self.vector_store = ChromaVectorStore()
        
        logger.info("CloudPipelineRunner initialized")
    
    def run_pipeline(self, pages: str = "all", start_page: int = 1, end_page: int = 50) -> Dict[str, Any]:
        """Run the complete PDF processing pipeline."""
        logger.info(f"Starting cloud pipeline: pages={pages}, start={start_page}, end={end_page}")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Download PDF from Cloud Storage
            pdf_path = temp_path / "fintbx.pdf"
            if not self.storage_manager.download_file("pdf-files/fintbx.pdf", str(pdf_path)):
                raise Exception("Failed to download PDF from Cloud Storage")
            
            # Determine page range
            if pages == "all" and end_page == 50:  # Process 50 pages when end_page is 50
                logger.info(f"Processing pages {start_page}-{end_page}")
            elif pages == "all":
                total_pages = self._count_pdf_pages(str(pdf_path))
                start_page = 1
                end_page = total_pages
                logger.info(f"Processing all {total_pages} pages")
            else:
                logger.info(f"Processing pages {start_page}-{end_page}")
            
            # Parse PDF
            logger.info("Starting PDF parsing...")
            parser = DoclingPDFParserFixed(start_page=start_page, max_pages=end_page-start_page+1)
            parsed_data = parser.parse_pdf(str(pdf_path))
            
            # Save parsed data
            parsed_file = temp_path / f"docling_parsed_{start_page}_{end_page}.json"
            with open(parsed_file, 'w') as f:
                json.dump(parsed_data, f, indent=2)
            
            # Upload parsed data
            self.storage_manager.upload_file(
                str(parsed_file), 
                f"processed-data/docling_parsed_{start_page}_{end_page}.json"
            )
            
            # Chunk the text
            logger.info("Starting text chunking...")
            chunker = CodeAwareStrategy(chunk_size=1000, chunk_overlap=100)
            
            # Process chunks by topic
            chunks_by_topic = {}
            structured_elements = []
            
            full_text = parsed_data.get('full_text', '')
            topics = parsed_data.get('topics', [])
            
            # Create chunks
            chunks = chunker.chunk_text(full_text, {'page_range': f"{start_page}-{end_page}"})
            
            # Organize chunks by topic
            for chunk in chunks:
                topic = self._determine_topic(chunk, topics)
                if topic not in chunks_by_topic:
                    chunks_by_topic[topic] = []
                chunks_by_topic[topic].append(chunk)
            
            # Process structured elements
            for element_type in ['code_blocks', 'tables', 'images', 'figures']:
                if element_type in parsed_data:
                    structured_elements.extend(parsed_data[element_type])
            
            # Generate embeddings and store in vector database
            logger.info("Generating embeddings and storing in vector database...")
            all_chunks = []
            for topic, topic_chunks in chunks_by_topic.items():
                for chunk in topic_chunks:
                    chunk['topic'] = topic
                    chunk['embedding'] = self.embedder.generate_embedding(chunk['chunk_text'])
                    all_chunks.append(chunk)
            
            # Store in ChromaDB
            if all_chunks:
                self.vector_store.upsert_vectors(all_chunks)
                logger.info(f"Stored {len(all_chunks)} chunks in vector database")
            
            # Save chunks and structured elements
            chunks_file = temp_path / f"chunks_{start_page}_{end_page}.json"
            with open(chunks_file, 'w') as f:
                json.dump(chunks_by_topic, f, indent=2)
            
            elements_file = temp_path / f"structured_elements_{start_page}_{end_page}.json"
            with open(elements_file, 'w') as f:
                json.dump(structured_elements, f, indent=2)
            
            # Upload results to Cloud Storage
            self.storage_manager.upload_file(
                str(chunks_file), 
                f"processed-data/chunks_{start_page}_{end_page}.json"
            )
            self.storage_manager.upload_file(
                str(elements_file), 
                f"processed-data/structured_elements_{start_page}_{end_page}.json"
            )
            
            # Log completion
            result = {
                'status': 'success',
                'pages_processed': f"{start_page}-{end_page}",
                'chunks_created': len(all_chunks),
                'topics_found': len(chunks_by_topic),
                'structured_elements': len(structured_elements),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Pipeline completed successfully: {result}")
            return result
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        """Count total pages in PDF."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to count PDF pages: {e}")
            return 3000  # Default fallback
    
    def _determine_topic(self, chunk: Dict[str, Any], topics: List[Dict[str, Any]]) -> str:
        """Determine topic for a chunk."""
        # Simple topic assignment based on content
        chunk_text = chunk.get('chunk_text', '').lower()
        
        if 'bond' in chunk_text or 'bndprice' in chunk_text:
            return 'bond_functions'
        elif 'portfolio' in chunk_text or 'portopt' in chunk_text:
            return 'portfolio_functions'
        elif 'date' in chunk_text or 'datetime' in chunk_text:
            return 'date_functions'
        elif 'matrix' in chunk_text or 'vector' in chunk_text:
            return 'matrix_operations'
        else:
            return 'general'


def main():
    """Main function for cloud pipeline execution."""
    parser = argparse.ArgumentParser(description='Cloud PDF Processing Pipeline')
    parser.add_argument('--pages', default='all', help='Pages to process (e.g., "all", "1-50")')
    parser.add_argument('--start', type=int, default=1, help='Start page number')
    parser.add_argument('--end', type=int, default=50, help='End page number')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--bucket-name', required=True, help='Cloud Storage bucket name')
    
    args = parser.parse_args()
    
    # Initialize pipeline runner
    runner = CloudPipelineRunner(args.project_id, args.bucket_name)
    
    try:
        # Run pipeline
        result = runner.run_pipeline(
            pages=args.pages,
            start_page=args.start,
            end_page=args.end
        )
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
