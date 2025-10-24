"""
Pydantic models for concept notes.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ConceptNote(BaseModel):
    """Concept note data model."""
    
    title: str = Field(..., description="Concept title")
    definition: str = Field(..., description="Clear definition")
    formula: Optional[str] = Field(None, description="Mathematical formula if applicable")
    example: Optional[str] = Field(None, description="Practical example")
    use_cases: List[str] = Field(default_factory=list, description="Use cases")
    references: List[str] = Field(default_factory=list, description="Source references")
    source: str = Field("PDF", description="Source: PDF or Wikipedia")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Black-Scholes Model",
                "definition": "A mathematical model for pricing European-style options",
                "formula": "C = S₀N(d₁) - Ke^(-rT)N(d₂)",
                "example": "Pricing a call option on AAPL stock",
                "use_cases": ["Option pricing", "Risk management"],
                "references": ["Financial Toolbox p.45", "Wikipedia"],
                "source": "PDF",
                "metadata": {"pages": [45, 46], "namespace": "options-pricing"}
            }
        }


class ConceptQuery(BaseModel):
    """Query request model."""
    
    concept: str = Field(..., description="Financial concept to query")
    top_k: int = Field(5, description="Number of similar chunks to retrieve", ge=1, le=20)
    force_regenerate: bool = Field(False, description="Force regeneration even if cached")
    
    class Config:
        json_schema_extra = {
            "example": {
                "concept": "Black-Scholes Model",
                "top_k": 5,
                "force_regenerate": False
            }
        }


class ConceptResponse(BaseModel):
    """Query response model."""
    
    concept: ConceptNote
    source: str = Field(..., description="Source: cache, rag, or wikipedia")
    retrieval_time_ms: float = Field(..., description="Retrieval time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "concept": {
                    "title": "Black-Scholes Model",
                    "definition": "A mathematical model for pricing European-style options",
                    "formula": "C = S₀N(d₁) - Ke^(-rT)N(d₂)",
                    "example": "Pricing a call option on AAPL stock",
                    "use_cases": ["Option pricing", "Risk management"],
                    "references": ["Financial Toolbox p.45"],
                    "source": "PDF",
                    "metadata": {}
                },
                "source": "rag",
                "retrieval_time_ms": 1250.5
            }
        }

