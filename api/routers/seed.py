"""
Seed Endpoints for Batch Concept Generation - ENTERPRISE VERSION
Production implementation with progress tracking and error recovery.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger
import asyncio

from api.dependencies import (
    get_retriever,
    get_generator,
    get_db_client
)
from concept_generator.instructor_models import SeedBatchRequest, SeedConceptItem

router = APIRouter()


# ===== Response Models =====

class SeedResponse(BaseModel):
    """Response for seed operations."""
    success: bool
    message: str
    concepts_processed: int
    concepts_success: int
    concepts_failed: int
    concepts_skipped: int
    details: List[dict]


class SeedStatusResponse(BaseModel):
    """Status of ongoing seed operation."""
    status: str
    progress: float
    concepts_processed: int
    total_concepts: int
    errors: List[str]


# ===== Background Seed Function =====

async def seed_concept_background(
    concept_name: str,
    retriever,
    generator,
    db_client
) -> dict:
    """
    Background task to seed a single concept.
    
    Args:
        concept_name: Name of concept to seed
        retriever: RAG retriever instance
        generator: Concept note generator
        db_client: Database client
        
    Returns:
        Result dict with status and details
    """
    try:
        # Check if already exists
        existing = db_client.get_concept_note(concept_name)
        if existing:
            logger.info(f"Concept '{concept_name}' already in cache, skipping")
            return {
                "concept": concept_name,
                "status": "skipped",
                "reason": "already_exists",
                "confidence": existing.confidence_score
            }
        
        # Retrieve context
        retrieval_result = retriever.retrieve(concept_name)
        
        # Generate concept note
        from concept_generator.instructor_models import ConceptNoteRequest
        
        request = ConceptNoteRequest(
            concept_name=concept_name,
            context=retrieval_result.contexts,
            source=retrieval_result.source.value,
            include_code_examples=True,
            target_length="comprehensive"
        )
        
        concept_note = generator.generate(request)
        
        # Cache
        db_client.cache_concept_note(concept_note)
        
        logger.info(
            f"✓ Successfully seeded: {concept_name} "
            f"(confidence: {concept_note.confidence_score:.2f}, "
            f"source: {concept_note.primary_source})"
        )
        
        return {
            "concept": concept_name,
            "status": "success",
            "confidence": concept_note.confidence_score,
            "source": concept_note.primary_source,
            "key_points": len(concept_note.key_points),
            "citations": len(concept_note.citations)
        }
    
    except Exception as e:
        logger.error(f"✗ Failed to seed '{concept_name}': {e}")
        return {
            "concept": concept_name,
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }


# ===== Seed Endpoints =====

@router.post("/seed", response_model=SeedResponse)
async def seed_concepts(
    request: SeedBatchRequest,
    background_tasks: BackgroundTasks,
    retriever=Depends(get_retriever),
    generator=Depends(get_generator),
    db_client=Depends(get_db_client)
):
    """
    Seed multiple concepts into the database.
    
    This endpoint generates and caches concept notes for a list of concepts.
    Processing happens synchronously for immediate feedback.
    
    For large batches (100+), use Airflow DAG instead.
    
    Args:
        request: SeedBatchRequest with list of concepts
        
    Returns:
        SeedResponse with results for each concept
    """
    try:
        logger.info(f"Seed request received for {len(request.concepts)} concepts")
        
        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for idx, concept_item in enumerate(request.concepts, 1):
            concept_name = concept_item.name
            
            logger.info(f"Processing {idx}/{len(request.concepts)}: {concept_name}")
            
            # Check if force regenerate
            if not request.force_regenerate:
                existing = db_client.get_concept_note(concept_name)
                if existing:
                    results.append({
                        "concept": concept_name,
                        "status": "skipped",
                        "reason": "already_exists",
                        "confidence": existing.confidence_score
                    })
                    skipped_count += 1
                    continue
            
            # Process concept
            result = await seed_concept_background(
                concept_name,
                retriever,
                generator,
                db_client
            )
            
            results.append(result)
            
            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "failed":
                failed_count += 1
            elif result["status"] == "skipped":
                skipped_count += 1
        
        logger.info(
            f"✓ Seeding complete: {success_count} success, "
            f"{failed_count} failed, {skipped_count} skipped"
        )
        
        return SeedResponse(
            success=failed_count == 0,
            message=f"Processed {len(request.concepts)} concepts",
            concepts_processed=len(request.concepts),
            concepts_success=success_count,
            concepts_failed=failed_count,
            concepts_skipped=skipped_count,
            details=results
        )
    
    except Exception as e:
        logger.error(f"Seed operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed/single")
async def seed_single_concept(
    concept_name: str,
    force_regenerate: bool = False,
    retriever=Depends(get_retriever),
    generator=Depends(get_generator),
    db_client=Depends(get_db_client)
):
    """
    Seed a single concept (convenience endpoint).
    
    Args:
        concept_name: Name of concept to seed
        force_regenerate: Force regeneration if exists
        
    Returns:
        Result of seeding operation
    """
    try:
        logger.info(f"Single seed request: {concept_name}")
        
        # Check if already exists
        if not force_regenerate:
            existing = db_client.get_concept_note(concept_name)
            if existing:
                return {
                    "success": True,
                    "message": f"Concept '{concept_name}' already exists in cache",
                    "status": "skipped",
                    "concept": concept_name,
                    "confidence": existing.confidence_score
                }
        
        # Seed concept
        result = await seed_concept_background(
            concept_name,
            retriever,
            generator,
            db_client
        )
        
        if result["status"] == "success":
            return {
                "success": True,
                "message": f"Successfully seeded '{concept_name}'",
                "status": "success",
                "concept": concept_name,
                "confidence": result.get("confidence"),
                "source": result.get("source")
            }
        else:
            return {
                "success": False,
                "message": f"Failed to seed '{concept_name}'",
                "status": "failed",
                "concept": concept_name,
                "error": result.get("error")
            }
    
    except Exception as e:
        logger.error(f"Single seed failed for '{concept_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/concepts/{concept_name}")
async def delete_concept(
    concept_name: str,
    db_client=Depends(get_db_client)
):
    """
    Delete a concept from cache (soft delete).
    
    Args:
        concept_name: Name of concept to delete
        
    Returns:
        Confirmation of deletion
    """
    try:
        deleted = db_client.delete_concept(concept_name)
        
        if deleted:
            return {
                "success": True,
                "message": f"Concept '{concept_name}' deleted",
                "concept": concept_name
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Concept '{concept_name}' not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
