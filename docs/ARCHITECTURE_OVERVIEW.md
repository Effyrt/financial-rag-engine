# 🏗️ Financial RAG Engine - Complete Architecture & Workflow

## 🎯 System Overview

**AURELIA** - Automated Financial Concept Note Generator
- **Purpose**: Generate standardized financial concept notes using RAG
- **Input**: Financial Toolbox User's Guide (fintbx.pdf) - 3,462 pages
- **Output**: Structured concept notes with source attribution
- **Architecture**: Cloud-native, microservices-based RAG system

---

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FINANCIAL RAG ENGINE (AURELIA)                        │
│                              Google Cloud Platform                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD INFRASTRUCTURE                              │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   DATA LAYER    │  │  PROCESSING     │  │   SERVICES      │  │   USERS     │ │
│  │                 │  │     LAYER       │  │     LAYER      │  │             │ │
│  │ • Cloud Storage │  │ • Cloud Composer│  │ • FastAPI      │  │ • Streamlit │ │
│  │ • ChromaDB      │  │ • Cloud Run Jobs│  │ • Streamlit    │  │ • Gradio    │ │
│  │ • Cloud SQL     │  │ • Vertex AI     │  │ • Gradio       │  │ • REST API  │ │
│  │ • Secret Manager│  │ • Document AI   │  │                │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Data Flow Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   PDF Input │───▶│  Document AI  │───▶│  Chunking   │───▶│ Embeddings  │
│ (fintbx.pdf)│    │   (Docling)  │    │ (LangChain) │    │  (OpenAI)   │
│  3,462 pages│    │ + Vertex AI   │    │ 7 Strategies│    │ 3072-dim    │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                                                                    │
                                                                    ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   User      │◀───│   RAG Query   │◀───│  Vector     │◀───│  ChromaDB   │
│ Interface   │    │   Service     │    │  Search     │    │   Store     │
│ (Multi-UI)  │    │ (FastAPI)     │    │ (Similarity)│    │ (Persistent)│
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

---

## 🧩 Component Architecture

### **1. Data Processing Pipeline**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PDF PROCESSING PIPELINE                             │
│                                                                                 │
│  PDF Input ──▶ Document AI ──▶ Text Extraction ──▶ Chunking ──▶ Embeddings     │
│     │              │              │                │           │               │
│     │              │              │                │           │               │
│     ▼              ▼              ▼                ▼           ▼               │
│  fintbx.pdf    Docling +      Raw Text       7 Strategies   OpenAI           │
│  3,462 pages   Vertex AI      Tables         semantic_1200   text-embedding   │
│                Images          Formulas       150 (winner)   3-large (3072d)  │
│                Metadata        Structure      81.1% optimal                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### **2. Chunking Strategy System**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CHUNKING STRATEGIES                               │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Recursive     │  │   Semantic      │  │  Heading-Aware  │  │   Hybrid    │ │
│  │   (3 variants)  │  │   (WINNER)      │  │                 │  │             │ │
│  │                 │  │                 │  │                 │  │             │ │
│  │ • 1000/100      │  │ • 1200/150      │  │ • 1000/100      │  │ • 1000/100  │ │
│  │ • 1500/200      │  │ • 81.1% optimal │  │ • Structure     │  │ • All-in-1  │ │
│  │ • 500/50        │  │ • Best for RAG  │  │ • Hierarchy     │  │ • Flexible  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Code-Aware    │  │   Evaluator     │  │   Optimizer     │                │
│  │                 │  │                 │  │                 │                │
│  │ • Code blocks   │  │ • Metrics       │  │ • Auto-select   │                │
│  │ • Syntax        │  │ • Comparison    │  │ • Performance   │                │
│  │ • Languages     │  │ • Quality       │  │ • Tuning        │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### **3. Vector Database & Retrieval**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VECTOR STORE SYSTEM                               │
│                                                                                 │
│  Embeddings ──▶ ChromaDB ──▶ Indexing ──▶ Similarity Search ──▶ Retrieval     │
│      │              │           │              │                  │            │
│      │              │           │              │                  │            │
│      ▼              ▼           ▼              ▼                  ▼            │
│  3072-dim      Collections    Metadata      Cosine Sim      Top-K Results    │
│  Vectors       Namespaces     Filtering     Distance        Ranking          │
│  OpenAI        Persistent     Versioning     Threshold       Context         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### **4. RAG Service Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG SERVICE LAYER                                 │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Query Input   │  │   Retrieval    │  │   Generation    │  │   Output    │ │
│  │                 │  │                 │  │                 │  │             │ │
│  │ • User Query    │  │ • Vector Search │  │ • LLM Prompt    │  │ • Concept   │ │
│  │ • Context       │  │ • Similarity    │  │ • Context       │  │   Note      │ │
│  │ • Filters       │  │ • Ranking       │  │ • Instructions  │  │ • Sources   │ │
│  │ • Parameters    │  │ • Top-K         │  │ • Templates     │  │ • Metadata  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Fallback      │  │   Caching       │  │   Validation    │                │
│  │                 │  │                 │  │                 │                │
│  │ • Wikipedia     │  │ • PostgreSQL    │  │ • Pydantic      │                │
│  │ • External      │  │ • Redis         │  │ • Instructor    │                │
│  │ • APIs          │  │ • Memory        │  │ • Structure     │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Complete Workflow Steps

### **Phase 1: Data Ingestion & Processing**

```
Step 1: PDF Upload & Storage
├── Upload fintbx.pdf to Cloud Storage
├── Trigger Cloud Composer DAG
└── Initialize processing pipeline

Step 2: Document AI Processing
├── Extract text, tables, images, formulas
├── Preserve document structure
├── Generate metadata
└── Create structured output

Step 3: Intelligent Chunking
├── Apply semantic_1200_150 strategy
├── Preserve concept boundaries
├── Generate 53-64 chunks per 20 pages
└── Create chunk metadata

Step 4: Embedding Generation
├── Process chunks with OpenAI text-embedding-3-large
├── Generate 3072-dimensional vectors
├── Batch processing for efficiency
└── Store embeddings in ChromaDB
```

### **Phase 2: Vector Store Population**

```
Step 5: Vector Database Setup
├── Initialize ChromaDB collections
├── Create namespaces for organization
├── Configure similarity search
└── Set up metadata filtering

Step 6: Indexing & Optimization
├── Build vector indices
├── Optimize for similarity search
├── Configure retrieval parameters
└── Performance tuning
```

### **Phase 3: RAG Service Deployment**

```
Step 7: FastAPI Backend
├── Deploy RAG service to Cloud Run
├── Configure API endpoints
├── Set up authentication
└── Enable CORS for frontend

Step 8: User Interface Deployment
├── Deploy Streamlit app
├── Deploy Gradio interface
├── Configure API connections
└── Set up monitoring
```

### **Phase 4: Query Processing Workflow**

```
Step 9: User Query Processing
├── Receive user query
├── Generate query embedding
├── Perform vector similarity search
└── Retrieve top-K relevant chunks

Step 10: Context Assembly
├── Combine retrieved chunks
├── Add source attribution
├── Prepare context for LLM
└── Apply query-specific filters

Step 11: RAG Generation
├── Construct LLM prompt with context
├── Generate structured response
├── Apply Pydantic validation
└── Format output with sources

Step 12: Response Delivery
├── Return concept note to user
├── Log query metrics
├── Update cache if needed
└── Monitor performance
```

---

## 🔧 Technology Stack Details

### **Core Technologies**

| **Component** | **Technology** | **Purpose** | **Performance** |
|---------------|----------------|-------------|-----------------|
| **PDF Parser** | Docling + Vertex AI | Extract structured content | 0.5-1.0 sec/page |
| **Chunking** | LangChain (7 strategies) | Intelligent segmentation | 81.1% optimal |
| **Embeddings** | OpenAI text-embedding-3-large | Vector representations | 3072 dimensions |
| **Vector DB** | ChromaDB | Similarity search | Sub-second retrieval |
| **Orchestration** | Cloud Composer (Airflow) | Workflow management | Automated scheduling |
| **Processing** | Cloud Run Jobs | Scalable processing | 2-3 parallel workers |
| **Backend** | FastAPI | REST API service | High performance |
| **Frontend** | Streamlit + Gradio | User interfaces | Real-time interaction |
| **Database** | Cloud SQL (PostgreSQL) | Cached responses | Fast queries |
| **Cloud** | Google Cloud Platform | Infrastructure | Enterprise-grade |

### **Performance Characteristics**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PERFORMANCE METRICS                                 │
│                                                                                 │
│  Processing Times:                                                              │
│  ├── 50 pages: ~1-2 minutes                                                    │
│  ├── 3,462 pages: ~15-30 minutes                                              │
│  └── Batch size: 20 pages per request                                          │
│                                                                                 │
│  Chunking Performance:                                                         │
│  ├── Strategy: semantic_1200_150 (winner)                                      │
│  ├── Optimal chunks: 81.1%                                                     │
│  ├── Average size: 990 characters                                             │
│  └── Total chunks: ~53 per 20 pages                                            │
│                                                                                 │
│  Retrieval Performance:                                                         │
│  ├── Vector search: <100ms                                                     │
│  ├── Context assembly: <200ms                                                  │
│  ├── LLM generation: 2-5 seconds                                               │
│  └── Total response: <10 seconds                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Orchestration & Scheduling

### **Cloud Composer DAGs**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AIRFLOW DAGs                                       │
│                                                                                 │
│  fintbx_ingest_dag (Weekly):                                                   │
│  ├── Download PDF from Cloud Storage                                           │
│  ├── Process with Document AI (optimized)                                      │
│  ├── Apply semantic chunking strategy                                          │
│  ├── Generate embeddings with OpenAI                                           │
│  ├── Update ChromaDB vector store                                              │
│  └── Upload artifacts to Cloud Storage                                         │
│                                                                                 │
│  concept_seed_dag (Daily):                                                     │
│  ├── Generate financial concept queries                                        │
│  ├── Pre-compute concept notes                                                 │
│  ├── Update vector store with new concepts                                     │
│  └── Cache responses in PostgreSQL                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### **Scheduling Configuration**

| **DAG** | **Schedule** | **Purpose** | **Resources** |
|---------|--------------|-------------|---------------|
| `fintbx_ingest_dag` | Weekly (Sunday 2 AM) | PDF processing | 8GB RAM, 4 CPU |
| `concept_seed_dag` | Daily (3 AM) | Concept updates | 4GB RAM, 2 CPU |
| `monthly_refresh` | Monthly (1st Sunday) | Full refresh | 16GB RAM, 8 CPU |

---

## 🎯 Key Features & Capabilities

### **1. Intelligent PDF Processing**
- **Multi-modal extraction**: Text, tables, images, formulas
- **Structure preservation**: Headings, sections, hierarchy
- **Metadata extraction**: Page numbers, timestamps, source attribution

### **2. Advanced Chunking System**
- **7 strategies**: From recursive to hybrid approaches
- **Automatic optimization**: Best strategy selection
- **Quality metrics**: 81.1% optimal chunk percentage
- **Semantic awareness**: Preserves concept boundaries

### **3. High-Performance Vector Search**
- **3072-dimensional embeddings**: OpenAI's latest model
- **Sub-second retrieval**: Optimized similarity search
- **Metadata filtering**: Context-aware results
- **Scalable storage**: ChromaDB with persistence

### **4. Production-Grade RAG**
- **Structured output**: Pydantic models for consistency
- **Source attribution**: Traceability to original content
- **Wikipedia fallback**: Comprehensive coverage
- **Quality validation**: Instructor integration

### **5. Multi-Interface Support**
- **Streamlit**: Primary web interface
- **Gradio**: Alternative UI with chat
- **REST API**: Programmatic access
- **Real-time**: Live query processing

### **6. Enterprise Scalability**
- **Cloud-native**: Google Cloud Platform
- **Auto-scaling**: Cloud Run services
- **Monitoring**: Built-in observability
- **Security**: Secret Manager, IAM

---

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT LAYER                                   │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Load Balancer │  │   API Gateway   │  │   Services      │  │   Storage   │ │
│  │                 │  │                 │  │                 │  │             │ │
│  │ • Global CDN    │  │ • Authentication│  │ • FastAPI       │  │ • Cloud     │ │
│  │ • SSL/TLS       │  │ • Rate Limiting │  │ • Streamlit     │  │   Storage   │ │
│  │ • Health Checks │  │ • CORS          │  │ • Gradio       │  │ • ChromaDB  │ │
│  │ • Failover      │  │ • Monitoring    │  │ • Auto-scaling  │  │ • Cloud SQL │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 System Metrics & Monitoring

### **Performance KPIs**
- **Processing Speed**: 0.5-1.0 seconds per page
- **Retrieval Latency**: <100ms vector search
- **Response Time**: <10 seconds end-to-end
- **Accuracy**: 81.1% optimal chunk quality
- **Availability**: 99.9% uptime target

### **Quality Metrics**
- **Chunk Distribution**: 81.1% in optimal range (800-1200 chars)
- **Semantic Coherence**: Preserved concept boundaries
- **Source Attribution**: 100% traceability
- **Response Quality**: Structured, validated output

---

## 🎓 Academic Context

**Course**: DAMG 7245 - Document Analysis & Mining  
**Institution**: Northeastern University  
**Project**: AURELIA - Automated Financial Concept Note Generator  
**Architecture**: Production-grade RAG system with enterprise scalability

---

*This architecture represents a complete, production-ready RAG system designed for automated financial concept note generation with enterprise-grade performance, scalability, and reliability.*
