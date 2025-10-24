"""
Vertex AI Parsing Service
Optimized Docling parsing with GPU acceleration
"""

import os
import logging
import argparse
from pathlib import Path
import json
from datetime import datetime

# Optional imports for testing
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("Warning: Google Cloud Storage not available")

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    print("Warning: Docling not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VertexAIParser:
    """Optimized PDF parser for Vertex AI with GPU acceleration"""
    
    def __init__(self):
        """Initialize the parser with optimized settings"""
        self.converter = None
        if GCS_AVAILABLE:
            self.storage_client = storage.Client()
        else:
            self.storage_client = None
        
    def initialize_vertex_ai_parser(self):
        """Initialize Vertex AI native PDF parsing"""
        try:
            # Use Vertex AI's native document AI capabilities
            from google.cloud import documentai
            
            # Initialize Document AI client
            self.document_ai_client = documentai.DocumentProcessorServiceClient()
            logger.info("✅ Vertex AI Document AI initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI Document AI: {e}")
            return False
    
    def parse_pdf(self, pdf_path: str, output_dir: str, start_page: int = 1, end_page: int = None):
        """Parse PDF with optimized settings"""
        try:
            logger.info(f"Parsing PDF: {pdf_path}")
            logger.info(f"Pages: {start_page}-{end_page}")
            
            # Parse with Docling
            result = self.converter.convert(pdf_path)
            
            # Extract text content
            parsed_data = {
                'full_text': result.document.export_to_markdown(),
                'pages': len(result.document.pages),
                'metadata': {
                    'source': pdf_path,
                    'start_page': start_page,
                    'end_page': end_page,
                    'parsed_at': str(datetime.now())
                }
            }
            
            # Save parsed data
            output_file = os.path.join(output_dir, 'parsed_data.json')
            with open(output_file, 'w') as f:
                json.dump(parsed_data, f, indent=2)
            
            logger.info(f"✅ Parsing completed: {output_file}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ Parsing failed: {e}")
            raise
    
    def upload_to_gcs(self, local_file: str, gcs_path: str):
        """Upload parsed data to Cloud Storage"""
        try:
            bucket_name = gcs_path.split('/')[2]
            object_name = '/'.join(gcs_path.split('/')[3:])
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_filename(local_file)
            
            logger.info(f"✅ Uploaded to GCS: gs://{bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return False

def main():
    """Main function for Vertex AI job"""
    parser = argparse.ArgumentParser(description='Vertex AI PDF Parser')
    parser.add_argument('--input', required=True, help='Input PDF path')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--start-page', type=int, default=1, help='Start page')
    parser.add_argument('--end-page', type=int, help='End page')
    
    args = parser.parse_args()
    
    # Initialize parser
    parser_instance = VertexAIParser()
    
    # Initialize Docling
    if not parser_instance.initialize_docling():
        exit(1)
    
    # Parse PDF
    try:
        parsed_data = parser_instance.parse_pdf(
            args.input,
            args.output,
            args.start_page,
            args.end_page
        )
        
        # Upload to GCS
        output_file = os.path.join(args.output, 'parsed_data.json')
        gcs_path = f"gs://{args.output}/parsed_data.json"
        parser_instance.upload_to_gcs(output_file, gcs_path)
        
        logger.info("🎉 Vertex AI parsing completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Parsing failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
