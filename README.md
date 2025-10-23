# Financial RAG Engine

Production-grade RAG system for automated financial concept note generation using Docling + Airflow.

## 🎯 Project Overview

Automated system that generates standardized concept notes for financial topics by:
- Parsing Financial Toolbox User's Guide (fintbx.pdf) with Docling
- Creating intelligent chunks with LangChain
- Storing embeddings in ChromaDB (3072-dim vectors)
- Using Retrieval-Augmented Generation for concept synthesis
- Falling back to Wikipedia when concept not found in PDF

## 🏗️ Architecture

```
Cloud Infrastructure (GCP)
├── Cloud Composer (Airflow)
│   ├── fintbx_ingest_dag (PDF → Chunks → Embeddings)
│   └── concept_seed_dag (Pre-generate notes)
├── ChromaDB (Vector Store)
├── Cloud SQL (PostgreSQL - Cached notes)
├── Cloud Run (FastAPI Service)
└── Cloud Run (Streamlit UI)
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| PDF Parser | Docling |
| Chunking | LangChain |
| Embeddings | OpenAI text-embedding-3-large |
| Vector DB | ChromaDB |
| Orchestration | Cloud Composer (Airflow) |
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL |
| Structured Output | instructor + Pydantic (implemented) |
| Cloud | GCP |

## 📋 Setup Progress

- [ ] **Phase 0:** Infrastructure Setup (Week 1)
  - [ ] GCP Project + Storage
  - [ ] ChromaDB Vector DB
  - [ ] Cloud Composer (Airflow)
  - [ ] Docling Integration Test
  
- [ ] **Phase 1:** Lab 1 - PDF Corpus Construction (Week 1-2)
  - [ ] PDF Parsing with Docling
  - [ ] Chunking Strategy Experimentation
  - [ ] Embedding Generation
  - [ ] Vector Store Population
  
- [ ] **Phase 2:** Lab 2 - Orchestration Pipeline (Week 2)
  - [ ] Concept Database Design
  - [ ] Instructor Integration
  - [ ] Concept Seeding DAG
  
- [ ] **Phase 3:** Lab 3 - FastAPI RAG Service (Week 3)
  - [ ] /query Endpoint
  - [ ] /seed Endpoint
  - [ ] Wikipedia Fallback
  
- [ ] **Phase 4:** Lab 4 - Streamlit Frontend (Week 4)
  - [ ] Search Interface
  - [ ] Concept Display
  - [ ] Source Indicators
  
- [ ] **Phase 5:** Lab 5 - Evaluation & Deployment (Week 5)
  - [ ] Quality Metrics
  - [ ] Performance Benchmarks
  - [ ] Full Deployment

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd financial-rag-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (after Phase 0)
pip install -r requirements.txt
```

### 2. Follow Setup Guides
```bash
# Phase 0: Infrastructure Setup
cd setup
# Follow guides in order:
# 1. 01_gcp_setup.md
# 2. 02_chromadb_setup.md
# 3. 03_composer_setup.md
# 4. 04_docling_test.md
```

### 3. Development Workflow
See `ROADMAP.md` for detailed phase-by-phase instructions.

## 📚 Documentation

- `ROADMAP.md` - Complete project roadmap with status checks
- `setup/` - Infrastructure setup guides
- `docs/` - Architecture and design docs

## 🎓 Course Information

**Course:** DAMG 7245 - Document Analysis & Mining  
**Institution:** Northeastern University  
**Project:** AURELIA - Automated Financial Concept Note Generator

## 📝 License

Academic project - All rights reserved

