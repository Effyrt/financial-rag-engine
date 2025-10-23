"""
FastAPI Backend for Financial RAG Engine.

Provides REST API for:
- Querying financial concepts
- RAG-based concept note generation
- Concept note management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
import os

from app.models.concept import ConceptNote, ConceptQuery, ConceptResponse
from app.services.rag_service import RAGService
from app.core.database import get_db, init_db
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Financial RAG Engine API",
    description="REST API for financial concept retrieval and generation",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
rag_service = RAGService()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting up Financial RAG Engine API...")
    init_db()
    logger.info("✅ API ready!")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Financial RAG Engine API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "financial-rag-api",
        "pinecone": rag_service.check_pinecone_health(),
        "database": "connected"  # TODO: Add actual DB health check
    }


@app.post("/api/v1/query", response_model=ConceptResponse)
async def query_concept(
    query: ConceptQuery,
    db: Session = Depends(get_db)
):
    """
    Query for a financial concept.
    
    Flow:
    1. Check database cache
    2. If not found, use RAG to generate
    3. Save to database
    4. Return concept note
    """
    try:
        logger.info(f"Query received: {query.concept}")
        
        # Check cache first
        cached_concept = rag_service.get_cached_concept(db, query.concept)
        if cached_concept and not query.force_regenerate:
            logger.info(f"Returning cached concept: {query.concept}")
            return ConceptResponse(
                concept=cached_concept,
                source="cache",
                retrieval_time_ms=0
            )
        
        # Generate using RAG
        logger.info(f"Generating concept using RAG: {query.concept}")
        concept, retrieval_time = rag_service.generate_concept_note(
            concept=query.concept,
            top_k=query.top_k
        )
        
        # Save to database
        rag_service.save_concept(db, concept)
        
        return ConceptResponse(
            concept=concept,
            source="rag",
            retrieval_time_ms=retrieval_time
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/concepts", response_model=List[ConceptNote])
async def list_concepts(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all cached concepts."""
    try:
        concepts = rag_service.list_concepts(db, limit=limit, offset=offset)
        return concepts
    except Exception as e:
        logger.error(f"Error listing concepts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/concepts/{title}", response_model=ConceptNote)
async def get_concept(
    title: str,
    db: Session = Depends(get_db)
):
    """Get a specific concept by title."""
    try:
        concept = rag_service.get_cached_concept(db, title)
        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")
        return concept
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting concept: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/concepts/{title}")
async def delete_concept(
    title: str,
    db: Session = Depends(get_db)
):
    """Delete a concept from cache."""
    try:
        success = rag_service.delete_concept(db, title)
        if not success:
            raise HTTPException(status_code=404, detail="Concept not found")
        return {"message": f"Concept '{title}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting concept: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_stats():
    """Get system statistics."""
    try:
        stats = rag_service.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

