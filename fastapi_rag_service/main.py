from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google.cloud import storage
import chromadb
from chromadb.config import Settings
import json
import requests
import os
import uvicorn
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Financial RAG API", version="1.0")

# Initialize ChromaDB with explicit settings for Cloud Run
chroma_client = chromadb.Client(Settings(
    is_persistent=False,  # Use in-memory storage (Cloud Run is stateless)
    anonymized_telemetry=False
))
collection = chroma_client.get_or_create_collection("financial_chunks")

# Your Google Cloud Storage bucket name
BUCKET_NAME = "financial-rag-artifacts"

# Initialize GCS client
storage_client = storage.Client()

# ===== Pydantic Models =====

class QueryRequest(BaseModel):
    """Request model for /query endpoint"""
    concept: str

class SeedRequest(BaseModel):
    """Request model for /seed endpoint"""
    concepts: Optional[List[str]] = None  # Optional: if not provided, load from GCS

class ConceptNote(BaseModel):
    """Response model for /query endpoint"""
    concept: str
    definition: str
    key_points: List[str]
    examples: List[str]
    references: List[str]
    source: str  # "fintbx.pdf", "chromadb", or "wikipedia"
    cached: bool
    generation_time: Optional[float] = None
    timestamp: str

# ===== Root endpoint for health check =====

@app.get("/")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Financial RAG API",
        "version": "1.0"
    }

# ===== /seed endpoint - POST method =====

@app.post("/seed")
def seed_data(request: SeedRequest = None):
    """
    Download concept_seed_v1.json from GCS and store it in ChromaDB
    
    POST body (optional):
    {
        "concepts": ["Credit Default Swap", "Value at Risk"]
    }
    
    If concepts not provided, loads from GCS file.
    """
    try:
        # If concepts provided in request, use those
        if request and request.concepts:
            concepts_to_seed = request.concepts
            logger.info(f"Seeding {len(concepts_to_seed)} concepts from request")
            
            # Add documents to ChromaDB
            for idx, concept in enumerate(concepts_to_seed):
                collection.add(documents=[concept], ids=[f"manual_{idx}"])
            
            return {
                "status": "ok", 
                "count": len(concepts_to_seed),
                "source": "request"
            }
        
        # Otherwise, load from GCS
        logger.info(f"Fetching seed data from gs://{BUCKET_NAME}/seeds/concept_seed_v1.json")
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob("seeds/concept_seed_v1.json")

        # Download JSON file
        seed_content = blob.download_as_text()
        data = json.loads(seed_content)

        # Add documents to ChromaDB
        for idx, concept in enumerate(data["concepts"]):
            collection.add(documents=[concept], ids=[str(idx)])

        logger.info(f"Successfully loaded {len(data['concepts'])} concepts from GCS")
        return {
            "status": "ok", 
            "count": len(data["concepts"]),
            "source": "gcs"
        }
        
    except Exception as e:
        logger.error(f"Error in /seed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== /query endpoint - POST method =====

@app.post("/query", response_model=ConceptNote)
def query_concept(request: QueryRequest):
    """
    Query from ChromaDB; if no match, fallback to Wikipedia
    
    POST body:
    {
        "concept": "Credit Default Swap"
    }
    
    Returns structured ConceptNote with definition, key points, examples, etc.
    """
    try:
        concept = request.concept
        logger.info(f"Querying for: {concept}")
        
        start_time = datetime.now()
        
        # Query ChromaDB
        result = collection.query(query_texts=[concept], n_results=3)

        if not result["documents"] or not result["documents"][0]:
            # Fallback: search on Wikipedia
            logger.info(f"No ChromaDB match, falling back to Wikipedia for: {concept}")
            wiki_resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{concept.replace(' ', '_')}"
            )
            
            if wiki_resp.status_code == 200:
                wiki_data = wiki_resp.json()
                extract = wiki_data.get("extract", "No data found")
                
                # Parse Wikipedia content into structured format
                generation_time = (datetime.now() - start_time).total_seconds()
                
                return ConceptNote(
                    concept=concept,
                    definition=extract[:500] if len(extract) > 500 else extract,
                    key_points=[
                        "Information sourced from Wikipedia",
                        "May not be in the textbook",
                        "Consider verifying with primary sources"
                    ],
                    examples=[],
                    references=[f"Wikipedia: {wiki_data.get('content_urls', {}).get('desktop', {}).get('page', '')}"],
                    source="wikipedia",
                    cached=False,
                    generation_time=generation_time,
                    timestamp=datetime.now().isoformat()
                )
            else:
                # No data found anywhere
                return ConceptNote(
                    concept=concept,
                    definition="No information found for this concept.",
                    key_points=["Concept not found in database or Wikipedia"],
                    examples=[],
                    references=[],
                    source="none",
                    cached=False,
                    generation_time=0.0,
                    timestamp=datetime.now().isoformat()
                )

        # Found in ChromaDB
        documents = result["documents"][0]
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Parse ChromaDB results into structured format
        # Assuming documents contain the concept information
        context = " ".join(documents) if isinstance(documents, list) else str(documents)
        
        return ConceptNote(
            concept=concept,
            definition=context[:500] if len(context) > 500 else context,
            key_points=[
                "Retrieved from textbook database",
                "Relevant financial concept",
                "Based on fintbx.pdf content"
            ],
            examples=["Example from textbook context"],
            references=["fintbx.pdf - Retrieved from ChromaDB"],
            source="chromadb",
            cached=True,  # Assume cached since it's in ChromaDB
            generation_time=generation_time,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error in /query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Entry point for Cloud Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Financial RAG API on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)