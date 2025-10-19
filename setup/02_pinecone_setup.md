# Phase 0.2: Pinecone Vector Database Setup

**Duration:** 30-45 minutes  
**Prerequisites:** Pinecone account (free tier available)

---

## Overview

Configure Pinecone as the vector database for storing and querying document embeddings.

## Tasks

### 1. Create Pinecone Account

1. Visit [https://www.pinecone.io/](https://www.pinecone.io/)
2. Sign up for a free account
3. Verify your email address
4. Log in to the Pinecone console

### 2. Get API Key

```bash
# In Pinecone Console:
# 1. Navigate to "API Keys" section
# 2. Copy your API key
# 3. Note your environment (e.g., us-central1-gcp)

# Add to .env file
cat >> .env << 'EOF'
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-central1-gcp
PINECONE_INDEX_NAME=financial-concepts
EOF
```

### 3. Install Pinecone Client (Local Testing)

```bash
# Activate virtual environment
source venv/bin/activate

# Install Pinecone
pip install pinecone-client==3.0.0

# Update requirements.txt
echo "pinecone-client==3.0.0" >> requirements.txt
```

### 4. Create Pinecone Index

Create a Python script to initialize the index:

```python
# scripts/create_pinecone_index.py
import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Index configuration
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "financial-concepts")
DIMENSION = 3072  # OpenAI text-embedding-3-large dimension
METRIC = "cosine"

# Create index
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric=METRIC,
        spec=ServerlessSpec(
            cloud="gcp",
            region="us-central1"
        )
    )
    print(f"✅ Index '{INDEX_NAME}' created successfully!")
else:
    print(f"ℹ️  Index '{INDEX_NAME}' already exists")

# Get index stats
index = pc.Index(INDEX_NAME)
stats = index.describe_index_stats()
print(f"\nIndex Stats:")
print(f"  Dimension: {stats.dimension}")
print(f"  Total vectors: {stats.total_vector_count}")
print(f"  Namespaces: {stats.namespaces}")
```

Run the script:

```bash
# Create scripts directory if it doesn't exist
mkdir -p scripts

# Run the index creation script
python scripts/create_pinecone_index.py
```

### 5. Test Pinecone Connection

Create a test script:

```python
# scripts/test_pinecone.py
import os
from pinecone import Pinecone
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Initialize
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# Create test vectors
test_vectors = [
    {
        "id": "test-1",
        "values": np.random.rand(3072).tolist(),
        "metadata": {
            "text": "Test document 1",
            "source": "test"
        }
    },
    {
        "id": "test-2",
        "values": np.random.rand(3072).tolist(),
        "metadata": {
            "text": "Test document 2",
            "source": "test"
        }
    }
]

# Upsert test vectors
print("Upserting test vectors...")
index.upsert(vectors=test_vectors)

# Query
print("Querying index...")
query_vector = np.random.rand(3072).tolist()
results = index.query(
    vector=query_vector,
    top_k=2,
    include_metadata=True
)

print(f"\n✅ Query successful!")
print(f"Found {len(results.matches)} matches")
for match in results.matches:
    print(f"  - ID: {match.id}, Score: {match.score:.4f}")

# Clean up test vectors
print("\nCleaning up test vectors...")
index.delete(ids=["test-1", "test-2"])

print("\n✅ Pinecone connection test passed!")
```

Run the test:

```bash
python scripts/test_pinecone.py
```

### 6. Configure Index Metadata

Set up metadata filtering capabilities:

```python
# scripts/configure_pinecone_metadata.py
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# Define metadata schema (for documentation purposes)
METADATA_SCHEMA = {
    "chunk_id": "string",          # Unique chunk identifier
    "source_file": "string",       # Source PDF filename
    "page_number": "integer",      # Page number in PDF
    "chunk_text": "string",        # Original text content
    "chunk_size": "integer",       # Number of tokens
    "section": "string",           # Document section
    "created_at": "string"         # ISO timestamp
}

print("Metadata Schema:")
for field, dtype in METADATA_SCHEMA.items():
    print(f"  - {field}: {dtype}")

print("\n✅ Metadata schema documented")
print("Note: Pinecone automatically indexes all metadata fields")
```

### 7. Set Up Monitoring

```python
# scripts/monitor_pinecone.py
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# Get detailed stats
stats = index.describe_index_stats()

print("📊 Pinecone Index Statistics")
print("=" * 50)
print(f"Index Name: {os.getenv('PINECONE_INDEX_NAME')}")
print(f"Dimension: {stats.dimension}")
print(f"Total Vectors: {stats.total_vector_count:,}")
print(f"Index Fullness: {stats.index_fullness:.2%}")
print(f"\nNamespaces:")
for ns, ns_stats in stats.namespaces.items():
    print(f"  - {ns}: {ns_stats.vector_count:,} vectors")
```

## Verification Checklist

- [ ] Pinecone account created
- [ ] API key obtained and added to `.env`
- [ ] Pinecone client installed locally
- [ ] Index created with correct dimensions (3072)
- [ ] Index uses cosine similarity metric
- [ ] Index is in GCP us-central1 region
- [ ] Connection test passed
- [ ] Can upsert and query vectors
- [ ] Metadata schema documented

## Index Configuration Summary

```yaml
Index Name: financial-concepts
Dimension: 3072
Metric: cosine
Cloud: GCP
Region: us-central1
Tier: Serverless (Free/Paid)
```

## Troubleshooting

### Issue: API key not working
```python
# Verify API key format
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("PINECONE_API_KEY")
print(f"API Key length: {len(api_key)}")
print(f"API Key starts with: {api_key[:8]}...")
```

### Issue: Index creation fails
```bash
# Check if index already exists
python -c "
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
print('Existing indexes:', pc.list_indexes().names())
"
```

### Issue: Dimension mismatch
- Ensure you're using `text-embedding-3-large` (3072 dimensions)
- If using `text-embedding-3-small`, dimension should be 1536
- Recreate index if dimension is wrong

## Cost Estimates

**Free Tier:**
- 1 index
- Up to 100,000 vectors
- Serverless architecture
- No credit card required initially

**Paid Tier (if needed):**
- $0.096 per million read units
- $0.12 per million write units
- Storage: ~$0.25/GB/month

**Estimated cost for this project:** $0-20/month

## Performance Optimization Tips

1. **Batch Upserts:** Upload vectors in batches of 100-200
2. **Namespaces:** Use namespaces to organize vectors by source
3. **Metadata Filtering:** Pre-filter by metadata before vector search
4. **Top-K Tuning:** Start with top_k=5, adjust based on results

## Next Steps

Proceed to `03_composer_setup.md` to set up Cloud Composer (Airflow).

## Resources

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Pinecone Python Client](https://github.com/pinecone-io/pinecone-python-client)
- [Vector Database Best Practices](https://www.pinecone.io/learn/vector-database/)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

