#!/usr/bin/env python3
"""
Financial RAG Engine - PDF Ingestion DAG
Cloud Run Job for processing PDF documents and updating vector store
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from google.cloud import storage
from google.cloud import secretmanager
import subprocess
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FintbxIngestDAG:
    """
    DAG for ingesting Financial Toolbox PDF and updating vector store
    """
    
    def __init__(self, 
                 project_id: str,
                 region: str = "us-central1",
                 bucket_name: str = "financial-rag-artifacts",
                 secret_name: str = "financial-rag-secrets"):
        self.project_id = project_id
        self.region = region
        self.bucket_name = bucket_name
        self.secret_name = secret_name
        
        # Initialize GCP clients
        self.storage_client = storage.Client(project=project_id)
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
    def _ensure_bucket_exists(self):
        """Create GCS bucket if it doesn't exist"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name, 
                    location=self.region
                )
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket exists: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def _get_secret(self, secret_key: str) -> str:
        """Retrieve secret from Secret Manager"""
        try:
            secret_path = f"projects/{self.project_id}/secrets/{self.secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            secrets = json.loads(response.payload.data.decode("UTF-8"))
            return secrets[secret_key]
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_key}: {e}")
            raise
    
    def _download_pdf_from_gcs(self, pdf_path: str) -> str:
        """Download PDF from GCS to local temp file"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(pdf_path)
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            blob.download_to_filename(temp_file.name)
            
            logger.info(f"Downloaded PDF: {pdf_path} -> {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            raise
    
    def _upload_artifacts_to_gcs(self, local_dir: str, gcs_prefix: str):
        """Upload processing artifacts to GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, local_dir)
                    gcs_path = f"{gcs_prefix}/{relative_path}"
                    
                    blob = bucket.blob(gcs_path)
                    blob.upload_from_filename(local_path)
                    logger.info(f"Uploaded: {relative_path} -> {gcs_path}")
                    
        except Exception as e:
            logger.error(f"Error uploading artifacts: {e}")
            raise
    
    def run_pipeline(self, 
                    pdf_path: str = "data/raw/fintbx.pdf",
                    pages: int = None,
                    use_chromadb: bool = True,
                    start_page: int = None,
                    end_page: int = None) -> Dict[str, Any]:
        """
        Run the PDF processing pipeline
        
        Args:
            pdf_path: Path to PDF in GCS
            pages: Number of pages to process (None for all)
            use_chromadb: Use ChromaDB instead of Pinecone
            start_page: Start page for range processing
            end_page: End page for range processing
        """
        logger.info("🚀 Starting Fintbx Ingest DAG")
        logger.info(f"   PDF: {pdf_path}")
        logger.info(f"   Pages: {pages}")
        logger.info(f"   ChromaDB: {use_chromadb}")
        
        # Create timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"ingest_{timestamp}"
        
        try:
            # Step 1: Download PDF from GCS
            logger.info("📥 Step 1: Downloading PDF from GCS")
            local_pdf = self._download_pdf_from_gcs(pdf_path)
            
            # Step 2: Set up environment variables
            logger.info("🔧 Step 2: Setting up environment")
            os.environ["OPENAI_API_KEY"] = self._get_secret("OPENAI_API_KEY")
            if not use_chromadb:
                os.environ["PINECONE_API_KEY"] = self._get_secret("PINECONE_API_KEY")
            
            # Step 3: Run pipeline
            logger.info("⚙️ Step 3: Running PDF processing pipeline")
            
            # Build pipeline command
            cmd = [
                "python", "run_pipeline.py",
                "--pdf", local_pdf,
                "--yes"  # Auto-confirm
            ]
            
            if pages:
                cmd.extend(["--pages", str(pages)])
            elif start_page and end_page:
                cmd.extend(["--start", str(start_page), "--end", str(end_page)])
            
            if use_chromadb:
                cmd.append("--use-chromadb")
            
            # Run pipeline
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="/app"  # Cloud Run working directory
            )
            
            if result.returncode != 0:
                logger.error(f"Pipeline failed: {result.stderr}")
                raise RuntimeError(f"Pipeline failed: {result.stderr}")
            
            logger.info("✅ Pipeline completed successfully")
            
            # Step 4: Upload artifacts to GCS
            logger.info("📤 Step 4: Uploading artifacts to GCS")
            artifacts_prefix = f"artifacts/{run_id}"
            self._upload_artifacts_to_gcs("data/processed", artifacts_prefix)
            
            # Step 5: Update metadata
            metadata = {
                "run_id": run_id,
                "timestamp": timestamp,
                "pdf_path": pdf_path,
                "pages_processed": pages,
                "use_chromadb": use_chromadb,
                "status": "completed",
                "artifacts_prefix": artifacts_prefix,
                "pipeline_output": result.stdout
            }
            
            # Save metadata to GCS
            metadata_blob = self.storage_client.bucket(self.bucket_name).blob(
                f"{artifacts_prefix}/run_metadata.json"
            )
            metadata_blob.upload_from_string(json.dumps(metadata, indent=2))
            
            logger.info(f"✅ DAG completed successfully: {run_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ DAG failed: {e}")
            
            # Upload error logs
            error_metadata = {
                "run_id": run_id,
                "timestamp": timestamp,
                "status": "failed",
                "error": str(e),
                "pdf_path": pdf_path
            }
            
            try:
                error_blob = self.storage_client.bucket(self.bucket_name).blob(
                    f"artifacts/{run_id}/error_metadata.json"
                )
                error_blob.upload_from_string(json.dumps(error_metadata, indent=2))
            except:
                pass  # Don't fail on error logging
            
            raise
        
        finally:
            # Cleanup temp files
            try:
                if 'local_pdf' in locals():
                    os.unlink(local_pdf)
            except:
                pass

def main():
    """Main entry point for Cloud Run Job"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fintbx Ingest DAG")
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument("--pdf-path", default="data/raw/fintbx.pdf", help="PDF path in GCS")
    parser.add_argument("--pages", type=int, help="Number of pages to process")
    parser.add_argument("--start-page", type=int, help="Start page for range")
    parser.add_argument("--end-page", type=int, help="End page for range")
    parser.add_argument("--use-chromadb", action="store_true", help="Use ChromaDB")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    parser.add_argument("--bucket", default="financial-rag-artifacts", help="GCS Bucket")
    
    args = parser.parse_args()
    
    # Create and run DAG
    dag = FintbxIngestDAG(
        project_id=args.project_id,
        region=args.region,
        bucket_name=args.bucket
    )
    
    result = dag.run_pipeline(
        pdf_path=args.pdf_path,
        pages=args.pages,
        use_chromadb=args.use_chromadb,
        start_page=args.start_page,
        end_page=args.end_page
    )
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
