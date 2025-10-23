"""
Database configuration and session management.
"""

import os
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag_user:password@localhost/financial_rag"
)

# Create engine with SQLite thread safety
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class ConceptNoteDB(Base):
    """Database model for concept notes."""
    
    __tablename__ = "concept_notes"
    
    title = Column(String, primary_key=True, index=True)
    definition = Column(Text, nullable=False)
    formula = Column(Text, nullable=True)
    example = Column(Text, nullable=True)
    use_cases = Column(JSON, default=list)
    references = Column(JSON, default=list)
    source = Column(String, default="PDF")
    extra_metadata = Column("metadata", JSON, default=dict)  # Renamed to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Don't fail startup if DB not available
        pass


def get_db() -> Session:
    """
    Dependency for getting database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

