"""
RAG Service for concept note generation.
"""

import os
import time
import logging
from typing import List, Optional, Tuple, Dict, Any
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from pathlib import Path
import instructor

# Load environment variables from project root
# Go up 4 levels: rag_service.py -> services -> app -> backend -> project_root
project_root = Path(__file__).resolve().parent.parent.parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

from app.models.concept import ConceptNote
from app.core.database import ConceptNoteDB

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG-based concept note generation."""
    
    def __init__(self):
        """Initialize RAG service with OpenAI and ChromaDB clients."""
        # Initialize clients only if API keys are available
        self.openai_client = None
        self.chroma_client = None
        self.collection = None
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "3072"))
        self.chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
        self.collection_name = os.getenv("CHROMA_COLLECTION_NAME", "financial-concepts")
        
        # Ensure data directory exists
        os.makedirs(self.chroma_path, exist_ok=True)
        os.makedirs("./data/processed", exist_ok=True)
        
        # Try to initialize OpenAI client with instructor
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            try:
                self.openai_client = instructor.from_openai(OpenAI(api_key=openai_key))
                logger.info("✅ OpenAI client with instructor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client with instructor: {e}")
                # Fallback to regular OpenAI client
                try:
                    self.openai_client = OpenAI(api_key=openai_key)
                    logger.info("✅ OpenAI client initialized (fallback)")
                except Exception as e2:
                    logger.error(f"❌ Failed to initialize OpenAI client: {e2}")
                    self.openai_client = None
        else:
            logger.warning("⚠️ OpenAI API key not found or not configured")
        
        # Try to initialize ChromaDB client
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Financial concepts and documentation"}
            )
            logger.info(f"✅ ChromaDB client initialized at {self.chroma_path}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB client: {e}")
            self.chroma_client = None
            self.collection = None
        
        # Validate initialization
        if self.openai_client and self.collection:
            logger.info("✅ RAG Service fully initialized")
        else:
            logger.warning("⚠️ RAG Service partially initialized - some features may not work")
    
    def check_chromadb_health(self) -> bool:
        """Check if ChromaDB is accessible."""
        if not self.collection:
            logger.warning("ChromaDB not initialized")
            return False
        try:
            self.collection.count()
            return True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model,
                dimensions=self.embedding_dimension
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from ChromaDB."""
        if not self.collection:
            logger.warning("ChromaDB not initialized, returning empty results")
            return []
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["metadatas", "distances"]
            )
            
            # Extract chunks
            chunks = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    # Convert distance to similarity score (ChromaDB uses distance, lower is better)
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1 - distance  # Convert distance to similarity
                    
                    chunks.append({
                        "text": metadata.get("chunk_text", ""),
                        "score": score,
                        "page": metadata.get("page_number"),
                        "source": metadata.get("source_file"),
                        "namespace": metadata.get("namespace")
                    })
            
            logger.info(f"Retrieved {len(chunks)} chunks for query: {query}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            raise
    
    def generate_concept_note(
        self,
        concept: str,
        top_k: int = 5
    ) -> Tuple[ConceptNote, float]:
        """
        Generate concept note using RAG.
        
        Returns:
            (ConceptNote, retrieval_time_ms)
        """
        start_time = time.time()
        
        try:
            # Retrieve relevant chunks
            chunks = self.retrieve_relevant_chunks(concept, top_k=top_k)
            
            if not chunks:
                logger.warning(f"No chunks found for concept: {concept}, trying Wikipedia fallback")
                # Try Wikipedia fallback
                return self._generate_wikipedia_concept(concept, start_time)
            
            # Build context from chunks
            context = "\n\n".join([
                f"[Source: {c['source']}, Page: {c['page']}, Score: {c['score']:.3f}]\n{c['text']}"
                for c in chunks
            ])
            
            # Generate concept note with LLM
            if not self.openai_client:
                logger.warning("OpenAI client not initialized, returning basic concept note")
                return ConceptNote(
                    title=concept,
                    definition=f"Basic information for '{concept}' (OpenAI not available)",
                    source="basic",
                    metadata={"error": "openai_not_available", "chunks_used": len(chunks)}
                ), (time.time() - start_time) * 1000

            prompt = f"""Based on the following excerpts from a financial textbook, create a comprehensive concept note for: {concept}

Context:
{context}

Generate a structured concept note with these EXACT fields:
- title: "{concept}" (exact concept name)
- definition: Clear, concise definition (2-3 sentences)
- formula: Mathematical formula in LaTeX format if applicable, otherwise null
- example: Practical example (1-2 sentences)
- use_cases: Array of specific use cases (3-5 items)
- references: Array of source page references
- source: "PDF"
- metadata: Object with chunks_used, top_score, namespaces

Be precise and use information only from the provided context. Ensure all fields match the expected structure exactly."""

            # Use instructor for structured output
            try:
                concept_note = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial education expert. Generate structured concept notes from textbook content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_model=ConceptNote
                )
                
                # Update the concept note with additional metadata
                concept_note.title = concept
                concept_note.source = "PDF"
                concept_note.metadata = {
                    "chunks_used": len(chunks),
                    "top_score": chunks[0]["score"] if chunks else 0,
                    "namespaces": list(set(c.get("namespace") for c in chunks if c.get("namespace")))
                }
                
            except Exception as e:
                logger.warning(f"Instructor failed, falling back to manual JSON parsing: {e}")
                # Fallback to manual JSON parsing
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial education expert. Generate structured concept notes from textbook content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                import json
                concept_data = json.loads(response.choices[0].message.content)
                
                # Create ConceptNote
                concept_note = ConceptNote(
                    title=concept_data.get("title", concept),
                    definition=concept_data.get("definition", ""),
                    formula=concept_data.get("formula"),
                    example=concept_data.get("example"),
                    use_cases=concept_data.get("use_cases", []),
                    references=concept_data.get("references", []),
                    source="PDF",
                    metadata={
                        "chunks_used": len(chunks),
                        "top_score": chunks[0]["score"] if chunks else 0,
                        "namespaces": list(set(c.get("namespace") for c in chunks if c.get("namespace")))
                    }
                )
            
            retrieval_time = (time.time() - start_time) * 1000
            logger.info(f"Generated concept note for '{concept}' in {retrieval_time:.2f}ms")
            
            return concept_note, retrieval_time
            
        except Exception as e:
            logger.error(f"Error generating concept note: {e}", exc_info=True)
            raise
    
    def get_cached_concept(self, db: Session, title: str) -> Optional[ConceptNote]:
        """Get concept from database cache."""
        try:
            db_concept = db.query(ConceptNoteDB).filter(ConceptNoteDB.title == title).first()
            if db_concept:
                return ConceptNote(
                    title=db_concept.title,
                    definition=db_concept.definition,
                    formula=db_concept.formula,
                    example=db_concept.example,
                    use_cases=db_concept.use_cases or [],
                    references=db_concept.references or [],
                    source=db_concept.source,
                    metadata=db_concept.metadata or {},
                    created_at=db_concept.created_at
                )
            return None
        except Exception as e:
            logger.error(f"Error getting cached concept: {e}")
            return None
    
    def save_concept(self, db: Session, concept: ConceptNote) -> bool:
        """Save concept to database."""
        try:
            db_concept = ConceptNoteDB(
                title=concept.title,
                definition=concept.definition,
                formula=concept.formula,
                example=concept.example,
                use_cases=concept.use_cases,
                references=concept.references,
                source=concept.source,
                metadata=concept.metadata
            )
            
            # Upsert (update if exists, insert if not)
            existing = db.query(ConceptNoteDB).filter(ConceptNoteDB.title == concept.title).first()
            if existing:
                for key, value in concept.dict().items():
                    if key != "created_at":
                        setattr(existing, key, value)
            else:
                db.add(db_concept)
            
            db.commit()
            logger.info(f"Saved concept: {concept.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving concept: {e}")
            db.rollback()
            return False
    
    def list_concepts(self, db: Session, limit: int = 50, offset: int = 0) -> List[ConceptNote]:
        """List all cached concepts."""
        try:
            db_concepts = db.query(ConceptNoteDB).offset(offset).limit(limit).all()
            return [
                ConceptNote(
                    title=c.title,
                    definition=c.definition,
                    formula=c.formula,
                    example=c.example,
                    use_cases=c.use_cases or [],
                    references=c.references or [],
                    source=c.source,
                    metadata=c.metadata or {},
                    created_at=c.created_at
                )
                for c in db_concepts
            ]
        except Exception as e:
            logger.error(f"Error listing concepts: {e}")
            return []
    
    def delete_concept(self, db: Session, title: str) -> bool:
        """Delete concept from database."""
        try:
            db_concept = db.query(ConceptNoteDB).filter(ConceptNoteDB.title == title).first()
            if db_concept:
                db.delete(db_concept)
                db.commit()
                logger.info(f"Deleted concept: {title}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting concept: {e}")
            db.rollback()
            return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        try:
            stats = {
                "openai_available": self.openai_client is not None,
                "chromadb_available": self.collection is not None,
                "status": "healthy" if (self.openai_client or self.collection) else "degraded"
            }
            
            if self.collection:
                # ChromaDB stats
                try:
                    count = self.collection.count()
                    stats["chromadb"] = {
                        "total_vectors": count,
                        "collection_name": self.collection.name,
                        "dimension": self.embedding_dimension
                    }
                except Exception as e:
                    stats["chromadb"] = {"error": f"failed_to_get_stats: {e}"}
            else:
                stats["chromadb"] = {"error": "not_initialized"}
            
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_wikipedia_concept(self, concept: str, start_time: float) -> Tuple[ConceptNote, float]:
        """Generate concept note using Wikipedia as fallback."""
        try:
            if not self.openai_client:
                return ConceptNote(
                    title=concept,
                    definition=f"No information found for '{concept}' in the knowledge base or Wikipedia.",
                    source="empty",
                    metadata={"error": "no_chunks_found", "wikipedia_fallback": "openai_unavailable"}
                ), (time.time() - start_time) * 1000
            
            # Use OpenAI to generate a basic concept note
            prompt = f"""Generate a comprehensive concept note for the financial concept: {concept}

Please provide these EXACT fields:
- title: "{concept}" (exact concept name)
- definition: Clear, concise definition (2-3 sentences)
- formula: Mathematical formula in LaTeX format if applicable, otherwise null
- example: Practical example (1-2 sentences)
- use_cases: Array of specific use cases (3-5 items)
- references: Array of general financial literature references
- source: "Wikipedia"
- metadata: Object with wikipedia_fallback: true, fallback_reason: "not_found_in_knowledge_base"

Note: This is generated from general knowledge as the specific concept was not found in the financial textbook database."""

            try:
                concept_note = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial education expert. Generate structured concept notes from general financial knowledge."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_model=ConceptNote
                )
                
                # Update the concept note with Wikipedia source
                concept_note.title = concept
                concept_note.source = "Wikipedia"
                concept_note.metadata = {
                    "wikipedia_fallback": True,
                    "chunks_used": 0,
                    "top_score": 0,
                    "fallback_reason": "not_found_in_knowledge_base"
                }
                
                retrieval_time = (time.time() - start_time) * 1000
                logger.info(f"Generated Wikipedia fallback concept note for '{concept}' in {retrieval_time:.2f}ms")
                
                return concept_note, retrieval_time
                
            except Exception as e:
                logger.warning(f"Instructor failed for Wikipedia fallback, using manual JSON: {e}")
                # Fallback to manual JSON parsing
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial education expert. Generate structured concept notes from general financial knowledge."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                import json
                concept_data = json.loads(response.choices[0].message.content)
                
                # Create ConceptNote
                concept_note = ConceptNote(
                    title=concept_data.get("title", concept),
                    definition=concept_data.get("definition", ""),
                    formula=concept_data.get("formula"),
                    example=concept_data.get("example"),
                    use_cases=concept_data.get("use_cases", []),
                    references=concept_data.get("references", []),
                    source="Wikipedia",
                    metadata={
                        "wikipedia_fallback": True,
                        "chunks_used": 0,
                        "top_score": 0,
                        "fallback_reason": "not_found_in_knowledge_base"
                    }
                )
                
                retrieval_time = (time.time() - start_time) * 1000
                logger.info(f"Generated Wikipedia fallback concept note for '{concept}' in {retrieval_time:.2f}ms")
                
                return concept_note, retrieval_time
                
        except Exception as e:
            logger.error(f"Error generating Wikipedia fallback: {e}")
            return ConceptNote(
                title=concept,
                definition=f"Error generating concept note for '{concept}': {str(e)}",
                source="error",
                metadata={"error": "wikipedia_fallback_failed", "error_message": str(e)}
            ), (time.time() - start_time) * 1000
    
    def create_searchable_text(self, concept: ConceptNote) -> str:
        """Create searchable text from concept note for better retrieval."""
        searchable_parts = [
            f"Title: {concept.title}",
            f"Definition: {concept.definition}",
        ]
        
        if concept.formula:
            searchable_parts.append(f"Formula: {concept.formula}")
        
        if concept.example:
            searchable_parts.append(f"Example: {concept.example}")
        
        if concept.use_cases:
            searchable_parts.append(f"Use Cases: {', '.join(concept.use_cases)}")
        
        if concept.references:
            searchable_parts.append(f"References: {', '.join(concept.references)}")
        
        return "\n".join(searchable_parts)

