"""
Production RAG Retrieval System - ENTERPRISE VERSION
PDF-first strategy with intelligent Wikipedia fallback and confidence-based routing.

This is the core retrieval component implementing a sophisticated multi-stage
retrieval pipeline with automatic fallback, reranking, and citation tracking.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
from enum import Enum


class RetrievalSource(str, Enum):
    """Source of retrieved content."""
    PDF = "fintbx_pdf"
    WIKIPEDIA = "wikipedia"
    CACHE = "database_cache"


@dataclass
class RetrievalResult:
    """Complete result of a retrieval operation with metadata."""
    query: str
    contexts: List[str]
    source: RetrievalSource
    confidence_score: float
    metadata: Dict[str, Any]
    citations: List[Dict[str, Any]]


class RAGRetriever:
    """
    Enterprise RAG retrieval system with advanced features.
    
    This implements a sophisticated retrieval pipeline:
    
    Stage 1: Query Embedding
    - Converts query to 3072-dim vector
    
    Stage 2: Vector Search
    - Searches PDF corpus via vector DB
    - Retrieves top-K similar chunks
    
    Stage 3: Confidence Assessment
    - Calculates confidence score
    - Considers: avg similarity, result count, score distribution
    
    Stage 4: Source Selection
    - If confidence >= threshold: use PDF
    - If confidence < threshold: fallback to Wikipedia
    - If fallback disabled: return with warning
    
    Stage 5: Context Compilation
    - Compiles retrieved contexts
    - Builds citation information
    - Adds metadata for tracking
    
    Features:
    - PDF-first retrieval strategy
    - Automatic Wikipedia fallback
    - Context reranking
    - Citation tracking with page/section info
    - Confidence scoring with multiple factors
    - Performance monitoring
    - Error recovery
    """
    
    def __init__(self,
                 vector_db,
                 embedding_service,
                 wikipedia_fallback,
                 top_k: int = 5,
                 confidence_threshold: float = 0.7,
                 enable_fallback: bool = True):
        """
        Initialize RAG retriever with all components.
        
        Args:
            vector_db: Vector database client (Pinecone or ChromaDB)
            embedding_service: Embedding service for query encoding
            wikipedia_fallback: Wikipedia fallback service
            top_k: Number of chunks to retrieve
            confidence_threshold: Minimum confidence for PDF results (0.0-1.0)
            enable_fallback: Whether to enable Wikipedia fallback
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.wikipedia_fallback = wikipedia_fallback
        self.top_k = top_k
        self.confidence_threshold = confidence_threshold
        self.enable_fallback = enable_fallback
        
        logger.info(
            f"RAG Retriever initialized: top_k={top_k}, "
            f"threshold={confidence_threshold:.2f}, fallback={enable_fallback}"
        )
    
    def retrieve(self, 
                query: str, 
                namespace: Optional[str] = "financial-toolbox",
                filter_dict: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        """
        Retrieve relevant context for query using PDF-first strategy with fallback.
        
        Complete retrieval pipeline:
        1. Embed query using embedding service
        2. Search PDF corpus via vector database
        3. Calculate confidence score from results
        4. If confidence high enough: use PDF contexts
        5. If confidence low: fallback to Wikipedia
        6. Compile contexts with complete citations
        
        Args:
            query: User query string
            namespace: Vector DB namespace (for Pinecone)
            filter_dict: Metadata filter for search
            
        Returns:
            RetrievalResult with contexts, source, confidence, citations
        """
        logger.info(f"Retrieving context for query: '{query}'")
        
        # Stage 1: Embed query
        logger.debug("Stage 1: Embedding query...")
        query_embedding = self.embedding_service.embed_query(query)
        
        # Stage 2: Search PDF corpus
        logger.debug("Stage 2: Searching PDF corpus...")
        pdf_matches = self._search_pdf_corpus(query_embedding, namespace, filter_dict)
        
        # Stage 3: Calculate confidence
        logger.debug("Stage 3: Calculating confidence...")
        confidence = self._calculate_confidence(pdf_matches)
        
        logger.debug(f"PDF retrieval confidence: {confidence:.3f} (threshold: {self.confidence_threshold:.2f})")
        
        # Stage 4: Decide on source based on confidence
        if confidence >= self.confidence_threshold and pdf_matches:
            # Use PDF results
            result = self._compile_pdf_result(query, pdf_matches, confidence)
            logger.info(
                f"✓ Using PDF results (confidence: {confidence:.3f}, "
                f"matches: {len(pdf_matches)}, top_score: {pdf_matches[0]['score']:.3f})"
            )
        
        elif self.enable_fallback:
            # Fallback to Wikipedia
            logger.info(
                f"PDF confidence too low ({confidence:.3f} < {self.confidence_threshold:.2f}), "
                f"falling back to Wikipedia"
            )
            result = self._fallback_to_wikipedia(query)
        
        else:
            # No fallback enabled, return empty result
            logger.warning(
                f"No confident results (confidence: {confidence:.3f}) "
                f"and fallback is disabled"
            )
            result = RetrievalResult(
                query=query,
                contexts=[],
                source=RetrievalSource.PDF,
                confidence_score=confidence,
                metadata={'matches': 0, 'error': 'Low confidence and no fallback'},
                citations=[]
            )
        
        return result
    
    def _search_pdf_corpus(self,
                          query_embedding: List[float],
                          namespace: Optional[str],
                          filter_dict: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Search PDF corpus via vector database.
        
        Handles both Pinecone and ChromaDB with appropriate method calls.
        """
        try:
            # Different query methods for different DBs
            if hasattr(self.vector_db, 'query'):
                if namespace:
                    # Pinecone with namespace
                    matches = self.vector_db.query(
                        query_embedding=query_embedding,
                        namespace=namespace,
                        top_k=self.top_k,
                        filter_dict=filter_dict
                    )
                else:
                    # ChromaDB without namespace
                    matches = self.vector_db.query(
                        query_embedding=query_embedding,
                        top_k=self.top_k,
                        filter_dict=filter_dict
                    )
            else:
                raise ValueError("Unknown vector DB type")
            
            return matches
            
        except Exception as e:
            logger.error(f"PDF corpus search failed: {e}")
            return []
    
    def _calculate_confidence(self, matches: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score using multi-factor analysis.
        
        Factors considered:
        1. Average similarity score across all matches
        2. Number of matches (penalty if fewer than top_k)
        3. Top result quality (bonus if very high)
        4. Score consistency (bonus if scores are consistent)
        
        Returns:
            Confidence score from 0.0 to 1.0
        """
        if not matches:
            return 0.0
        
        scores = [match['score'] for match in matches]
        
        # Factor 1: Average score
        avg_score = sum(scores) / len(scores)
        
        # Factor 2: Match count penalty (fewer matches = less confident)
        match_penalty = len(matches) / self.top_k
        
        # Factor 3: Top result bonus (very high top score = more confident)
        top_bonus = 1.1 if scores[0] > 0.85 else 1.0
        
        # Factor 4: Consistency bonus (similar scores = more confident)
        if len(scores) > 1:
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            score_std = score_variance ** 0.5
            consistency_bonus = 1.05 if score_std < 0.1 else 1.0
        else:
            consistency_bonus = 1.0
        
        # Combine factors
        confidence = avg_score * match_penalty * top_bonus * consistency_bonus
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _compile_pdf_result(self,
                           query: str,
                           matches: List[Dict[str, Any]],
                           confidence: float) -> RetrievalResult:
        """
        Compile PDF matches into complete retrieval result with citations.
        
        Extracts context and builds proper citations with page/section info.
        """
        contexts = []
        citations = []
        
        for idx, match in enumerate(matches):
            metadata = match.get('metadata', {})
            
            # Get content from metadata or match directly
            content = metadata.get('content', match.get('content', ''))
            if content:
                contexts.append(content)
            
            # Build detailed citation
            citation = {
                'rank': idx + 1,
                'score': match['score'],
                'section': metadata.get('section_title', 'Unknown'),
                'subsection': metadata.get('subsection_title', ''),
                'pages': metadata.get('page_numbers', []),
                'chunk_id': match['id'],
                'element_types': metadata.get('element_types', [])
            }
            citations.append(citation)
        
        # Calculate metadata statistics
        avg_score = sum(m['score'] for m in matches) / len(matches) if matches else 0
        
        return RetrievalResult(
            query=query,
            contexts=contexts,
            source=RetrievalSource.PDF,
            confidence_score=confidence,
            metadata={
                'matches': len(matches),
                'avg_score': avg_score,
                'top_score': matches[0]['score'] if matches else 0,
                'min_score': matches[-1]['score'] if matches else 0
            },
            citations=citations
        )
    
    def _fallback_to_wikipedia(self, query: str) -> RetrievalResult:
        """
        Fallback to Wikipedia when PDF retrieval is insufficient.
        
        Maintains same result structure as PDF retrieval for consistency.
        """
        try:
            wiki_result = self.wikipedia_fallback.retrieve(query)
            
            return RetrievalResult(
                query=query,
                contexts=[wiki_result['content']],
                source=RetrievalSource.WIKIPEDIA,
                confidence_score=wiki_result['confidence'],
                metadata={
                    'wikipedia_page': wiki_result['page_title'],
                    'url': wiki_result['url'],
                    'summary': wiki_result.get('summary', '')
                },
                citations=[{
                    'source': 'Wikipedia',
                    'page_title': wiki_result['page_title'],
                    'url': wiki_result['url'],
                    'type': 'online_encyclopedia'
                }]
            )
            
        except Exception as e:
            logger.error(f"Wikipedia fallback failed for '{query}': {e}")
            
            # Return empty result with error
            return RetrievalResult(
                query=query,
                contexts=[],
                source=RetrievalSource.WIKIPEDIA,
                confidence_score=0.0,
                metadata={'error': str(e), 'fallback_failed': True},
                citations=[]
            )
    
    def retrieve_with_reranking(self, 
                               query: str,
                               rerank_top_n: int = 3) -> RetrievalResult:
        """
        Retrieve with additional reranking step for improved relevance.
        
        First retrieves using standard pipeline, then reranks results
        based on query term overlap (simple reranking).
        
        In production, use cross-encoder models for reranking.
        
        Args:
            query: User query
            rerank_top_n: Number of top results to keep after reranking
            
        Returns:
            RetrievalResult with reranked contexts
        """
        # First get standard retrieval
        result = self.retrieve(query)
        
        if not result.contexts:
            return result
        
        # Simple reranking based on query term overlap
        scored_contexts = []
        query_terms = set(query.lower().split())
        
        for i, context in enumerate(result.contexts):
            context_terms = set(context.lower().split())
            overlap_score = len(query_terms & context_terms)
            scored_contexts.append((overlap_score, i, context))
        
        # Sort by overlap score (descending)
        scored_contexts.sort(reverse=True, key=lambda x: x[0])
        
        # Take top N after reranking
        reranked_contexts = [ctx for _, _, ctx in scored_contexts[:rerank_top_n]]
        reranked_citations = [result.citations[i] for _, i, _ in scored_contexts[:rerank_top_n]]
        
        logger.info(f"Reranked {len(result.contexts)} → {len(reranked_contexts)} contexts")
        
        return RetrievalResult(
            query=result.query,
            contexts=reranked_contexts,
            source=result.source,
            confidence_score=result.confidence_score,
            metadata={**result.metadata, 'reranked': True, 'rerank_method': 'term_overlap'},
            citations=reranked_citations
        )


# Example usage and testing
if __name__ == "__main__":
    from embeddings.embedding_service import EmbeddingService
    from vectordb.pinecone_client import PineconeVectorDB
    from vectordb.chromadb_client import ChromaVectorDB
    from retrieval.wikipedia_fallback import WikipediaFallback
    import os
    
    # Initialize components
    embedding_service = EmbeddingService()
    
    # Use ChromaDB for local testing
    vector_db_type = os.getenv('VECTOR_DB_TYPE', 'chromadb')
    if vector_db_type == 'pinecone':
        vector_db = PineconeVectorDB()
    else:
        vector_db = ChromaVectorDB()
    
    wikipedia_fallback = WikipediaFallback()
    
    # Create retriever
    retriever = RAGRetriever(
        vector_db=vector_db,
        embedding_service=embedding_service,
        wikipedia_fallback=wikipedia_fallback,
        top_k=5,
        confidence_threshold=0.7,
        enable_fallback=True
    )
    
    # Test queries
    test_queries = [
        "What is the Sharpe ratio?",
        "Explain Black-Scholes model",
        "How to calculate bond duration?",
        "What is quantum computing?"  # Should trigger Wikipedia
    ]
    
    print("\n" + "="*70)
    print("RAG RETRIEVER TEST")
    print("="*70)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        try:
            result = retriever.retrieve(query)
            
            print(f"  Source: {result.source}")
            print(f"  Confidence: {result.confidence_score:.3f}")
            print(f"  Contexts: {len(result.contexts)}")
            print(f"  Citations: {len(result.citations)}")
            
            if result.contexts:
                print(f"  First context preview: {result.contexts[0][:100]}...")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "="*70 + "\n")