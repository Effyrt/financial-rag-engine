"""
AURELIA FastAPI Service - ENTERPRISE VERSION
Production REST API with monitoring, health checks, and comprehensive endpoints.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
from loguru import logger
from datetime import datetime
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.routers import query, seed
from api.dependencies import (
    get_vector_db,
    get_embedding_service,
    get_retriever,
    get_generator,
    get_db_client
)

# Configure logging
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for startup and shutdown.
    
    Handles:
    - Service initialization
    - Database setup
    - Health checks
    - Cleanup on shutdown
    """
    # Startup
    logger.info("🚀 Starting AURELIA API service...")
    
    # Initialize database
    db_client = get_db_client()
    db_client.init_database()
    logger.info("✓ Database initialized")
    
    # Health check on vector DB
    vector_db = get_vector_db()
    if vector_db.health_check():
        logger.info("✓ Vector DB connected and healthy")
    else:
        logger.warning("⚠ Vector DB health check failed")
    
    # Test embedding service
    try:
        embedding_service = get_embedding_service()
        test_embedding = embedding_service.embed_query("test")
        logger.info(f"✓ Embedding service ready (dimension: {len(test_embedding)})")
    except Exception as e:
        logger.warning(f"⚠ Embedding service test failed: {e}")
    
    logger.info("✓ AURELIA API ready to serve requests")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AURELIA API service...")


# Create FastAPI application
app = FastAPI(
    title="AURELIA API",
    description="Automated Financial Concept Note Generator - Enterprise Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Query", "description": "Concept retrieval and generation endpoints"},
        {"name": "Seed", "description": "Batch concept seeding operations"},
        {"name": "Health", "description": "Health check and monitoring endpoints"},
        {"name": "Analytics", "description": "Statistics and performance metrics"}
    ]
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add processing time to response headers for monitoring."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time-Ms"] = str(int(process_time))
    return response


# Include routers
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(seed.router, prefix="/api/v1", tags=["Seed"])


# ===== Core Endpoints =====

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint with API information.
    
    Returns basic service info and available endpoints.
    """
    return {
        "service": "AURELIA",
        "version": "1.0.0",
        "description": "Automated Financial Concept Note Generator",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "query": "/api/v1/query",
            "seed": "/api/v1/seed",
            "search": "/api/v1/concepts/search",
            "health": "/health",
            "stats": "/stats",
            "metrics": "/metrics"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check(
    db_client=Depends(get_db_client),
    vector_db=Depends(get_vector_db)
):
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Database connectivity
    - Vector DB connectivity
    - API responsiveness
    
    Returns:
        Health status with component details
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database
    try:
        db_healthy = db_client.health_check()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "type": "postgresql"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check vector DB
    try:
        vector_db_healthy = vector_db.health_check()
        health_status["checks"]["vector_db"] = {
            "status": "healthy" if vector_db_healthy else "unhealthy",
            "type": os.getenv("VECTOR_DB_TYPE", "chromadb")
        }
    except Exception as e:
        health_status["checks"]["vector_db"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # API is responding if we got here
    health_status["checks"]["api"] = {"status": "healthy"}
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/stats", tags=["Analytics"])
async def get_stats(db_client=Depends(get_db_client)):
    """
    Get comprehensive system statistics.
    
    Returns:
    - Cache statistics
    - Query statistics
    - Performance metrics
    """
    try:
        cache_stats = db_client.get_cache_stats()
        performance_metrics = db_client.get_performance_metrics(hours=24)
        
        return {
            "cache": cache_stats,
            "performance": performance_metrics,
            "status": "ok"
        }
    
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/metrics", tags=["Analytics"])
async def metrics(db_client=Depends(get_db_client)):
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus text format for monitoring systems.
    """
    try:
        stats = db_client.get_cache_stats()
        
        metrics_text = f"""# HELP aurelia_cached_concepts Total number of cached concepts
# TYPE aurelia_cached_concepts gauge
aurelia_cached_concepts {stats['total_concepts']}

# HELP aurelia_cache_hit_rate Cache hit rate percentage
# TYPE aurelia_cache_hit_rate gauge
aurelia_cache_hit_rate {stats['cache_hit_rate_percent']}

# HELP aurelia_avg_confidence Average confidence score
# TYPE aurelia_avg_confidence gauge
aurelia_avg_confidence {stats['avg_confidence']}

# HELP aurelia_total_queries Total number of queries
# TYPE aurelia_total_queries counter
aurelia_total_queries {stats['total_queries']}
"""
        
        return Response(content=metrics_text, media_type="text/plain")
    
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(content="", media_type="text/plain", status_code=500)


# ===== Exception Handlers =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with custom response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


# For local development
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        workers=1,
        log_level="info"
    )
