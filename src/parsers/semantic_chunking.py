"""
Advanced semantic chunking strategies with embedding-based similarity.
Uses sentence transformers for intelligent chunk boundary detection.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from loguru import logger
import numpy as np
import re
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SemanticChunk:
    """Enhanced chunk with semantic metadata."""
    content: str
    chunk_id: str
    page_numbers: List[int]
    section_title: str
    subsection_title: str
    element_types: List[str]
    char_count: int
    token_count: int
    semantic_score: float  # Semantic coherence score
    keywords: List[str]
    embedding_preview: Optional[List[float]] = None  # First 10 dims for preview
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SemanticChunker:
    """
    Advanced semantic chunking using sentence embeddings.
    
    Features:
    - Embedding-based boundary detection
    - Semantic coherence scoring
    - Keyword extraction
    - Multi-strategy chunking
    - Adaptive chunk sizing
    - Context preservation
    """
    
    def __init__(self,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 model_name: str = 'all-MiniLM-L6-v2',
                 similarity_threshold: float = 0.5,
                 preserve_code: bool = True,
                 preserve_formulas: bool = True):
        """
        Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            model_name: Sentence transformer model
            similarity_threshold: Threshold for semantic boundaries
            preserve_code: Keep code blocks intact
            preserve_formulas: Keep formulas intact
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        self.preserve_code = preserve_code
        self.preserve_formulas = preserve_formulas
        
        # Initialize sentence transformer for semantic analysis
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Base splitter for fallback
        self.base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n\n", "\n\n", "\n", ". ", ", ", " ", ""]
        )
        
        logger.info(f"SemanticChunker initialized: size={chunk_size}, overlap={chunk_overlap}")
    
    def chunk_document(self, parsed_elements: List[Any]) -> List[SemanticChunk]:
        """
        Main chunking method with semantic analysis.
        
        Args:
            parsed_elements: List of ParsedElement objects
            
        Returns:
            List of SemanticChunk objects
        """
        logger.info(f"Starting semantic chunking for {len(parsed_elements)} elements")
        
        chunks = []
        current_section = None
        current_subsection = None
        text_buffer = []
        buffer_metadata = []
        
        for element in parsed_elements:
            # Update section tracking
            if element.section_title != current_section:
                # Flush buffer when section changes
                if text_buffer:
                    section_chunks = self._process_buffer(
                        text_buffer, 
                        buffer_metadata,
                        current_section,
                        current_subsection
                    )
                    chunks.extend(section_chunks)
                    text_buffer = []
                    buffer_metadata = []
                
                current_section = element.section_title
                current_subsection = element.subsection_title
            
            # Handle special elements
            if element.element_type == 'code' and self.preserve_code:
                # Flush buffer and create code chunk
                if text_buffer:
                    section_chunks = self._process_buffer(
                        text_buffer, buffer_metadata, current_section, current_subsection
                    )
                    chunks.extend(section_chunks)
                    text_buffer = []
                    buffer_metadata = []
                
                chunks.append(self._create_code_chunk(element))
                
            elif element.element_type == 'formula' and self.preserve_formulas:
                # Similar to code
                if text_buffer:
                    section_chunks = self._process_buffer(
                        text_buffer, buffer_metadata, current_section, current_subsection
                    )
                    chunks.extend(section_chunks)
                    text_buffer = []
                    buffer_metadata = []
                
                chunks.append(self._create_formula_chunk(element))
                
            elif element.element_type == 'table':
                # Tables get their own chunks
                if text_buffer:
                    section_chunks = self._process_buffer(
                        text_buffer, buffer_metadata, current_section, current_subsection
                    )
                    chunks.extend(section_chunks)
                    text_buffer = []
                    buffer_metadata = []
                
                chunks.append(self._create_table_chunk(element))
                
            else:
                # Add to buffer
                text_buffer.append(element.content)
                buffer_metadata.append(element)
        
        # Flush remaining buffer
        if text_buffer:
            section_chunks = self._process_buffer(
                text_buffer, buffer_metadata, current_section, current_subsection
            )
            chunks.extend(section_chunks)
        
        # Post-process chunks
        chunks = self._post_process_chunks(chunks)
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def _process_buffer(self, 
                       text_buffer: List[str],
                       metadata_buffer: List[Any],
                       section: str,
                       subsection: str) -> List[SemanticChunk]:
        """Process text buffer with semantic chunking."""
        # Combine text
        combined_text = "\n\n".join(text_buffer)
        
        # If text is small enough, create single chunk
        if len(combined_text) <= self.chunk_size:
            return [self._create_chunk_from_buffer(
                combined_text, metadata_buffer, section, subsection, 1.0
            )]
        
        # Split into sentences for semantic analysis
        sentences = self._split_into_sentences(combined_text)
        
        if len(sentences) <= 3:
            # Too few sentences for semantic chunking, use base splitter
            return self._fallback_chunking(combined_text, metadata_buffer, section, subsection)
        
        # Perform semantic chunking
        try:
            return self._semantic_split(
                sentences, metadata_buffer, section, subsection
            )
        except Exception as e:
            logger.warning(f"Semantic chunking failed, using fallback: {e}")
            return self._fallback_chunking(combined_text, metadata_buffer, section, subsection)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _semantic_split(self,
                       sentences: List[str],
                       metadata_buffer: List[Any],
                       section: str,
                       subsection: str) -> List[SemanticChunk]:
        """
        Split sentences into semantically coherent chunks.
        
        Uses embedding similarity to find natural boundaries.
        """
        # Generate embeddings for sentences
        sentence_embeddings = self.embedding_model.encode(sentences)
        
        # Calculate similarity between consecutive sentences
        similarities = []
        for i in range(len(sentence_embeddings) - 1):
            sim = cosine_similarity(
                sentence_embeddings[i].reshape(1, -1),
                sentence_embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)
        
        # Find boundaries where similarity drops
        boundaries = [0]
        current_chunk_size = 0
        
        for i, (sentence, sim) in enumerate(zip(sentences, similarities + [1.0])):
            current_chunk_size += len(sentence)
            
            # Check if we should create a boundary
            should_split = (
                (sim < self.similarity_threshold) or  # Low semantic similarity
                (current_chunk_size >= self.chunk_size)  # Size threshold
            )
            
            if should_split and current_chunk_size >= self.chunk_size * 0.5:
                boundaries.append(i + 1)
                current_chunk_size = 0
        
        boundaries.append(len(sentences))
        
        # Create chunks from boundaries
        chunks = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            
            # Add overlap
            if i > 0:
                overlap_sentences = max(1, int(self.chunk_overlap / 100))  # Approximate
                start = max(0, start - overlap_sentences)
            
            chunk_sentences = sentences[start:end]
            chunk_text = " ".join(chunk_sentences)
            
            # Calculate semantic coherence
            if len(chunk_sentences) > 1:
                chunk_embeddings = self.embedding_model.encode(chunk_sentences)
                coherence = np.mean([
                    cosine_similarity(
                        chunk_embeddings[j].reshape(1, -1),
                        chunk_embeddings[j + 1].reshape(1, -1)
                    )[0][0]
                    for j in range(len(chunk_embeddings) - 1)
                ])
            else:
                coherence = 1.0
            
            chunk = self._create_chunk_from_buffer(
                chunk_text, metadata_buffer, section, subsection, coherence
            )
            chunks.append(chunk)
        
        return chunks
    
    def _fallback_chunking(self,
                          text: str,
                          metadata_buffer: List[Any],
                          section: str,
                          subsection: str) -> List[SemanticChunk]:
        """Fallback to base splitter when semantic chunking fails."""
        text_chunks = self.base_splitter.split_text(text)
        
        chunks = []
        for chunk_text in text_chunks:
            chunk = self._create_chunk_from_buffer(
                chunk_text, metadata_buffer, section, subsection, 0.7
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_from_buffer(self,
                                  text: str,
                                  metadata_buffer: List[Any],
                                  section: str,
                                  subsection: str,
                                  semantic_score: float) -> SemanticChunk:
        """Create semantic chunk from buffer."""
        # Extract metadata
        page_numbers = list(set(
            elem.page_number for elem in metadata_buffer if hasattr(elem, 'page_number')
        ))
        element_types = list(set(
            elem.element_type for elem in metadata_buffer if hasattr(elem, 'element_type')
        ))
        
        # Extract keywords (simple TF-IDF-like approach)
        keywords = self._extract_keywords(text)
        
        # Generate embedding preview (first 10 dimensions)
        embedding = self.embedding_model.encode([text])[0]
        embedding_preview = embedding[:10].tolist()
        
        return SemanticChunk(
            content=text,
            chunk_id="",  # Will be set later
            page_numbers=sorted(page_numbers) if page_numbers else [0],
            section_title=section or "Unknown",
            subsection_title=subsection or "",
            element_types=element_types or ['text'],
            char_count=len(text),
            token_count=self._estimate_tokens(text),
            semantic_score=semantic_score,
            keywords=keywords,
            embedding_preview=embedding_preview,
            metadata={
                'source_elements': len(metadata_buffer),
                'has_code': 'code' in element_types,
                'has_formula': 'formula' in element_types
            }
        )
    
    def _create_code_chunk(self, element: Any) -> SemanticChunk:
        """Create specialized chunk for code."""
        keywords = self._extract_keywords(element.content)
        
        return SemanticChunk(
            content=f"```matlab\n{element.content}\n```",
            chunk_id="",
            page_numbers=[element.page_number],
            section_title=element.section_title or "Unknown",
            subsection_title=element.subsection_title or "",
            element_types=['code'],
            char_count=len(element.content),
            token_count=self._estimate_tokens(element.content),
            semantic_score=1.0,
            keywords=keywords,
            metadata={'is_code_block': True, 'language': 'matlab'}
        )
    
    def _create_formula_chunk(self, element: Any) -> SemanticChunk:
        """Create specialized chunk for formulas."""
        keywords = self._extract_keywords(element.content)
        
        return SemanticChunk(
            content=element.content,
            chunk_id="",
            page_numbers=[element.page_number],
            section_title=element.section_title or "Unknown",
            subsection_title=element.subsection_title or "",
            element_types=['formula'],
            char_count=len(element.content),
            token_count=self._estimate_tokens(element.content),
            semantic_score=1.0,
            keywords=keywords,
            metadata={'is_formula': True}
        )
    
    def _create_table_chunk(self, element: Any) -> SemanticChunk:
        """Create specialized chunk for tables."""
        keywords = self._extract_keywords(element.content)
        
        return SemanticChunk(
            content=element.content,
            chunk_id="",
            page_numbers=[element.page_number],
            section_title=element.section_title or "Unknown",
            subsection_title=element.subsection_title or "",
            element_types=['table'],
            char_count=len(element.content),
            token_count=self._estimate_tokens(element.content),
            semantic_score=1.0,
            keywords=keywords,
            metadata={'is_table': True}
        )
    
    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract keywords from text using simple frequency analysis."""
        # Remove common words and extract important terms
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Common stopwords
        stopwords = {
            'this', 'that', 'with', 'from', 'have', 'been', 'will', 
            'would', 'could', 'should', 'their', 'there', 'where', 'when'
        }
        
        # Filter and count
        word_freq = {}
        for word in words:
            if word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4
    
    def _post_process_chunks(self, chunks: List[SemanticChunk]) -> List[SemanticChunk]:
        """Post-process chunks: assign IDs, validate, etc."""
        for idx, chunk in enumerate(chunks):
            chunk.chunk_id = f"chunk_{idx:05d}"
        
        return chunks
    
    def get_statistics(self, chunks: List[SemanticChunk]) -> Dict[str, Any]:
        """Get statistics about chunks."""
        if not chunks:
            return {}
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': np.mean([c.char_count for c in chunks]),
            'avg_semantic_score': np.mean([c.semantic_score for c in chunks]),
            'avg_tokens': np.mean([c.token_count for c in chunks]),
            'code_chunks': sum(1 for c in chunks if 'code' in c.element_types),
            'formula_chunks': sum(1 for c in chunks if 'formula' in c.element_types),
            'table_chunks': sum(1 for c in chunks if 'table' in c.element_types),
            'unique_sections': len(set(c.section_title for c in chunks))
        }


# Example usage
if __name__ == "__main__":
    from advanced_pdf_parser import FinancialToolboxParser
    
    # Parse PDF
    parser = FinancialToolboxParser()
    parsed_doc = parser.parse("data/raw/fintbx.pdf")
    
    # Semantic chunking
    chunker = SemanticChunker(
        chunk_size=1000,
        chunk_overlap=200,
        similarity_threshold=0.5
    )
    
    chunks = chunker.chunk_document(parsed_doc.elements)
    stats = chunker.get_statistics(chunks)
    
    print(f"\nSemantic Chunking Results:")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Avg semantic score: {stats['avg_semantic_score']:.3f}")
    print(f"Avg chunk size: {stats['avg_chunk_size']:.0f} chars")