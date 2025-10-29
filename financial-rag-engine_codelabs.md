summary: Financial RAG Engine 
id: financial-rag-engine
categories: data-engineering

# Financial RAG Engine

AURELIA is a cloud-native Retrieval-Augmented Generation (RAG) system built to generate standardized financial concept notes from the *Financial Toolbox User’s Guide*.  
This codelab explains how we designed, implemented, and deployed the system step by step on Google Cloud Platform.

Prerequisites: Python 3.10+, Google Cloud account, OpenAI API key  

---

## Step 1 — Building the PDF Corpus
We began by constructing a high-quality corpus from the *Financial Toolbox User’s Guide *.

- **Method:** Used *Google Document AI* combined with *LayoutParser* to parse the PDF.  
  This preserved section hierarchy, figures, equations, and captions in correct reading order.  
- **Data Cleaning:** Removed noise, merged fragmented lines, and standardized headers.  
- **Result:** A structured dataset with page-level metadata and extracted text stored in Google Cloud Storage for downstream tasks.  

---

## Step 2 — Chunking and Embedding
To make the document searchable, we implemented a multi-strategy chunking and embedding pipeline.

- **Experiment:** Tested seven chunking methods (recursive, markdown header, semantic window, etc.) to balance coverage and coherence.  
- **Best Strategy:** Selected **semantic_1200_150**, which achieved the highest retrieval quality (81.1 % optimal chunks).  
- **Embedding:** Generated 3072-dimensional vectors using **OpenAI text-embedding-3-large**.  
- **Storage:** Stored all vectors and metadata in **ChromaDB** under the namespace “financial_concepts.”  
- **Result:** Sub-second retrieval across 100 k + chunks with strong semantic consistency.  

---

## Step 3 — Cloud Orchestration
We automated the end-to-end workflow using **Google Cloud Composer (Airflow)**.

- **DAGs Created:**  
  - `fintbx_ingest_dag` — parses PDFs and uploads structured text to GCS.  
  - `concept_seed_dag` — seeds the concept database by generating JSON notes.  
- **Parameterization:** Each DAG supports both scheduled refresh and on-demand runs.  
- **Error Handling:** Implemented retries and artifact versioning to ensure reproducibility.  
- **Result:** The entire RAG data pipeline can be re-executed automatically in the cloud without manual intervention.  

---

## Step 4 — RAG Microservice Development
Next, we built a FastAPI-based microservice to perform concept retrieval and generation.

- **Endpoints:**  
  - `/seed` – loads pre-defined concept lists and stores them in the vector DB.  
  - `/query` – retrieves top-k similar chunks, generates structured notes via GPT-4, and returns them in JSON.  
- **Logic Flow:**  
  1. Retrieve context from ChromaDB  
  2. If empty, fetch supplementary content from Wikipedia  
  3. Send context to GPT-4 using LangChain  
  4. Validate output using Instructor’s Pydantic schema  
  5. Cache results in PostgreSQL  
- **Result:** Response time under 10 s; retrieval latency < 100 ms; fallback coverage 100 %.  

---

## Step 5 — Frontend and User Interface
We developed two interfaces for usability and demonstration.

- **Streamlit App:** Simple layout where users can enter a concept, view cached notes, or generate new ones.  
- **Gradio Interface:** Chat-style layout for natural-language interaction.  
- **Deployment:** Both frontend and backend deployed on **Cloud Run**, communicating via REST APIs.  
- **UI Features:**  
  - Displays PDF section sources and page references.  
  - Highlights when content is retrieved from Wikipedia.  
- **Result:** Smooth, real-time interaction experience accessible from any browser.  

---

## Step 6 — Evaluation and Performance
To assess the quality and efficiency of AURELIA, we conducted end-to-end benchmarking.

| Metric | Result | Observation |
|:--|:--|:--|
| **Chunking Quality** | 81.1 % optimal | Best contextual preservation |
| **Retrieval Latency** | < 100 ms | Fast vector similarity search |
| **Response Time** | < 10 s | End-to-end note generation |
| **Processing Speed** | 0.5–1 s / page | Document AI parsing |
| **Accuracy** | High | Reliable citations and structured output |
| **Cached Queries** | ~5× faster | Efficient PostgreSQL reuse |

**Key Insight:**  
Semantic-aware chunking and schema validation via Instructor significantly improved factual accuracy and consistency compared to basic RAG implementations.  

---

## Step 7 — Summary and Future Work
AURELIA demonstrates a scalable and explainable financial knowledge generation pipeline.

**Achievements**
- Fully cloud-hosted with zero local dependency  
- Seamless integration of Document AI, ChromaDB, LangChain, and GPT-4  
- Robust orchestration with Airflow  
- Accurate, source-linked concept generation  

**Next Steps**
- Add version control for document updates  
- Enhance multimodal understanding with financial tables and charts  
- Integrate authentication and role-based access for enterprise deployment  

---

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com)  
- [LangChain](https://python.langchain.com)  
- [ChromaDB](https://docs.trychroma.com)  
- [Google Cloud Composer](https://cloud.google.com/composer)  
- [Document AI](https://cloud.google.com/document-ai/docs)  
- [Streamlit](https://docs.streamlit.io)

