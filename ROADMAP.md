# Financial RAG Engine - Development Roadmap

**Project:** AURELIA - Automated Financial Concept Note Generator  
**Course:** DAMG 7245 - Document Analysis & Mining  
**Duration:** 5 Weeks  
**Status:** 🚧 In Progress

---

## 📊 Overall Progress

```
Phase 0: Infrastructure Setup       [ ] 0/35 tasks
Phase 1: PDF Corpus Construction    [ ] 0/42 tasks
Phase 2: Orchestration Pipeline     [ ] 0/38 tasks
Phase 3: FastAPI RAG Service        [ ] 0/45 tasks
Phase 4: Streamlit Frontend         [ ] 0/32 tasks
Phase 5: Evaluation & Deployment    [ ] 0/28 tasks
---------------------------------------------------
Total Progress:                     [ ] 0/220 tasks (0%)
```

---

## 🎯 Phase 0: Infrastructure Setup (Week 1)

**Goal:** Set up all cloud infrastructure and development environment  
**Status:** ⏳ Not Started  
**Duration:** 3-4 days

### 0.1 GCP Project Setup (Follow: `setup/01_gcp_setup.md`)
- [ ] Set project variables (PROJECT_ID, PROJECT_NAME, BILLING_ACCOUNT_ID)
- [ ] Create GCP project using gcloud CLI
- [ ] Link billing account to project
- [ ] Set project as default in gcloud config
- [ ] Enable Composer API
- [ ] Enable Cloud Run API
- [ ] Enable Cloud SQL Admin API
- [ ] Enable Cloud Storage APIs
- [ ] Enable IAM and Resource Manager APIs
- [ ] Verify all APIs are enabled

### 0.2 Service Account & IAM
- [ ] Create service account: `financial-rag-sa`
- [ ] Grant `roles/composer.worker` role
- [ ] Grant `roles/storage.objectAdmin` role
- [ ] Grant `roles/cloudsql.client` role
- [ ] Create and download service account key JSON
- [ ] Store key securely in project root
- [ ] Add key path to `.env` file
- [ ] Test service account authentication

### 0.3 Cloud Storage Setup
- [ ] Set GCP_REGION variable (us-central1)
- [ ] Create bucket: `${PROJECT_ID}-raw-pdfs`
- [ ] Create bucket: `${PROJECT_ID}-processed`
- [ ] Create bucket: `${PROJECT_ID}-airflow-dags`
- [ ] Configure bucket lifecycle rules (90-day deletion)
- [ ] Test bucket write permissions
- [ ] Test bucket read permissions
- [ ] Add bucket names to `.env` file

### 0.4 Budget & Cost Management
- [ ] Create budget alert at 50% threshold
- [ ] Create budget alert at 90% threshold
- [ ] Create budget alert at 100% threshold
- [ ] Set up billing export to BigQuery (optional)
- [ ] Document expected monthly costs

### 0.5 Pinecone Setup (Follow: `setup/02_pinecone_setup.md`)
- [ ] Sign up for Pinecone account (free tier)
- [ ] Get Pinecone API key from console
- [ ] Note Pinecone environment (us-central1-gcp)
- [ ] Add Pinecone credentials to `.env`
- [ ] Install pinecone-client package
- [ ] Create `scripts/create_pinecone_index.py`
- [ ] Run index creation script
- [ ] Verify index created with correct dimensions (3072)
- [ ] Verify index uses cosine metric
- [ ] Create `scripts/test_pinecone.py`
- [ ] Run Pinecone connection test
- [ ] Verify upsert operations work
- [ ] Verify query operations work
- [ ] Clean up test vectors
- [ ] Document metadata schema

### 0.6 Cloud Composer Setup (Follow: `setup/03_composer_setup.md`)
- [ ] Set Composer environment variables
- [ ] Create Composer environment (takes 20-30 min)
- [ ] Wait for environment to reach RUNNING state
- [ ] Get Airflow web UI URL
- [ ] Get DAGs bucket path
- [ ] Add Composer details to `.env`
- [ ] Upload `composer_requirements.txt`
- [ ] Wait for dependencies to install
- [ ] Set Airflow variable: `gcp_project_id`
- [ ] Set Airflow variable: `gcs_raw_bucket`
- [ ] Set Airflow variable: `gcs_processed_bucket`
- [ ] Create Airflow connection: `openai_default`
- [ ] Create Airflow connection: `pinecone_default`
- [ ] Create test DAG file
- [ ] Upload test DAG to Composer
- [ ] Trigger test DAG
- [ ] Verify test DAG runs successfully
- [ ] Access Airflow web UI
- [ ] Configure Airflow settings (disable examples, etc.)

### 0.7 Docling Testing (Follow: `setup/04_docling_test.md`)
- [ ] Install Docling package
- [ ] Install Docling-core package
- [ ] Verify fintbx.pdf exists in `data/raw/`
- [ ] Create `scripts/test_docling_basic.py`
- [ ] Run basic parsing test
- [ ] Verify markdown output generated
- [ ] Verify JSON output generated
- [ ] Review first page preview
- [ ] Create `scripts/test_docling_advanced.py`
- [ ] Run advanced parsing test
- [ ] Analyze element types found
- [ ] Count tables extracted
- [ ] Count formulas/equations found
- [ ] Count headings/sections
- [ ] Save analysis results
- [ ] Create `scripts/test_chunking.py`
- [ ] Test chunk size: 500 with 50 overlap
- [ ] Test chunk size: 1000 with 100 overlap
- [ ] Test chunk size: 1500 with 150 overlap
- [ ] Compare chunking strategies
- [ ] Create `scripts/generate_parsing_report.py`
- [ ] Generate comprehensive parsing report
- [ ] Review parsing quality
- [ ] Select optimal chunking strategy
- [ ] Document any parsing limitations

---

## 📚 Phase 1: PDF Corpus Construction (Week 1-2)

**Goal:** Parse PDF, create chunks, generate embeddings, populate vector store  
**Status:** ⏳ Not Started  
**Duration:** 5-7 days

### 1.1 PDF Acquisition & Upload
- [ ] Verify fintbx.pdf exists in project root
- [ ] Check PDF file size and page count
- [ ] Upload PDF to GCS: `gsutil cp fintbx.pdf gs://[project]-raw-pdfs/`
- [ ] Verify upload with `gsutil ls`
- [ ] Test download from GCS
- [ ] Document PDF metadata (version, pages, size)

### 1.2 PDF Parser Module Development
- [ ] Create `pipeline/__init__.py` with module docstring
- [ ] Create `pipeline/pdf_parser.py`
- [ ] Add type hints and imports
- [ ] Implement `PDFParser` class
- [ ] Add `__init__` method with configuration
- [ ] Implement `parse_pdf()` method using Docling
- [ ] Add error handling for corrupted PDFs
- [ ] Implement `extract_text()` method
- [ ] Implement `extract_tables()` method
- [ ] Implement `extract_metadata()` method
- [ ] Add logging throughout parser
- [ ] Create `save_to_json()` method
- [ ] Create `save_to_markdown()` method
- [ ] Write unit tests for parser
- [ ] Test with fintbx.pdf
- [ ] Document parser API

### 1.3 Chunking Module Development
- [ ] Create `pipeline/chunker.py`
- [ ] Import LangChain text splitters
- [ ] Implement `TextChunker` class
- [ ] Add configuration for chunk size and overlap
- [ ] Implement `chunk_text()` method
- [ ] Add chunk ID generation
- [ ] Implement `chunk_with_metadata()` method
- [ ] Add page number tracking
- [ ] Implement `validate_chunks()` method
- [ ] Create chunk statistics calculator
- [ ] Write unit tests for chunker
- [ ] Test with sample text

### 1.4 Chunking Strategy Experiments
- [ ] Create `notebooks/02_chunking_experiments.ipynb`
- [ ] Load parsed PDF content
- [ ] Test strategy 1: 500 chars, 50 overlap
- [ ] Calculate metrics for strategy 1
- [ ] Test strategy 2: 1000 chars, 100 overlap
- [ ] Calculate metrics for strategy 2
- [ ] Test strategy 3: 1500 chars, 150 overlap
- [ ] Calculate metrics for strategy 3
- [ ] Compare chunk distributions
- [ ] Analyze chunk coherence
- [ ] Check for split sentences/paragraphs
- [ ] Select optimal strategy
- [ ] Document decision rationale
- [ ] Save optimal configuration

### 1.5 Embedding Module Development
- [ ] Create `pipeline/embedder.py`
- [ ] Import OpenAI client
- [ ] Implement `EmbeddingGenerator` class
- [ ] Add OpenAI API key configuration
- [ ] Implement `generate_embedding()` for single text
- [ ] Implement `generate_embeddings_batch()` for multiple texts
- [ ] Add batch size configuration (100 texts)
- [ ] Implement retry logic with exponential backoff
- [ ] Add rate limiting (requests per minute)
- [ ] Implement progress bar with tqdm
- [ ] Add cost estimation calculator
- [ ] Log API calls and costs
- [ ] Write unit tests for embedder
- [ ] Test with sample chunks
- [ ] Verify embedding dimensions (3072)

### 1.6 Vector Store Module Development
- [ ] Create `pipeline/vector_store.py`
- [ ] Import Pinecone client
- [ ] Implement `VectorStore` class
- [ ] Add Pinecone connection initialization
- [ ] Implement `upsert_vectors()` method
- [ ] Add metadata schema validation
- [ ] Implement batch upsert (100 vectors)
- [ ] Add progress tracking
- [ ] Implement `query_vectors()` method
- [ ] Add `delete_vectors()` method
- [ ] Implement `get_index_stats()` method
- [ ] Add error handling for network issues
- [ ] Write unit tests for vector store
- [ ] Test upsert operations
- [ ] Test query operations
- [ ] Verify metadata is stored correctly

### 1.7 End-to-End Pipeline Integration
- [ ] Create `pipeline/main.py`
- [ ] Import all pipeline modules
- [ ] Implement `FinancialRAGPipeline` class
- [ ] Add configuration management
- [ ] Implement `run_full_pipeline()` method
- [ ] Add stage 1: PDF parsing
- [ ] Add stage 2: Text chunking
- [ ] Add stage 3: Embedding generation
- [ ] Add stage 4: Vector store upload
- [ ] Add progress tracking between stages
- [ ] Implement checkpoint/resume functionality
- [ ] Add comprehensive logging
- [ ] Create pipeline execution report
- [ ] Write integration tests
- [ ] Run full pipeline with fintbx.pdf
- [ ] Verify all vectors in Pinecone
- [ ] Document execution time
- [ ] Calculate total API costs
- [ ] Create pipeline usage documentation

---

## ⚙️ Phase 2: Orchestration Pipeline (Week 2)

**Goal:** Create Airflow DAGs for automated ingestion and concept seeding  
**Status:** ⏳ Not Started  
**Duration:** 4-5 days

### 2.1 Database Schema Design
- [ ] Create PostgreSQL database in Cloud SQL
- [ ] Apply schema from `database/schema.sql`
- [ ] Create indexes for performance
- [ ] Set up connection pooling
- [ ] Test database connectivity from Composer

### 2.2 Concept Note Data Model
- [ ] Create `backend/app/models/concept.py`
- [ ] Define Pydantic model for ConceptNote:
  ```python
  class ConceptNote(BaseModel):
      title: str
      definition: str
      formula: Optional[str]
      example: Optional[str]
      use_cases: List[str]
      references: List[str]
      source: Literal["PDF", "Wikipedia"]
      metadata: Dict[str, Any]
  ```
- [ ] Implement SQLAlchemy ORM model
- [ ] Create database migration scripts

### 2.3 Instructor Integration
- [ ] Install instructor library: `pip install instructor`
- [ ] Create `backend/app/services/llm_service.py`
- [ ] Implement structured output generation:
  ```python
  def generate_concept_note(concept: str, context: str) -> ConceptNote:
      """Generate structured concept note using instructor."""
  ```
- [ ] Test with sample financial concepts
- [ ] Optimize prompt for financial domain

### 2.4 Airflow DAG: PDF Ingestion
- [ ] Create `airflow/dags/fintbx_ingest_dag.py`
- [ ] Define DAG tasks:
  1. Download PDF from GCS
  2. Parse with Docling
  3. Create chunks
  4. Generate embeddings
  5. Upload to Pinecone
- [ ] Add task dependencies and error handling
- [ ] Configure retry policies
- [ ] Set up email alerts on failure
- [ ] Test DAG in Composer environment

### 2.5 Airflow DAG: Concept Seeding
- [ ] Create `airflow/dags/concept_seed_dag.py`
- [ ] Load concept list from `data/concept_lists/financial_concepts.json`
- [ ] Define DAG tasks:
  1. For each concept:
     - Query Pinecone for relevant chunks
     - Generate concept note with LLM
     - Save to PostgreSQL
- [ ] Implement parallel processing (5 concepts at a time)
- [ ] Add progress tracking
- [ ] Test DAG with subset of concepts

### 2.6 DAG Monitoring & Optimization
- [ ] Set up Airflow monitoring dashboard
- [ ] Configure logging to Cloud Logging
- [ ] Implement cost tracking
- [ ] Optimize DAG performance
- [ ] Document DAG execution schedule

---

## 🚀 Phase 3: FastAPI RAG Service (Week 3)

**Goal:** Build REST API for concept retrieval and generation  
**Status:** ⏳ Not Started  
**Duration:** 5-6 days

### 3.1 FastAPI Project Setup
- [ ] Create `backend/app/main.py` with FastAPI app
- [ ] Set up CORS middleware
- [ ] Configure logging
- [ ] Add health check endpoint: `GET /health`
- [ ] Add API documentation with Swagger UI

### 3.2 Configuration Management
- [ ] Create `backend/app/core/config.py`
- [ ] Load environment variables with Pydantic Settings
- [ ] Implement configuration validation
- [ ] Add secrets management for API keys

### 3.3 Database Connection
- [ ] Create `backend/app/core/database.py`
- [ ] Set up SQLAlchemy engine and session
- [ ] Implement connection pooling
- [ ] Add database health check

### 3.4 Pinecone Service
- [ ] Create `backend/app/services/pinecone_service.py`
- [ ] Implement vector search function:
  ```python
  def search_similar_chunks(query: str, top_k: int = 5) -> List[Dict]:
      """Search Pinecone for relevant chunks."""
  ```
- [ ] Add query embedding generation
- [ ] Implement result filtering and ranking

### 3.5 RAG Service
- [ ] Create `backend/app/services/rag_service.py`
- [ ] Implement RAG pipeline:
  ```python
  def generate_concept_note_from_rag(concept: str) -> ConceptNote:
      """Generate concept note using RAG."""
  ```
- [ ] Combine retrieved chunks into context
- [ ] Generate structured output with instructor
- [ ] Add response caching

### 3.6 Wikipedia Fallback Service
- [ ] Create `backend/app/services/wikipedia_service.py`
- [ ] Implement Wikipedia API integration
- [ ] Create fallback logic:
  ```python
  def get_wikipedia_concept(concept: str) -> ConceptNote:
      """Fetch and structure Wikipedia content."""
  ```
- [ ] Parse Wikipedia content into ConceptNote format

### 3.7 API Endpoints
- [ ] **POST /api/v1/query** - Query for concept note
  - Check database cache first
  - If not found, use RAG
  - If RAG fails, fallback to Wikipedia
  - Save result to database
- [ ] **POST /api/v1/seed** - Manually seed a concept
- [ ] **GET /api/v1/concepts** - List all cached concepts
- [ ] **GET /api/v1/concepts/{title}** - Get specific concept
- [ ] **DELETE /api/v1/concepts/{title}** - Delete concept from cache

### 3.8 Testing & Documentation
- [ ] Create `backend/tests/test_api.py`
- [ ] Write unit tests for all endpoints
- [ ] Write integration tests
- [ ] Test error handling and edge cases
- [ ] Document API with detailed examples

### 3.9 Docker Containerization
- [ ] Build Docker image: `docker build -t financial-rag-api .`
- [ ] Test container locally
- [ ] Optimize image size
- [ ] Add health checks to Dockerfile

### 3.10 Cloud Run Deployment
- [ ] Deploy to Cloud Run
- [ ] Configure environment variables
- [ ] Set up Cloud SQL connection
- [ ] Configure auto-scaling (min: 0, max: 10)
- [ ] Test deployed API

---

## 🎨 Phase 4: Streamlit Frontend (Week 4)

**Goal:** Build user-friendly web interface for concept exploration  
**Status:** ⏳ Not Started  
**Duration:** 4-5 days

### 4.1 Streamlit App Setup
- [ ] Create `frontend/app.py` main application file
- [ ] Configure Streamlit theme and layout
- [ ] Set up page configuration
- [ ] Add custom CSS for styling

### 4.2 API Client
- [ ] Create `frontend/utils/api_client.py`
- [ ] Implement API wrapper functions:
  ```python
  def query_concept(concept: str) -> Dict
  def list_concepts() -> List[Dict]
  def get_concept(title: str) -> Dict
  ```
- [ ] Add error handling and retries
- [ ] Implement loading states

### 4.3 Search Interface
- [ ] Create search bar component
- [ ] Add autocomplete suggestions from cached concepts
- [ ] Implement search button with loading spinner
- [ ] Add search history (session state)

### 4.4 Concept Display Component
- [ ] Create `frontend/components/concept_card.py`
- [ ] Display concept note with sections:
  - Title
  - Definition
  - Formula (with LaTeX rendering)
  - Example
  - Use Cases
  - References
- [ ] Add source indicator badge (PDF/Wikipedia)
- [ ] Implement copy-to-clipboard functionality

### 4.5 Sidebar Features
- [ ] Add "Browse Concepts" list
- [ ] Show recently viewed concepts
- [ ] Add filters (by source, date)
- [ ] Display system statistics

### 4.6 Advanced Features
- [ ] Add concept comparison view (side-by-side)
- [ ] Implement export to PDF/Markdown
- [ ] Add feedback mechanism (thumbs up/down)
- [ ] Create admin panel for cache management

### 4.7 Testing & Polish
- [ ] Test all UI interactions
- [ ] Ensure responsive design
- [ ] Add error messages and user guidance
- [ ] Optimize loading performance

### 4.8 Docker & Deployment
- [ ] Build Docker image: `docker build -t financial-rag-ui .`
- [ ] Test container locally
- [ ] Deploy to Cloud Run
- [ ] Configure custom domain (optional)

---

## 📊 Phase 5: Evaluation & Deployment (Week 5)

**Goal:** Evaluate system quality, optimize, and prepare final deployment  
**Status:** ⏳ Not Started  
**Duration:** 5-7 days

### 5.1 Quality Metrics
- [ ] Create `notebooks/04_evaluation_metrics.ipynb`
- [ ] Define evaluation criteria:
  - Relevance of retrieved chunks
  - Accuracy of generated definitions
  - Completeness of concept notes
  - Response time
- [ ] Implement automated evaluation pipeline
- [ ] Test with 20 sample concepts

### 5.2 Performance Benchmarking
- [ ] Measure end-to-end latency
- [ ] Profile API endpoints
- [ ] Analyze Pinecone query performance
- [ ] Monitor LLM token usage and costs
- [ ] Document performance bottlenecks

### 5.3 Cost Analysis
- [ ] Calculate costs per concept generation:
  - OpenAI API costs (embeddings + completions)
  - Pinecone storage and query costs
  - GCP infrastructure costs
- [ ] Project monthly operational costs
- [ ] Identify cost optimization opportunities

### 5.4 System Optimization
- [ ] Implement response caching
- [ ] Optimize Pinecone queries (adjust top_k)
- [ ] Reduce LLM token usage (prompt optimization)
- [ ] Add rate limiting to API
- [ ] Optimize database queries

### 5.5 Documentation
- [ ] Write comprehensive README.md
- [ ] Create architecture diagrams
- [ ] Document API endpoints with examples
- [ ] Write deployment guide
- [ ] Create user guide for frontend

### 5.6 Testing & Validation
- [ ] Run full end-to-end tests
- [ ] Test with edge cases and unusual concepts
- [ ] Validate Wikipedia fallback
- [ ] Test system under load
- [ ] Fix any discovered bugs

### 5.7 Final Deployment
- [ ] Deploy all services to production
- [ ] Configure monitoring and alerting
- [ ] Set up automated backups
- [ ] Test production environment
- [ ] Create rollback plan

### 5.8 Presentation Preparation
- [ ] Create demo video
- [ ] Prepare presentation slides
- [ ] Document key learnings
- [ ] Prepare Q&A responses

---

## 📝 Status Tracking

### Current Sprint
**Week:** 1  
**Phase:** 0 - Infrastructure Setup  
**Focus:** GCP, Pinecone, Composer setup

### Blockers
- None currently

### Risks
- Docling parsing quality for complex financial formulas
- OpenAI API rate limits during bulk embedding generation
- Pinecone query performance with large vector store
- Cost management for API usage

### Next Actions
1. Create GCP project and enable APIs
2. Sign up for Pinecone and create index
3. Test Docling with sample financial PDF
4. Set up Cloud Composer environment

---

## 🎯 Success Criteria

### Technical Requirements
- ✅ PDF parsing accuracy > 95%
- ✅ RAG retrieval relevance > 80%
- ✅ API response time < 5 seconds
- ✅ System uptime > 99%
- ✅ Test coverage > 80%

### Business Requirements
- ✅ Generate accurate concept notes for 20+ financial terms
- ✅ Wikipedia fallback working for non-PDF concepts
- ✅ User-friendly interface with <3 clicks to result
- ✅ Cost per concept generation < $0.10

### Academic Requirements
- ✅ Demonstrate advanced RAG techniques
- ✅ Show production-grade cloud deployment
- ✅ Document all design decisions
- ✅ Present comprehensive evaluation

---

## 📚 Resources

### Documentation
- [Docling Documentation](https://github.com/DS4SD/docling)
- [LangChain Docs](https://python.langchain.com/)
- [Pinecone Docs](https://docs.pinecone.io/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Streamlit Docs](https://docs.streamlit.io/)

### Tutorials
- [Building RAG Systems](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [Cloud Composer Guide](https://cloud.google.com/composer/docs)
- [Instructor Library](https://python.useinstructor.com/)

### Course Materials
- DAMG 7245 Lecture Notes
- Lab Assignment Guidelines
- Project Rubric

---

## 🔄 Change Log

| Date | Phase | Change | Reason |
|------|-------|--------|--------|
| 2025-10-19 | - | Initial roadmap created | Project kickoff |

---

**Last Updated:** 2025-10-19  
**Next Review:** 2025-10-26

