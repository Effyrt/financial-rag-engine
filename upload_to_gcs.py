"""
Upload PDF processing results to Google Cloud Storage
Run this from project root: python upload_to_gcs.py
"""

from google.cloud import storage
import os

# Auto-detect credentials file
CREDENTIALS_PATH = ".credentials/gcp-key.json"
if os.path.exists(CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    print(f"✅ Using credentials from: {CREDENTIALS_PATH}\n")

BUCKET_NAME = "financial-rag-artifacts"

def upload_directory(local_dir, gcs_prefix):
    """Upload entire directory to GCS"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    uploaded_files = []
    
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            gcs_path = os.path.join(gcs_prefix, relative_path).replace("\\", "/")
            
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
            uploaded_files.append(gcs_path)
            print(f"  ✅ Uploaded: {gcs_path}")
    
    return uploaded_files

def upload_processing_results():
    """Upload all PDF processing results to GCS"""
    
    print("=" * 60)
    print("📤 Uploading Processing Results to GCS")
    print("=" * 60)
    
    # Upload parsed data
    print("\n1️⃣ Uploading parsed data...")
    upload_directory("data/parsed", "processed_data/parsed")
    
    # Upload experiments
    print("\n2️⃣ Uploading experiment results...")
    upload_directory("data/experiments", "processed_data/experiments")
    
    # Upload vectorstore config
    print("\n3️⃣ Uploading vectorstore config...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    if os.path.exists("data/vectorstore_config.json"):
        blob = bucket.blob("processed_data/vectorstore_config.json")
        blob.upload_from_filename("data/vectorstore_config.json")
        print(f"  ✅ Uploaded: processed_data/vectorstore_config.json")
    
    # Upload source code (for reference)
    print("\n4️⃣ Uploading source code...")
    for script in ["src/parser", "src/embeddings", "src/experiments"]:
        if os.path.exists(script):
            upload_directory(script, f"processed_data/code/{os.path.basename(script)}")
    
    print("\n" + "=" * 60)
    print("✅ Results Successfully Uploaded!")
    print("=" * 60)
    print(f"\n📂 View in GCS Console:")
    print(f"https://console.cloud.google.com/storage/browser/{BUCKET_NAME}/processed_data")
    print(f"\n💡 Files available at:")
    print(f"gs://{BUCKET_NAME}/processed_data/")
    print(f"  - parsed/chunks_full.json")
    print(f"  - experiments/chunking_results.json")
    print(f"  - experiments/retrieval_metrics.json")

if __name__ == "__main__":
    try:
        upload_processing_results()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you:")
        print("1. Are in the project root directory")
        print("2. Have Google Cloud credentials configured")
        print("   Run: gcloud auth application-default login")
        print("3. Have access to the GCS bucket")