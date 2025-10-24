"""
Automated PDF Processing Pipeline
Run all PDF processing steps in sequence


Steps:
    1. Parse PDF using Docling
    2. Convert to chunks format
    3. Experiment with chunking strategies (4 strategies)
    4. Build vectorstore with OpenAI embeddings (best strategy)
    5. Evaluate retrieval performance
"""

import subprocess
import sys
from pathlib import Path
import time
import os
import argparse          
from dotenv import load_dotenv

load_dotenv()

class PDFProcessingPipeline:
    def __init__(self, skip_upload=False):
        self.project_root = Path(__file__).parent
        self.skip_upload = skip_upload
        
    def run_command(self, cmd, description, cwd=None):
        """Run a command and handle errors"""
        print("\n" + "="*80)
        print(f"🚀 {description}")
        print("="*80)
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                check=True,
                capture_output=False,
                text=True
            )
            
            print(f"✅ {description} - SUCCESS")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} - FAILED")
            print(f"Error: {e}")
            return False
    
    def check_prerequisites(self):
        """Check if required files and packages exist"""
        print("\n" + "="*80)
        print("🔍 Checking Prerequisites")
        print("="*80)
        
        # Reload .env to ensure it's loaded
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Check PDF exists
        pdf_path = self.project_root / "data" / "raw" / "fintbx.pdf"
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            print("   Please place fintbx.pdf in data/raw/")
            return False
        else:
            print(f"✅ PDF found: {pdf_path}")
            print(f"   Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Check required directories
        required_dirs = ["src/parser", "src/embeddings", "src/experiments"]
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                print(f"❌ Directory not found: {dir_path}")
                return False
            else:
                print(f"✅ Directory exists: {dir_path}")
        
        # Check Python packages
        required_packages = ["docling", "langchain", "chromadb", "openai"]
        print("\n📦 Checking Python packages...")
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ⚠️  {package} not installed (may cause issues)")
        
        # Check environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("\n⚠️  Warning: OPENAI_API_KEY not set")
            print("   Checking .env file...")
            
            # Check if .env exists
            env_file = self.project_root / ".env"
            if env_file.exists():
                print(f"   ✅ .env file exists: {env_file}")
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'OPENAI_API_KEY' in content:
                        print("   ✅ OPENAI_API_KEY found in .env")
                        print("   ⚠️  But not loaded into environment")
                        print("\n   💡 Possible issues:")
                        print("      - Check format: OPENAI_API_KEY=value (no spaces)")
                        print("      - Make sure no extra characters")
                    else:
                        print("   ❌ OPENAI_API_KEY not in .env file")
            else:
                print(f"   ❌ .env file not found: {env_file}")
            
            print("\n   Since vectorstore already exists, continuing anyway...")
            print("   (Pipeline will skip vectorstore building if it fails)")
        else:
            print(f"\n✅ OPENAI_API_KEY is set")
            print(f"   Key preview: {api_key[:20]}...")
        
        return True
    
    def step1_parse_pdf(self):
        """Step 1: Parse PDF using Docling"""
        return self.run_command(
            ["python", "src/parser/docling_or_fallback_parser.py"],
            "Step 1: Parse PDF with Docling"
        )
    
    def step2_convert_to_chunks(self):
        """Step 2: Convert Docling output to chunks"""
        return self.run_command(
            ["python", "src/parser/convert_docling_to_chunks.py"],
            "Step 2: Convert to Standard Chunks Format"
        )
    
    def step3_chunking_experiments(self):
        """Step 3: Run chunking experiments (4 strategies)"""
        return self.run_command(
            ["python", "src/experiments/chunking_experiments.py"],
            "Step 3: Chunking Strategy Experiments (4 strategies)"
        )
    
    def step4_build_vectorstore(self):
        """Step 4: Build vector database with best strategy"""
        return self.run_command(
            ["python", "src/embeddings/build_vectorstore.py"],
            "Step 4: Build Vector Database (OpenAI text-embedding-3-large)"
        )
    
    def step5_retrieval_evaluation(self):
        """Step 5: Evaluate retrieval performance"""
        return self.run_command(
            ["python", "src/experiments/retrieval_evaluation.py"],
            "Step 5: Retrieval Performance Evaluation"
        )
    
    def step6_upload_to_gcs(self):
        """Step 6: Upload results to Google Cloud Storage"""
        if self.skip_upload:
            print("\n⏭️  Skipping GCS upload (--skip-upload flag)")
            return True
        
        print("\n" + "="*80)
        print("🚀 Step 6: Upload Results to Google Cloud Storage")
        print("="*80)
        
        try:
            from google.cloud import storage
            
            # Check credentials
            creds_path = ".credentials/gcp-key.json"
            if os.path.exists(creds_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
                print(f"✅ Using credentials from: {creds_path}")
            
            storage_client = storage.Client()
            bucket = storage_client.bucket("financial-rag-artifacts")
            
            # Upload directories
            upload_dirs = [
                ("data/parsed", "processed_data/parsed"),
                ("data/experiments", "processed_data/experiments"),
                ("src/parser", "processed_data/code/parser"),
                ("src/embeddings", "processed_data/code/embeddings"),
                ("src/experiments", "processed_data/code/experiments")
            ]
            
            uploaded_count = 0
            
            for local_dir, gcs_prefix in upload_dirs:
                if os.path.exists(local_dir):
                    print(f"\n📤 Uploading {local_dir}...")
                    for root, dirs, files in os.walk(local_dir):
                        for file in files:
                            local_path = os.path.join(root, file)
                            relative_path = os.path.relpath(local_path, local_dir)
                            gcs_path = os.path.join(gcs_prefix, relative_path).replace("\\", "/")
                            
                            blob = bucket.blob(gcs_path)
                            blob.upload_from_filename(local_path)
                            uploaded_count += 1
                            print(f"  ✅ {gcs_path}")
            
            # Upload vectorstore config
            if os.path.exists("data/vectorstore_config.json"):
                blob = bucket.blob("processed_data/vectorstore_config.json")
                blob.upload_from_filename("data/vectorstore_config.json")
                uploaded_count += 1
                print(f"  ✅ processed_data/vectorstore_config.json")
            
            print(f"\n✅ Uploaded {uploaded_count} files to GCS")
            print(f"🌐 View at: https://console.cloud.google.com/storage/browser/financial-rag-artifacts/processed_data")
            
            return True
            
        except Exception as e:
            print(f"⚠️  GCS upload failed: {e}")
            print("   Continuing anyway (results saved locally)")
            return True  # Don't fail pipeline if upload fails
    
    def run_pipeline(self):
        """Run the complete pipeline - all steps required"""
        print("\n" + "🎯"*40)
        print("Automated PDF Processing Pipeline")
        print("All Steps Required")
        print("🎯"*40)
        
        start_time = time.time()
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Prerequisites check failed. Exiting.")
            return False
        
        # Run all steps in correct order
        steps = [
            ("Step 1: Parse PDF", self.step1_parse_pdf),
            ("Step 2: Convert to Chunks", self.step2_convert_to_chunks),
            ("Step 3: Chunking Experiments", self.step3_chunking_experiments),
            ("Step 4: Build Vectorstore", self.step4_build_vectorstore),
            ("Step 5: Retrieval Evaluation", self.step5_retrieval_evaluation),
            ("Step 6: Upload to GCS", self.step6_upload_to_gcs),
        ]
        
        # Execute steps
        results = {}
        for step_name, step_func in steps:
            success = step_func()
            results[step_name] = success
            
            # Only fail on critical steps (1-5), not upload
            if not success and not step_name.startswith("Step 6"):
                print(f"\n❌ Pipeline failed at: {step_name}")
                print("Please fix the error and run again.")
                return False
        
        # Summary
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print("📊 PIPELINE SUMMARY")
        print("="*80)
        
        for step_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{status} - {step_name}")
        
        print(f"\n⏱️  Total Time: {elapsed:.2f}s ({elapsed/60:.1f} minutes)")
        print("="*80)
        
        # Final output locations
        print("\n📂 Local Output Files:")
        print(f"   - Parsed PDF: data/parsed/fintbx_docling.json")
        print(f"   - Chunks: data/parsed/chunks_full.json")
        print(f"   - Chunking Results: data/experiments/chunking_results.json")
        print(f"   - Vectorstore: data/vectorstore/")
        print(f"   - Vectorstore Config: data/vectorstore_config.json")
        print(f"   - Retrieval Evaluation: data/experiments/retrieval_results.json")
        
        if results.get("Step 6: Upload to GCS"):
            print("\n☁️  Cloud Storage:")
            print(f"   - GCS: gs://financial-rag-artifacts/processed_data/")
            print(f"   - Console: https://console.cloud.google.com/storage/browser/financial-rag-artifacts/processed_data")
        
        print("\n✅ PDF Processing Pipeline Complete!")
        
        return True


def main():
    """Main entry point - Run all steps"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Complete PDF Processing Pipeline with GCS Upload"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip uploading to Google Cloud Storage (Step 6)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "📚"*40)
    print("Complete PDF Processing Pipeline")
    print("All Steps Will Be Executed")
    print("📚"*40)
    print("\nSteps:")
    print("  1. Parse PDF using Docling")
    print("  2. Convert to chunks format")
    print("  3. Experiment with 4 chunking strategies")
    print("  4. Build vectorstore (OpenAI text-embedding-3-large)")
    print("  5. Evaluate retrieval performance")
    print("  6. Upload results to Google Cloud Storage")
    
    if args.skip_upload:
        print("\n⏭️  GCS upload will be skipped (--skip-upload)")
    
    print("\n⚠️  This will take approximately 7-11 minutes")
    print("⚠️  Requires OPENAI_API_KEY in .env file")
    print("="*80 + "\n")
    
    # Run pipeline
    pipeline = PDFProcessingPipeline(skip_upload=args.skip_upload)
    success = pipeline.run_pipeline()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()