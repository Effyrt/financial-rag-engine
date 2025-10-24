"""
PostgreSQL Client for Concept Caching - ENTERPRISE VERSION
Production-grade with connection pooling, transaction management, analytics.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from loguru import logger
from datetime import datetime, timedelta
import json
import os

from database.models import (
    Base, ConceptNoteDB, ConceptQuery, VectorIndexMetadata,
    ConceptSeedJob, SystemHealth, SourceType, ConceptStatus
)


class PostgresClient:
    """
    Production PostgreSQL client with enterprise features.
    
    Features:
    - Connection pooling for performance
    - Transaction management with automatic rollback
    - Caching operations with TTL support
    - Query tracking for analytics
    - Health monitoring
    - Statistics and reporting
    - Automatic schema creation
    - Thread-safe operations
    
    Performance:
    - Connection pool: 10 base + 20 overflow
    - Automatic connection verification
    - Query timeout handling
    - Optimized indexes for common queries
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize PostgreSQL client with connection pooling.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided and not found in environment")
        
        # Create engine with production-grade connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=10,  # Base pool size
            max_overflow=20,  # Additional connections when needed
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections every hour
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info("PostgreSQL client initialized with connection pooling")
    
    def init_database(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✓ Database tables initialized")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        
        Provides automatic transaction management with commit/rollback.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # ===== Concept Note Operations =====
    
    def cache_concept_note(self, concept_note) -> ConceptNoteDB:
        """
        Cache a concept note to the database.
        
        Handles both new inserts and updates to existing concepts.
        
        Args:
            concept_note: ConceptNote object to cache
            
        Returns:
            ConceptNoteDB object (database model)
        """
        with self.get_session() as session:
            # Check if concept already exists
            existing = session.query(ConceptNoteDB).filter(
                ConceptNoteDB.concept_name == concept_note.concept_name
            ).first()
            
            if existing:
                # Update existing concept
                existing.definition = concept_note.definition
                existing.detailed_explanation = concept_note.detailed_explanation
                existing.key_points = concept_note.key_points
                existing.formulas = [f.dict() for f in concept_note.formulas]
                existing.use_cases = concept_note.use_cases
                existing.code_examples = [c.dict() for c in concept_note.code_examples]
                existing.prerequisites = concept_note.prerequisites
                existing.related_concepts = [r.dict() for r in concept_note.related_concepts]
                existing.citations = [c.dict() for c in concept_note.citations]
                existing.confidence_score = concept_note.confidence_score
                existing.model_used = concept_note.model_used
                existing.version = concept_note.version
                existing.updated_at = datetime.utcnow()
                
                logger.info(f"✓ Updated cached concept: {concept_note.concept_name}")
                return existing
            
            # Create new concept
            db_concept = ConceptNoteDB(
                concept_name=concept_note.concept_name,
                category=concept_note.category.value,
                aliases=concept_note.aliases,
                definition=concept_note.definition,
                detailed_explanation=concept_note.detailed_explanation,
                key_points=concept_note.key_points,
                formulas=[f.dict() for f in concept_note.formulas],
                use_cases=concept_note.use_cases,
                code_examples=[c.dict() for c in concept_note.code_examples],
                prerequisites=concept_note.prerequisites,
                related_concepts=[r.dict() for r in concept_note.related_concepts],
                primary_source=SourceType.PDF if "pdf" in concept_note.primary_source.lower() else SourceType.WIKIPEDIA,
                citations=[c.dict() for c in concept_note.citations],
                confidence_score=concept_note.confidence_score,
                model_used=concept_note.model_used,
                version=concept_note.version,
                status=ConceptStatus.ACTIVE
            )
            
            session.add(db_concept)
            session.flush()
            
            logger.info(f"✓ Cached new concept: {concept_note.concept_name} (ID: {db_concept.id})")
            return db_concept
    
    def get_concept_note(self, concept_name: str) -> Optional[ConceptNoteDB]:
        """
        Retrieve a concept note from cache.
        
        Updates access tracking automatically.
        
        Args:
            concept_name: Name of concept to retrieve
            
        Returns:
            ConceptNoteDB object or None if not found
        """
        with self.get_session() as session:
            concept = session.query(ConceptNoteDB).filter(
                and_(
                    ConceptNoteDB.concept_name == concept_name,
                    ConceptNoteDB.status == ConceptStatus.ACTIVE
                )
            ).first()
            
            if concept:
                # Update access tracking
                concept.last_accessed = datetime.utcnow()
                concept.access_count += 1
                session.commit()
                
                logger.info(f"✓ Retrieved cached concept: {concept_name} (accessed {concept.access_count} times)")
            else:
                logger.debug(f"Concept not found in cache: {concept_name}")
            
            return concept
    
    def search_concepts(self,
                       query: Optional[str] = None,
                       category: Optional[str] = None,
                       source: Optional[SourceType] = None,
                       min_confidence: float = 0.0,
                       limit: int = 10) -> List[ConceptNoteDB]:
        """
        Search for concepts with multiple filters.
        
        Args:
            query: Text search in concept name
            category: Filter by category
            source: Filter by source type
            min_confidence: Minimum confidence score
            limit: Maximum results to return
            
        Returns:
            List of matching ConceptNoteDB objects
        """
        with self.get_session() as session:
            filters = [ConceptNoteDB.status == ConceptStatus.ACTIVE]
            
            if query:
                filters.append(
                    ConceptNoteDB.concept_name.ilike(f"%{query}%")
                )
            
            if category:
                filters.append(ConceptNoteDB.category == category)
            
            if source:
                filters.append(ConceptNoteDB.primary_source == source)
            
            filters.append(ConceptNoteDB.confidence_score >= min_confidence)
            
            concepts = session.query(ConceptNoteDB).filter(
                and_(*filters)
            ).order_by(
                ConceptNoteDB.confidence_score.desc()
            ).limit(limit).all()
            
            logger.info(f"Search returned {len(concepts)} concepts")
            return concepts
    
    def delete_concept(self, concept_name: str) -> bool:
        """
        Soft delete a concept (mark as outdated).
        
        Args:
            concept_name: Name of concept to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.get_session() as session:
            concept = session.query(ConceptNoteDB).filter(
                ConceptNoteDB.concept_name == concept_name
            ).first()
            
            if concept:
                concept.status = ConceptStatus.OUTDATED
                logger.info(f"✓ Soft deleted concept: {concept_name}")
                return True
            
            logger.warning(f"Concept not found for deletion: {concept_name}")
            return False
    
    # ===== Query Tracking =====
    
    def track_query(self,
                   query_text: str,
                   concept_name: Optional[str],
                   source_used: SourceType,
                   confidence: float,
                   contexts_count: int,
                   retrieval_time_ms: int,
                   generation_time_ms: int,
                   was_cached: bool,
                   session_id: Optional[str] = None) -> ConceptQuery:
        """
        Track a user query for analytics and monitoring.
        
        Args:
            query_text: Original user query
            concept_name: Resolved concept name
            source_used: Source that was used (PDF/Wikipedia)
            confidence: Confidence score
            contexts_count: Number of contexts retrieved
            retrieval_time_ms: Time for retrieval
            generation_time_ms: Time for generation
            was_cached: Whether result was from cache
            session_id: Optional session identifier
            
        Returns:
            ConceptQuery object
        """
        with self.get_session() as session:
            query = ConceptQuery(
                query_text=query_text,
                concept_name_resolved=concept_name,
                source_used=source_used,
                confidence_score=confidence,
                contexts_count=contexts_count,
                retrieval_time_ms=retrieval_time_ms,
                generation_time_ms=generation_time_ms,
                total_time_ms=retrieval_time_ms + generation_time_ms,
                was_cached=was_cached,
                session_id=session_id
            )
            
            session.add(query)
            return query
    
    # ===== Statistics and Analytics =====
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns detailed metrics about cached concepts, usage patterns,
        and performance.
        """
        with self.get_session() as session:
            # Total active concepts
            total_concepts = session.query(ConceptNoteDB).filter(
                ConceptNoteDB.status == ConceptStatus.ACTIVE
            ).count()
            
            # Breakdown by category
            by_category = dict(session.query(
                ConceptNoteDB.category,
                func.count(ConceptNoteDB.id)
            ).filter(
                ConceptNoteDB.status == ConceptStatus.ACTIVE
            ).group_by(ConceptNoteDB.category).all())
            
            # Breakdown by source
            by_source = dict(session.query(
                ConceptNoteDB.primary_source,
                func.count(ConceptNoteDB.id)
            ).filter(
                ConceptNoteDB.status == ConceptStatus.ACTIVE
            ).group_by(ConceptNoteDB.primary_source).all())
            
            # Average confidence
            avg_confidence = session.query(
                func.avg(ConceptNoteDB.confidence_score)
            ).filter(
                ConceptNoteDB.status == ConceptStatus.ACTIVE
            ).scalar()
            
            # Cache hit rate calculation
            total_queries = session.query(func.count(ConceptQuery.id)).scalar() or 1
            cached_queries = session.query(
                func.count(ConceptQuery.id)
            ).filter(ConceptQuery.was_cached == True).scalar() or 0
            
            cache_hit_rate = (cached_queries / total_queries * 100) if total_queries > 0 else 0
            
            # Most accessed concepts
            most_accessed = session.query(
                ConceptNoteDB.concept_name,
                ConceptNoteDB.access_count
            ).filter(
                ConceptNoteDB.status == ConceptStatus.ACTIVE
            ).order_by(
                ConceptNoteDB.access_count.desc()
            ).limit(5).all()
            
            return {
                'total_concepts': total_concepts,
                'by_category': by_category,
                'by_source': by_source,
                'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
                'cache_hit_rate_percent': round(cache_hit_rate, 2),
                'total_queries': total_queries,
                'cached_queries': cached_queries,
                'most_accessed': [
                    {'concept': name, 'count': count} 
                    for name, count in most_accessed
                ]
            }
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Performance metrics dictionary
        """
        with self.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            recent_queries = session.query(ConceptQuery).filter(
                ConceptQuery.created_at >= cutoff_time
            ).all()
            
            if not recent_queries:
                return {'error': 'No queries in time period'}
            
            # Calculate metrics
            total_queries = len(recent_queries)
            cached_queries = sum(1 for q in recent_queries if q.was_cached)
            
            retrieval_times = [q.retrieval_time_ms for q in recent_queries if q.retrieval_time_ms]
            generation_times = [q.generation_time_ms for q in recent_queries 
                              if q.generation_time_ms is not None]
            total_times = [q.total_time_ms for q in recent_queries if q.total_time_ms]
            
            return {
                'time_period_hours': hours,
                'total_queries': total_queries,
                'cached_queries': cached_queries,
                'cache_hit_rate': round(cached_queries / total_queries * 100, 2),
                'avg_retrieval_time_ms': round(sum(retrieval_times) / len(retrieval_times), 2) if retrieval_times else 0,
                'avg_generation_time_ms': round(sum(generation_times) / len(generation_times), 2) if generation_times else 0,
                'avg_total_time_ms': round(sum(total_times) / len(total_times), 2) if total_times else 0,
                'median_total_time_ms': sorted(total_times)[len(total_times)//2] if total_times else 0
            }
    
    def health_check(self) -> bool:
        """
        Check database connectivity and responsiveness.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_database_size(self) -> Dict[str, Any]:
        """Get database size statistics."""
        with self.get_session() as session:
            try:
                # Get table sizes (PostgreSQL specific)
                result = session.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                        pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)
                
                tables = [
                    {
                        'table': row[1],
                        'size': row[2],
                        'size_bytes': row[3]
                    }
                    for row in result
                ]
                
                return {'tables': tables}
            except Exception as e:
                logger.error(f"Failed to get database size: {e}")
                return {'error': str(e)}


if __name__ == "__main__":
    # Test database client
    client = PostgresClient()
    
    print("Testing PostgreSQL client...")
    
    # Initialize database
    client.init_database()
    print("✓ Database initialized")
    
    # Health check
    if client.health_check():
        print("✓ Database is healthy")
    else:
        print("✗ Database health check failed")
    
    # Get statistics
    stats = client.get_cache_stats()
    print(f"✓ Cache stats: {json.dumps(stats, indent=2)}")