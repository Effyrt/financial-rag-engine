"""
Query Endpoints for Concept Retrieval - ENTERPRISE VERSION
Complete implementation with caching, monitoring, and error handling.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger
import time

from api.dependencies import (
    get_retriever,
    get_generator,
    get_db_client
)
from concept_generator.instructor_models import ConceptNoteRequest
from retrieval.rag_retriever import RetrievalSource
from database.models import SourceType

router = APIRouter()


# ===== Request/Response Models =====

class QueryRequest(BaseModel):
    """Request model for querying concepts."""
    concept_name: str = Field(..., description="Name of financial concept", min_length=2, max_length=255)
    force_regenerate: bool = Field(default=False, description="Force regeneration even if cached")
    include_citations: bool = Field(default=True, description="Include citations in response")
    include_code_examples: bool = Field(default=True, description="Include code examples")


class ConceptNoteResponse(BaseModel):
    """Response model containing complete concept note."""
    concept_name: str
    definition: str
    detailed_explanation: str
    key_points: List[str]
    formulas: List[dict]
    use_cases: List[str]
    code_examples: List[dict]
    prerequisites: List[str]
    related_concepts: List[dict]
    primary_source: str
    citations: List[dict]
    confidence_score: float
    
    # Performance Metadata
    was_cached: bool
    retrieval_time_ms: int
    generation_time_ms: Optional[int] = None
    total_time_ms: int


class QueryResponse(BaseModel):
    """Wrapper for query response."""
    success: bool
    concept_note: Optional[ConceptNoteResponse] = None
    error: Optional[str] = None
    metadata: dict


# ===== Main Query Endpoint =====

@router.post("/query", response_model=QueryResponse)
async def query_concept(
    request: QueryRequest,
    retriever=Depends(get_retriever),
    generator=Depends(get_generator),
    db_client=Depends(get_db_client)
):
    """
    Query for a financial concept note - PRIMARY ENDPOINT.
    
    Complete Pipeline:
    1. Check PostgreSQL cache (fast path ~200ms)
    2. If not cached:
       a. Retrieve context via RAG (vector DB search)
       b. Generate structured note using Instructor + GPT-4
       c. Cache result in PostgreSQL
    3. Track query for analytics
    4. Return concept note
    
    Args:
        request: QueryRequest with concept name and options
        
    Returns:
        QueryResponse with concept note or error
        
    Performance:
    - Cached: ~200-300ms
    - Uncached: ~3,000-5,000ms (includes generation)
    """
    start_time = time.time()
    retrieval_time_ms = 0
    generation_time_ms = 0
    
    try:
        logger.info(
            f"Query received: '{request.concept_name}' "
            f"(force_regenerate={request.force_regenerate})"
        )
        
        # ===== FAST PATH: Check Cache =====
        cached_concept = None
        if not request.force_regenerate:
            cache_start = time.time()
            cached_concept = db_client.get_concept_note(request.concept_name)
            retrieval_time_ms = int((time.time() - cache_start) * 1000)
            
            if cached_concept:
                logger.info(
                    f"✓ Cache HIT for '{request.concept_name}' "
                    f"(retrieved in {retrieval_time_ms}ms)"
                )
                
                # Convert to response format
                concept_response = ConceptNoteResponse(
                    concept_name=cached_concept.concept_name,
                    definition=cached_concept.definition,
                    detailed_explanation=cached_concept.detailed_explanation,
                    key_points=cached_concept.key_points,
                    formulas=cached_concept.formulas if request.include_code_examples else [],
                    use_cases=cached_concept.use_cases,
                    code_examples=cached_concept.code_examples if request.include_code_examples else [],
                    prerequisites=cached_concept.prerequisites,
                    related_concepts=cached_concept.related_concepts,
                    primary_source=cached_concept.primary_source.value,
                    citations=cached_concept.citations if request.include_citations else [],
                    confidence_score=cached_concept.confidence_score,
                    was_cached=True,
                    retrieval_time_ms=retrieval_time_ms,
                    generation_time_ms=None,
                    total_time_ms=retrieval_time_ms
                )
                
                # Track query for analytics
                db_client.track_query(
                    query_text=request.concept_name,
                    concept_name=request.concept_name,
                    source_used=SourceType(cached_concept.primary_source),
                    confidence=cached_concept.confidence_score,
                    contexts_count=0,
                    retrieval_time_ms=retrieval_time_ms,
                    generation_time_ms=0,
                    was_cached=True
                )
                
                return QueryResponse(
                    success=True,
                    concept_note=concept_response,
                    metadata={
                        "cache_hit": True,
                        "source": "cache",
                        "access_count": cached_concept.access_count
                    }
                )
        
        # ===== SLOW PATH: Generate New Concept =====
        logger.info(f"Cache MISS for '{request.concept_name}', retrieving context...")
        
        # Step 1: Retrieve context via RAG
        retrieval_start = time.time()
        retrieval_result = retriever.retrieve(request.concept_name)
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        logger.info(
            f"Retrieved {len(retrieval_result.contexts)} contexts "
            f"(source: {retrieval_result.source}, "
            f"confidence: {retrieval_result.confidence_score:.2f}, "
            f"time: {retrieval_time_ms}ms)"
        )
        
        # Step 2: Generate concept note with Instructor
        generation_start = time.time()
        
        concept_request = ConceptNoteRequest(
            concept_name=request.concept_name,
            context=retrieval_result.contexts,
            source=retrieval_result.source.value,
            include_code_examples=request.include_code_examples,
            target_length="comprehensive"
        )
        
        concept_note = generator.generate(concept_request)
        generation_time_ms = int((time.time() - generation_start) * 1000)
        
        logger.info(
            f"✓ Generated concept note for '{concept_note.concept_name}' "
            f"(generation time: {generation_time_ms}ms)"
        )
        
        # Step 3: Cache the result
        db_client.cache_concept_note(concept_note)
        logger.info(f"✓ Cached concept note for '{concept_note.concept_name}'")
        
        # Step 4: Prepare response
        total_time_ms = retrieval_time_ms + generation_time_ms
        
        concept_response = ConceptNoteResponse(
            concept_name=concept_note.concept_name,
            definition=concept_note.definition,
            detailed_explanation=concept_note.detailed_explanation,
            key_points=concept_note.key_points,
            formulas=[f.dict() for f in concept_note.formulas] if request.include_code_examples else [],
            use_cases=concept_note.use_cases,
            code_examples=[c.dict() for c in concept_note.code_examples] if request.include_code_examples else [],
            prerequisites=concept_note.prerequisites,
            related_concepts=[r.dict() for r in concept_note.related_concepts],
            primary_source=concept_note.primary_source,
            citations=[c.dict() for c in concept_note.citations] if request.include_citations else [],
            confidence_score=concept_note.confidence_score,
            was_cached=False,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=total_time_ms
        )
        
        # Track query for analytics
        db_client.track_query(
            query_text=request.concept_name,
            concept_name=concept_note.concept_name,
            source_used=SourceType.PDF if "pdf" in retrieval_result.source.value.lower() else SourceType.WIKIPEDIA,
            confidence=concept_note.confidence_score,
            contexts_count=len(retrieval_result.contexts),
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            was_cached=False
        )
        
        return QueryResponse(
            success=True,
            concept_note=concept_response,
            metadata={
                "cache_hit": False,
                "source": retrieval_result.source.value,
                "contexts_retrieved": len(retrieval_result.contexts),
                "citations_count": len(retrieval_result.citations)
            }
        )
    
    except Exception as e:
        logger.error(f"Query failed for '{request.concept_name}': {e}")
        
        return QueryResponse(
            success=False,
            error=str(e),
            metadata={
                "concept_name": request.concept_name,
                "error_type": type(e).__name__
            }
        )


# ===== Additional Query Endpoints =====

@router.get("/concept/{concept_name}")
async def get_concept(
    concept_name: str,
    db_client=Depends(get_db_client)
):
    """
    Get a cached concept note by name (lightweight endpoint).
    
    Args:
        concept_name: Name of concept to retrieve
        
    Returns:
        Cached concept note summary or 404
    """
    try:
        concept = db_client.get_concept_note(concept_name)
        
        if not concept:
            raise HTTPException(
                status_code=404,
                detail=f"Concept '{concept_name}' not found in cache"
            )
        
        return {
            "concept_name": concept.concept_name,
            "category": concept.category,
            "definition": concept.definition,
            "confidence_score": concept.confidence_score,
            "primary_source": concept.primary_source.value,
            "created_at": concept.created_at.isoformat(),
            "last_accessed": concept.last_accessed.isoformat() if concept.last_accessed else None,
            "access_count": concept.access_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get concept '{concept_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/search")
async def search_concepts(
    query: Optional[str] = Query(None, description="Search query for concept names"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_confidence: float = Query(0.0, description="Minimum confidence score", ge=0.0, le=1.0),
    limit: int = Query(10, description="Maximum results", ge=1, le=100),
    db_client=Depends(get_db_client)
):
    """
    Search for concepts with flexible filters.
    
    Args:
        query: Text search in concept names (partial match)
        category: Filter by exact category
        min_confidence: Minimum confidence score
        limit: Maximum number of results
        
    Returns:
        List of matching concepts with summaries
    """
    try:
        concepts = db_client.search_concepts(
            query=query,
            category=category,
            min_confidence=min_confidence,
            limit=limit
        )
        
        results = []
        for concept in concepts:
            results.append({
                "concept_name": concept.concept_name,
                "category": concept.category,
                "definition": concept.definition[:200] + "..." if len(concept.definition) > 200 else concept.definition,
                "confidence_score": concept.confidence_score,
                "primary_source": concept.primary_source.value,
                "access_count": concept.access_count
            })
        
        return {
            "total": len(results),
            "query": query,
            "filters": {
                "category": category,
                "min_confidence": min_confidence
            },
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/categories")
async def get_categories(db_client=Depends(get_db_client)):
    """
    Get list of all concept categories with counts.
    
    Returns:
        Dictionary of categories with concept counts
    """
    try:
        stats = db_client.get_cache_stats()
        return {
            "categories": stats.get('by_category', {}),
            "total_categories": len(stats.get('by_category', {}))
        }
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
