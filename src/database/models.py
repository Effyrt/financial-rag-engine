"""
SQLAlchemy Database Models for AURELIA - ENTERPRISE VERSION
Complete schema with all tables, indexes, relationships, and constraints.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean,
    JSON, Enum as SQLEnum, Index, ForeignKey, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class SourceType(str, enum.Enum):
    """Source types for concept notes."""
    PDF = "pdf"
    WIKIPEDIA = "wikipedia"
    HYBRID = "hybrid"


class ConceptStatus(str, enum.Enum):
    """Status of concept note."""
    ACTIVE = "active"
    OUTDATED = "outdated"
    PENDING = "pending"
    ERROR = "error"


class ConceptNoteDB(Base):
    """
    Main table for storing generated concept notes.
    
    This is the primary cache table storing all generated concept notes
    with complete metadata, content, and tracking information.
    """
    __tablename__ = "concept_notes"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core Concept Information
    concept_name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    aliases = Column(JSON, default=list)
    
    # Content Fields
    definition = Column(Text, nullable=False)
    detailed_explanation = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=False)
    
    # Mathematical Content
    formulas = Column(JSON, default=list)
    
    # Practical Information
    use_cases = Column(JSON, nullable=False)
    code_examples = Column(JSON, default=list)
    
    # Relationships and Context
    prerequisites = Column(JSON, default=list)
    related_concepts = Column(JSON, default=list)
    
    # Source and Quality
    primary_source = Column(SQLEnum(SourceType), nullable=False, index=True)
    citations = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False, index=True)
    
    # Status and Versioning
    status = Column(SQLEnum(ConceptStatus, values_callable=lambda x: [e.value for e in x]), default=ConceptStatus.ACTIVE, index=True)
    model_used = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime)
    
    # Usage Statistics
    access_count = Column(Integer, default=0)
    
    # Composite Indexes for Common Queries
    __table_args__ = (
        Index('idx_concept_category_status', 'category', 'status'),
        Index('idx_concept_source_status', 'primary_source', 'status'),
        Index('idx_concept_confidence_status', 'confidence_score', 'status'),
        Index('idx_concept_updated_status', 'updated_at', 'status'),
    )
    
    def __repr__(self):
        return f"<ConceptNote(id={self.id}, name='{self.concept_name}', category='{self.category}')>"


class ConceptQuery(Base):
    """
    Track user queries and retrieval performance for analytics.
    
    This table logs all queries for performance analysis, cache optimization,
    and user behavior insights.
    """
    __tablename__ = "concept_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query Information
    query_text = Column(Text, nullable=False, index=True)
    concept_name_resolved = Column(String(255), index=True)
    
    # Results
    source_used = Column(SQLEnum(SourceType), nullable=False)
    confidence_score = Column(Float)
    contexts_count = Column(Integer)
    
    # Performance Metrics
    retrieval_time_ms = Column(Integer)
    generation_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    
    # Cache Performance
    was_cached = Column(Boolean, default=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_agent = Column(String(255))
    session_id = Column(String(100), index=True)
    
    def __repr__(self):
        return f"<ConceptQuery(id={self.id}, query='{self.query_text[:50]}...')>"


class VectorIndexMetadata(Base):
    """
    Track vector index updates and statistics.
    
    Maintains audit trail of vector database updates for troubleshooting
    and performance monitoring.
    """
    __tablename__ = "vector_index_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Index Information
    index_name = Column(String(100), nullable=False, index=True)
    namespace = Column(String(100), index=True)
    vector_db_type = Column(String(50), nullable=False)
    
    # Statistics
    total_vectors = Column(Integer)
    dimension = Column(Integer)
    
    # Update Information
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_source = Column(String(100))
    chunks_added = Column(Integer, default=0)
    chunks_updated = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<VectorIndexMetadata(index='{self.index_name}', namespace='{self.namespace}')>"


class ConceptSeedJob(Base):
    """
    Track concept seeding jobs from Airflow DAG.
    
    Monitors batch concept generation jobs for progress tracking
    and error analysis.
    """
    __tablename__ = "concept_seed_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job Information
    dag_run_id = Column(String(255), nullable=False, index=True)
    execution_date = Column(DateTime, nullable=False, index=True)
    
    # Concepts to Seed
    concepts_list = Column(JSON, nullable=False)
    total_concepts = Column(Integer, nullable=False)
    
    # Progress Tracking
    processed_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default="running", index=True)
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    def __repr__(self):
        return f"<ConceptSeedJob(id={self.id}, status='{self.status}', concepts={self.total_concepts})>"


class SystemHealth(Base):
    """
    Track system health metrics over time.
    
    Stores periodic health check results for monitoring and alerting.
    """
    __tablename__ = "system_health"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Component Health Status
    vector_db_status = Column(String(20), default="unknown")
    database_status = Column(String(20), default="unknown")
    api_status = Column(String(20), default="unknown")
    embedding_service_status = Column(String(20), default="unknown")
    
    # Performance Metrics
    avg_query_time_ms = Column(Float)
    cache_hit_rate = Column(Float)
    total_concepts_cached = Column(Integer)
    
    # Resource Usage
    disk_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    
    # Timestamp
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemHealth(checked_at='{self.checked_at}', db_status='{self.database_status}')>"