#!/usr/bin/env python3
"""
Vertex AI Native PDF Parser
Uses Google's Document AI for fast, GPU-accelerated PDF parsing
"""

import os
import logging
import argparse
from pathlib import Path
import json
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional imports for testing
try:
    from google.cloud import storage
    from google.cloud import documentai
    GCS_AVAILABLE = True
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    DOCUMENT_AI_AVAILABLE = False
    print("Warning: Google Cloud services not available")

class VertexAIParser:
    """Native Vertex AI PDF parser using Document AI"""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        """Initialize the parser with Vertex AI Document AI"""
        self.project_id = project_id
        self.location = location
        self.storage_client = None
        self.document_ai_client = None
        
        if GCS_AVAILABLE:
            self.storage_client = storage.Client(project=project_id)
        if DOCUMENT_AI_AVAILABLE:
            self.document_ai_client = documentai.DocumentProcessorServiceClient()
    
    def parse_pdf_with_document_ai(self, pdf_path: str, output_dir: str, start_page: int = 1, end_page: int = None):
        """Parse PDF using Vertex AI Document AI (much faster than Docling)"""
        try:
            logger.info(f"🚀 Parsing PDF with Vertex AI Document AI: {pdf_path}")
            logger.info(f"   Pages: {start_page}-{end_page}")
            
            # Download PDF from GCS if needed
            local_pdf_path = pdf_path
            if pdf_path.startswith("gs://") and self.storage_client:
                bucket_name, blob_name = pdf_path[5:].split("/", 1)
                bucket = self.storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                
                local_pdf_path = f"/tmp/{Path(pdf_path).name}"
                logger.info(f"📥 Downloading {pdf_path} to {local_pdf_path}")
                blob.download_to_filename(local_pdf_path)
            
            # Use Document AI for parsing
            if not self.document_ai_client:
                logger.error("❌ Document AI client not available")
                return None
            
            # Read PDF file
            with open(local_pdf_path, "rb") as f:
                pdf_content = f.read()
            
            # Create document
            document = documentai.Document(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            # Process document with Document AI
            logger.info("⚡ Processing with Vertex AI Document AI...")
            
            # Use the general document processor
            processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/general"
            
            request = documentai.ProcessRequest(
                name=processor_name,
                document=document
            )
            
            result = self.document_ai_client.process_document(request=request)
            document = result.document
            
            # Extract text content
            full_text = document.text
            
            # Extract structured data
            parsed_data = {
                "source_pdf": pdf_path,
                "pages_processed": f"{start_page}-{end_page}",
                "extracted_text": full_text,
                "page_count": len(document.pages),
                "entities": [entity.text for entity in document.entities],
                "tables": [table.text for table in document.pages[0].tables] if document.pages else [],
                "timestamp": datetime.now().isoformat(),
                "parser": "vertex_ai_document_ai"
            }
            
            # Upload results to GCS
            if output_dir.startswith("gs://") and self.storage_client:
                output_bucket_name, output_blob_prefix = output_dir[5:].split("/", 1)
                output_bucket = self.storage_client.bucket(output_bucket_name)
                output_blob_name = f"{output_blob_prefix}/{Path(pdf_path).stem}_parsed_{start_page}-{end_page}.json"
                output_blob = output_bucket.blob(output_blob_name)
                
                logger.info(f"📤 Uploading to {output_blob_name}")
                output_blob.upload_from_string(json.dumps(parsed_data, indent=2), content_type="application/json")
            else:
                # Save locally
                local_output_path = Path(output_dir) / f"{Path(pdf_path).stem}_parsed_{start_page}-{end_page}.json"
                local_output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_output_path, 'w') as f:
                    json.dump(parsed_data, f, indent=2)
                logger.info(f"💾 Saved to {local_output_path}")

            logger.info("✅ Vertex AI parsing completed successfully!")
            logger.info(f"   Text length: {len(full_text)} characters")
            logger.info(f"   Pages: {len(document.pages)}")
            logger.info(f"   Entities: {len(document.entities)}")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ Vertex AI parsing failed: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vertex AI Native PDF Parser")
    parser.add_argument("--pdf_path", type=str, required=True, help="Path to the input PDF (gs:// or local)")
    parser.add_argument("--output_dir", type=str, default="./output", help="Directory for output (gs:// or local)")
    parser.add_argument("--start_page", type=int, default=1, help="Start page for parsing")
    parser.add_argument("--end_page", type=int, help="End page for parsing (inclusive)")
    parser.add_argument("--project_id", type=str, required=True, help="GCP Project ID")
    parser.add_argument("--location", type=str, default="us-central1", help="GCP Location")
    
    args = parser.parse_args()
    
    vertex_parser = VertexAIParser(project_id=args.project_id, location=args.location)
    vertex_parser.parse_pdf_with_document_ai(args.pdf_path, args.output_dir, args.start_page, args.end_page)
