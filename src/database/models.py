"""
Database Models - ENTERPRISE++ VERSION
Advanced SQLAlchemy models with indexes, constraints, and audit trails.

Features:
- Comprehensive indexing for performance
- Full-text search support
- Audit trails (created_at, updated_at)
- Soft deletes
- Versioning
- Foreign key relationships
- Custom validators
- JSON fields for flexible storage
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    JSON, Enum as SQLEnum, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


# ===== Enums =====

class ConceptStatus(str, enum.Enum):
    """Status of concept note with full lifecycle."""
    ACTIVE = "active"
    OUTDATED = "outdated"
    PENDING = "pending"
    VALIDATING = "validating"
    ERROR = "error"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    """Source type for content."""
    PDF = "fintbx_pdf"
    WIKIPEDIA = "wikipedia"
    MANUAL = "manual"
    API = "api"


class ConceptCategory(str, enum.Enum):
    """Financial concept categories."""
    RISK_METRICS = "Risk Metrics"
    OPTIONS_DERIVATIVES = "Options and Derivatives"
    FIXED_INCOME = "Fixed Income"
    PORTFOLIO_THEORY = "Portfolio Theory"
    STATISTICAL_METHODS = "Statistical Methods"
    TIME_SERIES = "Time Series Analysis"
    VALUATION = "Valuation Methods"
    MARKET_MICROSTRUCTURE = "Market Microstructure"
    OTHER = "Other"


# ===== Main Tables =====

class ConceptNoteDB(Base):
    """
    Primary table for concept notes with full metadata.
    
    Features:
    - Complete concept information
    - Versioning support
    - Audit trail
    - Performance indexes
    - Full-text search
    """
    __tablename__ = 'concept_notes'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core Concept Information
    concept_name = Column(String(255), nullable=False, index=True)
    category = Column(SQLEnum(ConceptCategory), nullable=False, index=True)
    aliases = Column(ARRAY(String), default=list)  # Alternative names
    
    # Content Fields
    definition = Column(Text, nullable=False)
    detailed_explanation = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=False)  # List[str]
    formulas = Column(JSON)  # List[Formula]
    use_cases = Column(JSON, nullable=False)  # List[str]
    code_examples = Column(JSON)  # List[CodeExample]
    prerequisites = Column(JSON)  # List[str]
    related_concepts = Column(JSON)  # List[RelatedConcept]
    
    # Source & Citation
    primary_source = Column(SQLEnum(SourceType), nullable=False, index=True)
    citations = Column(JSON, nullable=False)  # List[Citation]
    confidence_score = Column(Float, nullable=False, index=True)
    
    # Metadata
    status = Column(
        SQLEnum(ConceptStatus, values_callable=lambda x: [e.value for e in x]),
        default=ConceptStatus.ACTIVE,
        nullable=False,
        index=True
    )
    model_used = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0")
    
    # Quality Metrics
    quality_score = Column(Float)  # Overall quality 0-1
    completeness_score = Column(Float)  # How complete the note is
    citation_fidelity_score = Column(Float)  # Citation quality
    
    # Timestamps (Audit Trail)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, index=True)
    
    # Usage Statistics
    access_count = Column(Integer, default=0)
    regeneration_count = Column(Integer, default=0)
    
    # Soft Delete
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    
    # Relationships
    queries = relationship("QueryLog", back_populates="concept_note")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_concept_status_confidence', 'concept_name', 'status', 'confidence_score'),
        Index('idx_category_status', 'category', 'status'),
        Index('idx_source_confidence', 'primary_source', 'confidence_score'),
        Index('idx_created_desc', created_at.desc()),
        Index('idx_accessed_desc', last_accessed.desc()),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_range'),
        CheckConstraint('access_count >= 0', name='check_access_count_positive'),
        UniqueConstraint('concept_name', 'status', name='unique_active_concept'),
    )


class QueryLog(Base):
    """
    Query logging for analytics and monitoring.
    
    Tracks:
    - All user queries
    - Response times
    - Cache hits/misses
    - Costs
    - Errors
    """
    __tablename__ = 'query_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query Information
    query_text = Column(String(500), nullable=False, index=True)
    concept_name = Column(String(255), index=True)
    
    # Request Details
    force_regenerate = Column(Boolean, default=False)
    include_citations = Column(Boolean, default=True)
    include_code_examples = Column(Boolean, default=True)
    
    # Response Information
    was_cached = Column(Boolean, default=False, index=True)
    retrieval_source = Column(SQLEnum(SourceType), index=True)
    
    # Performance Metrics
    retrieval_time_ms = Column(Float)
    generation_time_ms = Column(Float, nullable=True)
    total_time_ms = Column(Float, index=True)
    
    # Quality Metrics
    confidence_score = Column(Float)
    contexts_retrieved = Column(Integer)
    
    # Cost Tracking
    tokens_used = Column(Integer)
    estimated_cost_usd = Column(Float)
    
    # Error Tracking
    had_error = Column(Boolean, default=False, index=True)
    error_message = Column(Text)
    
    # Request Metadata
    client_ip = Column(String(45))
    user_agent = Column(String(500))
    correlation_id = Column(String(36), index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    concept_note_id = Column(Integer, ForeignKey('concept_notes.id'), nullable=True)
    concept_note = relationship("ConceptNoteDB", back_populates="queries")
    
    # Indexes
    __table_args__ = (
        Index('idx_query_performance', 'created_at', 'total_time_ms'),
        Index('idx_cache_analysis', 'was_cached', 'created_at'),
        Index('idx_error_tracking', 'had_error', 'created_at'),
        Index('idx_cost_tracking', 'created_at', 'estimated_cost_usd'),
    )


class VectorIndexMetadata(Base):
    """
    Metadata for vector database indexes.
    
    Tracks vector DB state for monitoring and debugging.
    """
    __tablename__ = 'vector_index_metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Index Information
    index_name = Column(String(255), nullable=False)
    namespace = Column(String(255))
    vector_db_type = Column(String(50), nullable=False)  # pinecone or chromadb
    
    # Statistics
    total_vectors = Column(Integer, nullable=False)
    dimension = Column(Integer, nullable=False)
    
    # Update Information
    last_update = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_source = Column(String(100))  # airflow_dag, manual, api
    chunks_added = Column(Integer, default=0)
    chunks_updated = Column(Integer, default=0)
    chunks_deleted = Column(Integer, default=0)
    
    # Quality Metrics
    avg_chunk_size = Column(Float)
    total_tokens = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_index_updates', 'index_name', 'last_update'),
    )


class ConceptSeedJob(Base):
    """
    Airflow concept seeding job tracking.
    
    Tracks batch seeding operations from Airflow DAGs.
    """
    __tablename__ = 'concept_seed_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job Identification
    dag_run_id = Column(String(250), nullable=False, unique=True, index=True)
    execution_date = Column(DateTime, nullable=False, index=True)
    
    # Job Configuration
    concepts_list = Column(JSON, nullable=False)  # List of concepts to seed
    total_concepts = Column(Integer, nullable=False)
    
    # Progress Tracking
    processed_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default='pending', index=True)  # pending, running, completed, failed
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Error Handling
    error_message = Column(Text)
    failed_concepts = Column(JSON)  # List of failed concept names
    
    # Cost Tracking
    total_tokens = Column(Integer)
    total_cost_usd = Column(Float)
    
    __table_args__ = (
        Index('idx_seed_job_status', 'status', 'execution_date'),
    )


class PerformanceMetrics(Base):
    """
    Time-series performance metrics for monitoring.
    
    Aggregated metrics collected every 5 minutes.
    """
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Time bucket
    timestamp = Column(DateTime, nullable=False, index=True)
    period_minutes = Column(Integer, default=5)
    
    # Query Metrics
    total_queries = Column(Integer, default=0)
    successful_queries = Column(Integer, default=0)
    failed_queries = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    
    # Performance
    avg_retrieval_time_ms = Column(Float)
    avg_generation_time_ms = Column(Float)
    avg_total_time_ms = Column(Float)
    p95_total_time_ms = Column(Float)
    p99_total_time_ms = Column(Float)
    
    # Quality
    avg_confidence_score = Column(Float)
    avg_quality_score = Column(Float)
    
    # Costs
    total_tokens = Column(Integer)
    total_cost_usd = Column(Float)
    
    # Source Distribution
    pdf_retrievals = Column(Integer, default=0)
    wikipedia_retrievals = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_metrics_timestamp', 'timestamp'),
        Index('idx_metrics_hourly', 'timestamp', 'period_minutes'),
    )


class SystemHealth(Base):
    """
    System health check results for monitoring.
    
    Stores periodic health check results for trending.
    """
    __tablename__ = 'system_health'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Component Health
    database_healthy = Column(Boolean, nullable=False)
    vector_db_healthy = Column(Boolean, nullable=False)
    redis_healthy = Column(Boolean, nullable=True)
    api_healthy = Column(Boolean, nullable=False)
    
    # Response Times
    database_response_ms = Column(Float)
    vector_db_response_ms = Column(Float)
    
    # Overall Status
    overall_status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy
    
    # Additional Metadata
    metadata = Column(JSON)
    
    __table_args__ = (
        Index('idx_health_timestamp', 'timestamp'),
        Index('idx_health_status', 'overall_status', 'timestamp'),
    )


# ===== Helper Functions =====

def create_all_tables(engine):
    """Create all tables with proper error handling."""
    try:
        Base.metadata.create_all(engine)
        logger.info("✓ All database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def drop_all_tables(engine):
    """Drop all tables (use with caution!)."""
    try:
        Base.metadata.drop_all(engine)
        logger.info("✓ All tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise