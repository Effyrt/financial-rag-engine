"""
Structured Output Models using Instructor for concept note generation.
Complete Pydantic schemas with validation and examples.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class ConceptCategory(str, Enum):
    """Financial concept categories."""
    RISK_METRICS = "Risk Metrics"
    OPTIONS_PRICING = "Options and Derivatives"
    FIXED_INCOME = "Fixed Income"
    PORTFOLIO_THEORY = "Portfolio Theory"
    TIME_SERIES = "Time Series Analysis"
    STATISTICAL_METHODS = "Statistical Methods"
    GENERAL = "General Finance"


class CitationType(str, Enum):
    """Types of citations."""
    PDF_SECTION = "pdf_section"
    PDF_PAGE = "pdf_page"
    WIKIPEDIA = "wikipedia"
    CODE_EXAMPLE = "code_example"


class Citation(BaseModel):
    """Citation information."""
    source: str = Field(..., description="Source name")
    citation_type: CitationType = Field(..., description="Type of citation")
    location: str = Field(..., description="Specific location")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    excerpt: Optional[str] = Field(None, max_length=200)


class CodeExample(BaseModel):
    """Code example for financial concept."""
    language: str = Field(default="MATLAB")
    code: str = Field(..., description="Code snippet")
    description: str = Field(..., description="What code demonstrates")
    expected_output: Optional[str] = None


class Formula(BaseModel):
    """Mathematical formula."""
    latex: str = Field(..., description="LaTeX formula")
    description: str = Field(..., description="What formula calculates")
    variables: List[str] = Field(default_factory=list)


class RelatedConcept(BaseModel):
    """Related financial concept."""
    name: str
    relationship: str
    brief_description: str = Field(..., max_length=200)


class ConceptNote(BaseModel):
    """
    Complete structured financial concept note.
    This is the main output format for AURELIA.
    """
    
    # Basic Information
    concept_name: str = Field(..., description="Name of financial concept")
    category: ConceptCategory = Field(..., description="Primary category")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    
    # Core Content
    definition: str = Field(..., min_length=50, max_length=500)
    detailed_explanation: str = Field(..., min_length=200)
    key_points: List[str] = Field(..., min_items=3, max_items=7)
    
    # Mathematical Content
    formulas: List[Formula] = Field(default_factory=list)
    
    # Practical Application
    use_cases: List[str] = Field(..., min_items=1, max_items=5)
    code_examples: List[CodeExample] = Field(default_factory=list)
    
    # Context and Relationships
    prerequisites: List[str] = Field(default_factory=list)
    related_concepts: List[RelatedConcept] = Field(default_factory=list)
    
    # Source Information
    primary_source: str = Field(..., description="Primary source (PDF or Wikipedia)")
    citations: List[Citation] = Field(..., min_items=1)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = Field(default="gpt-4-turbo-preview")
    version: str = Field(default="1.0")


class ConceptNoteRequest(BaseModel):
    """Request format for concept note generation."""
    concept_name: str
    context: Optional[List[str]] = None
    source: str
    include_code_examples: bool = Field(default=True)
    target_length: str = Field(default="comprehensive")


class SeedConceptItem(BaseModel):
    """Single concept for batch seeding."""
    name: str
    category: Optional[ConceptCategory] = None
    priority: int = Field(default=5, ge=1, le=10)


class SeedBatchRequest(BaseModel):
    """Batch concept seeding request."""
    concepts: List[SeedConceptItem] = Field(..., min_items=1)
    force_regenerate: bool = Field(default=False)
    namespace: str = Field(default="financial-toolbox")