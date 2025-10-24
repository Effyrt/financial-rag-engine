"""
Dependency Injection for FastAPI Endpoints - ENTERPRISE VERSION
Manages singleton instances of all services with proper lifecycle.
"""

import os
from functools import lru_cache
from loguru import logger
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from embeddings.embedding_service import EmbeddingService
from vectordb.pinecone_client import PineconeVectorDB
from vectordb.chromadb_client import ChromaVectorDB
from retrieval.rag_retriever import RAGRetriever
from retrieval.wikipedia_fallback import WikipediaFallback
from concept_generator.concept_note_generator import ConceptNoteGenerator
from database.postgres_client import PostgresClient

# Configuration
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'chromadb')


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """
    Get singleton embedding service instance.
    
    Uses LRU cache to ensure single instance across requests.
    """
    logger.info("Initializing Embedding Service singleton")
    return EmbeddingService(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", 100)),
        max_workers=int(os.getenv("EMBEDDING_MAX_WORKERS", 5))
    )


@lru_cache()
def get_vector_db():
    """
    Get singleton vector database client.
    
    Automatically selects Pinecone or ChromaDB based on configuration.
    """
    logger.info(f"Initializing Vector DB singleton ({VECTOR_DB_TYPE})")
    
    if VECTOR_DB_TYPE.lower() == 'pinecone':
        return PineconeVectorDB(
            index_name=os.getenv("PINECONE_INDEX_NAME", "aurelia-financial-concepts"),
            dimension=int(os.getenv("PINECONE_DIMENSION", 3072))
        )
    else:
        return ChromaVectorDB(
            persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chromadb"),
            collection_name=os.getenv("CHROMA_COLLECTION_NAME", "financial_concepts")
        )


@lru_cache()
def get_wikipedia_fallback() -> WikipediaFallback:
    """Get singleton Wikipedia fallback service."""
    logger.info("Initializing Wikipedia Fallback singleton")
    return WikipediaFallback(
        lang="en",
        sentences=5,
        auto_suggest=True
    )


@lru_cache()
def get_retriever() -> RAGRetriever:
    """
    Get singleton RAG retriever.
    
    Combines vector DB, embedding service, and Wikipedia fallback
    into a complete retrieval pipeline.
    """
    logger.info("Initializing RAG Retriever singleton")
    
    vector_db = get_vector_db()
    embedding_service = get_embedding_service()
    wikipedia_fallback = get_wikipedia_fallback()
    
    return RAGRetriever(
        vector_db=vector_db,
        embedding_service=embedding_service,
        wikipedia_fallback=wikipedia_fallback,
        top_k=int(os.getenv("TOP_K_RETRIEVAL", 5)),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", 0.7)),
        enable_fallback=os.getenv("FALLBACK_TO_WIKIPEDIA", "true").lower() == "true"
    )


@lru_cache()
def get_generator() -> ConceptNoteGenerator:
    """Get singleton concept note generator."""
    logger.info("Initializing Concept Note Generator singleton")
    
    return ConceptNoteGenerator(
        model=os.getenv("INSTRUCTOR_MODEL", "gpt-4-turbo-preview"),
        temperature=float(os.getenv("INSTRUCTOR_TEMPERATURE", 0.3)),
        max_retries=int(os.getenv("MAX_RETRIES", 3))
    )


@lru_cache()
def get_db_client() -> PostgresClient:
    """Get singleton PostgreSQL client."""
    logger.info("Initializing PostgreSQL Client singleton")
    
    return PostgresClient(
        database_url=os.getenv("DATABASE_URL")
    )


# Clear cache function for testing/development
def clear_dependency_cache():
    """
    Clear all cached dependencies.
    
    Useful for testing or when configuration changes.
    """
    get_embedding_service.cache_clear()
    get_vector_db.cache_clear()
    get_wikipedia_fallback.cache_clear()
    get_retriever.cache_clear()
    get_generator.cache_clear()
    get_db_client.cache_clear()
    logger.info("✓ Dependency cache cleared")


# Startup verification
if __name__ == "__main__":
    print("Testing dependency injection...")
    
    # Test each dependency
    try:
        db = get_db_client()
        print("✓ PostgreSQL client initialized")
        
        vector_db = get_vector_db()
        print(f"✓ Vector DB initialized ({VECTOR_DB_TYPE})")
        
        embedding = get_embedding_service()
        print("✓ Embedding service initialized")
        
        retriever = get_retriever()
        print("✓ RAG retriever initialized")
        
        generator = get_generator()
        print("✓ Concept generator initialized")
        
        print("\n✅ All dependencies initialized successfully!")
        
    except Exception as e:
        print(f"\n✗ Dependency initialization failed: {e}")
        print("   Check your .env file and API keys")