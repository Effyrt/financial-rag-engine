# Financial RAG Engine

Cloud-deployed Retrieval-Augmented Generation system for financial concept queries, built with Airflow, FastAPI, and Streamlit on GCP.

## 🌐 Live Deployment

| Service | URL | Purpose |
|---------|-----|---------|
| **Streamlit Frontend** | https://financial-rag-frontend-387661610307.us-central1.run.app | User interface |
| **FastAPI Backend** | https://financial-rag-api-387661610307.us-central1.run.app/docs | REST API |
| **Cloud Storage** | gs://financial-rag-artifacts/ | Data artifacts |
| **Airflow** | Cloud Composer | Workflow orchestration |

## 🎥 Demo Video
Watch the complete pipeline in action: [Financial RAG Engine Demo](https://northeastern-my.sharepoint.com/personal/chen_peiyi_northeastern_edu/_layouts/15/stream.aspx?id=%2Fpersonal%2Fchen%5Fpeiyi%5Fnortheastern%5Fedu%2FDocuments%2FRecordings%2FMeeting%20with%20Pei%2DYing%20Chen%2D20251024%5F235257%2DMeeting%20Recording%2Emp4&ga=1&referrer=StreamWebApp%2EWeb&referrerScenario=AddressBarCopied%2Eview%2Eec696149%2Db3b3%2D4ed4%2Da2af%2D7e2f8d041587)

## 📘 Interactive Codelab  
View the full tutorial here:  
👉 [Open Google Codelab](https://codelabs-preview.appspot.com/?file_id=https://raw.githubusercontent.com/Effyrt/financial-rag-engine/main/financial-rag-engine_codelabs.md#0)

## 🏗️ Architecture

```
User → Streamlit → FastAPI → ChromaDB (Vector Store)
                       ↓
                  PostgreSQL (Cache)
                       ↓
                  Wikipedia (Fallback)
       
Airflow DAGs → Automated Updates
```

## 📦 Components

### PDF Processing Pipeline
**Automated 6-step pipeline** (`pipeline_parse_chunck_vectorstore.py`):
1. Parse PDF with Docling
2. Convert to chunks (31 pages)
3. Experiment with 4 chunking strategies
4. Build vectorstore with optimal strategy
5. Evaluate retrieval performance
6. Upload to GCS

**Best Strategy:** Medium Chunks (1000 chars, 200 overlap)
- Precision@3: 0.933
- MRR: 1.0
- Total: 122 chunks

### Airflow DAGs (Cloud Composer)
- `fintbx_ingest_dag`: Weekly PDF processing
- `concept_seed_dag`: On-demand concept seeding

### FastAPI Backend (Cloud Run)
**Endpoints:**
- `POST /query`: Query concepts with automatic caching
- `POST /seed`: Batch pre-generate notes

**Features:**
- ChromaDB vector search
- Wikipedia fallback
- PostgreSQL caching
- Structured JSON responses

### Streamlit Frontend (Cloud Run)
**Features:**
- Concept query interface
- Cache status indicators
- Source tracking (textbook vs Wikipedia)
- Search history
- PDF section references

### Evaluation & Benchmarking
**Quality Metrics:**
- Accuracy: 100%
- Completeness: 100%
- Citation Fidelity: 100%

**Performance:**
- Embedding Cost: $0.0222 (342 chunks)
- Retrieval Success: 100%
- Model: text-embedding-3-large 

## 📊 Key Results
## 🎯 Chosen Strategy: **Medium Chunks**

---

## 📊 Experimental Results

### Strategy Comparison

| Strategy | Chunks | Precision@3 | Recall@3 | MRR | Avg Time |
|----------|--------|-------------|----------|-----|----------|
| Small (500) | 225 | 0.867 | 1.30 | 1.00 | 0.76s |
| **Medium (1000)** | **118** | **0.933** | **1.40** | **1.00** | **0.56s** |
| Large (2000) | 65 | 0.933 | 1.40 | 0.90 | 0.95s |
| Paragraph | 115 | 0.933 | 1.40 | 1.00 | 0.32s |

**Testing**: 5 queries evaluated across 4 strategies using text-embedding-3-large

---

## 💡 Justification

### Quantitative Evidence

**1. Highest Precision (93.3%)**
- 6.6% better than Small Chunks (86.7%)
- 93 out of 100 retrieved results are relevant
- Minimizes noise in search results

**2. Best Recall (1.40)**
- Retrieves all relevant documents plus additional context
- Tied for highest with Large and Paragraph strategies
- Ensures comprehensive information coverage

**3. Perfect MRR (1.0)**
- Most relevant document always ranks first
- Outperforms Large Chunks (MRR = 0.9)
- Critical for user experience

**4. Optimal Speed (0.56s)**
- 26% faster than Small (0.76s)
- 41% faster than Large (0.95s)
- Acceptable for real-time applications

**5. Balanced Chunk Count (118)**
- Not over-fragmented (vs 225 for Small)
- Not too coarse (vs 65 for Large)
- Optimal for processing efficiency

---

## 📖 Concrete Examples

### Example 1: Product Overview Query

**Query**: "What is Financial Toolbox?"

**Medium Chunks Result**:
```
[1] Similarity: 0.572 | Page 28 | Product Description
    "Financial Toolbox Product Description
     Analyze financial data and develop financial models
     Financial Toolbox provides functions for mathematical modeling
     and statistical analysis of financial data..."
```

**Why Medium Works**:
- Complete product description in one chunk
- 791 chars average provides sufficient context
- Not fragmented like Small (would split across 2-3 chunks)
- Not diluted like Large (would mix with installation info)

---

### Example 2: Technical Implementation

**Query**: "Matrix operations"

**Medium Chunks Result**:
```
[1] Similarity: 0.051 | Page 33 | Matrix Algebra 💻
    "Matrix Algebra Refresher
     
     Introduction
     The explanations use MATLAB matrix operations.
     
     Adding and Subtracting Matrices
     Matrix addition operates element-by-element:
     A = [1 2; 3 4];
     B = [5 6; 7 8];
     C = A + B..."
```

**Why Medium Works**:
- Preserves complete code examples (intro + code + explanation)
- 1000 chars captures full instructional flow
- Code blocks remain intact and executable
- Not split mid-example like Small Chunks

---

### Example 3: Domain Concept

**Query**: "Portfolio optimization"

**Medium Chunks Result**:
```
[1] Similarity: 0.163 | Page 7 | Analyzing Portfolios 📊
    "Analyzing Portfolios
     - Portfolio Optimization Against a Benchmark
     - Obtaining Efficient Portfolios for Target Risks
     - Mean-Variance Portfolio Optimization
     [Table: Related functions and page references]"
```

**Why Medium Works**:
- Groups related concepts together
- Table of contents stays with section header
- Maintains logical document structure
- Links subsections appropriately

---

## 🔬 Comparison with Alternatives

### vs. Small Chunks (500)
```diff
+ Precision: 93.3% vs 86.7% (+6.6%)
+ Recall: 1.40 vs 1.30 (+7.7%)
+ Speed: 0.56s vs 0.76s (26% faster)
+ Fewer chunks: 118 vs 225 (48% reduction)
- MRR: 1.00 (tied)
```
**Verdict**: Medium significantly outperforms Small

### vs. Large Chunks (2000)
```diff
+ MRR: 1.00 vs 0.90 (better ranking)
+ Speed: 0.56s vs 0.95s (41% faster)
+ More granular: 118 vs 65 chunks
- Precision: 93.3% (tied)
- Recall: 1.40 (tied)
```
**Verdict**: Medium provides better ranking and speed

### vs. Paragraph-focused
```diff
- Speed: 0.56s vs 0.32s (Paragraph faster)
+ More predictable chunk sizes
+ Better for production consistency
- Precision: 93.3% (tied)
- Recall: 1.40 (tied)
- MRR: 1.00 (tied)
```
**Verdict**: Medium chosen for predictability; Paragraph is valid alternative

### Chunking Strategy Comparison

| Strategy | Size | Chunks | Precision@3 | MRR | Selected |
|----------|------|--------|-------------|-----|----------|
| Small | 500 | 225 | 0.867 | 1.0 | ❌ |
| **Medium** | **1000** | **118** | **0.933** | **1.0** | **✅** |
| Large | 2000 | 65 | 0.933 | 0.9 | ❌ |
| Paragraph | 1000 | 116 | 0.867 | 1.0 | ❌ |

**Selection Rationale:** Strategy 2 achieves highest precision (0.933) with perfect MRR (1.0), providing optimal balance between accuracy and context preservation.

## 📁 Project Structure

```
financial-rag-engine/
├── pipeline_parse_chunck_vectorstore.py  # Automated pipeline
├── src/
│   ├── parser/              # PDF parsing
│   ├── embeddings/          # Vectorstore building
│   └── experiments/         # Chunking & evaluation
├── dags/                    # Airflow DAGs
├── fastapi_rag_service/     # Backend API
├── streamlit-app/           # Frontend UI
├── data/
│   ├── parsed/              # Processing results
│   ├── experiments/         # Experiment results
│   ├── evaluation/          # Benchmark results
│   └── vectorstore/         # ChromaDB database
└── upload_to_gcs.py         # GCS upload utility
```

## 🔧 Prerequisites

```bash

# Environment variables (.env)
OPENAI_API_KEY=your-key
GOOGLE_APPLICATION_CREDENTIALS=.credentials/gcp-key.json


```

## 📈 Technologies

- **PDF Parsing**: Docling
- **Chunking**: LangChain RecursiveCharacterTextSplitter
- **Embeddings**: OpenAI text-embedding-3-large 
- **Vector Store**: ChromaDB
- **Orchestration**: Apache Airflow (Cloud Composer)
- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Cloud**: GCP (Cloud Run, Cloud Composer, Cloud Storage)



>>>>>>> f092f74ad9fe531cccd2aee5ce897fcfddc11d8f
