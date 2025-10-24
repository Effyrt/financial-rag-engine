"""
Advanced query understanding and optimization system.
Uses NLP to enhance user queries before retrieval.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
from loguru import logger
import spacy
from collections import Counter


@dataclass
class QueryAnalysis:
    """Analysis of user query."""
    original_query: str
    cleaned_query: str
    key_terms: List[str]
    query_type: str  # 'definition', 'how_to', 'comparison', 'calculation'
    entities: List[str]
    complexity: float  # 0-1 score
    suggested_searches: List[str]
    intent: str


class QueryOptimizer:
    """
    Advanced query understanding and optimization.
    
    Features:
    - Query intent detection
    - Entity extraction
    - Term expansion with synonyms
    - Query reformulation
    - Complexity scoring
    """
    
    # Financial concept synonyms
    FINANCIAL_SYNONYMS = {
        'sharpe': ['sharpe ratio', 'reward-to-variability', 'risk-adjusted return'],
        'var': ['value at risk', 'VaR'],
        'capm': ['capital asset pricing model', 'capm model'],
        'bs': ['black-scholes', 'black scholes model'],
        'duration': ['bond duration', 'macaulay duration', 'modified duration'],
        'beta': ['beta coefficient', 'systematic risk', 'market beta'],
        'volatility': ['vol', 'standard deviation', 'variance'],
        'option': ['options', 'derivatives', 'calls and puts']
    }
    
    # Query patterns
    QUERY_PATTERNS = {
        'definition': r'^(what is|define|explain|tell me about)',
        'how_to': r'^(how to|how do|calculate|compute)',
        'comparison': r'(vs|versus|compare|difference between)',
        'example': r'(example|show me|demonstrate)',
    }
    
    def __init__(self, load_spacy: bool = True):
        """
        Initialize query optimizer.
        
        Args:
            load_spacy: Whether to load spaCy model (requires download)
        """
        self.nlp = None
        if load_spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model for NLP")
            except Exception as e:
                logger.warning(f"Could not load spaCy: {e}")
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze and optimize user query.
        
        Args:
            query: User's input query
            
        Returns:
            QueryAnalysis with enhanced understanding
        """
        logger.debug(f"Analyzing query: '{query}'")
        
        # Clean query
        cleaned = self._clean_query(query)
        
        # Detect intent
        intent = self._detect_intent(query)
        query_type = self._detect_query_type(query)
        
        # Extract key terms
        key_terms = self._extract_key_terms(cleaned)
        
        # Extract entities (if spaCy available)
        entities = self._extract_entities(cleaned)
        
        # Calculate complexity
        complexity = self._calculate_complexity(query)
        
        # Generate alternative searches
        suggested_searches = self._generate_suggestions(cleaned, key_terms)
        
        analysis = QueryAnalysis(
            original_query=query,
            cleaned_query=cleaned,
            key_terms=key_terms,
            query_type=query_type,
            entities=entities,
            complexity=complexity,
            suggested_searches=suggested_searches,
            intent=intent
        )
        
        logger.debug(f"Query analysis: type={query_type}, complexity={complexity:.2f}")
        return analysis
    
    def optimize_for_retrieval(self, query: str) -> List[str]:
        """
        Generate optimized query variants for better retrieval.
        
        Returns:
            List of query variants to try
        """
        analysis = self.analyze_query(query)
        
        variants = [analysis.cleaned_query]
        
        # Add synonym expansions
        for term in analysis.key_terms:
            term_lower = term.lower()
            if term_lower in self.FINANCIAL_SYNONYMS:
                for synonym in self.FINANCIAL_SYNONYMS[term_lower]:
                    variant = analysis.cleaned_query.replace(term, synonym)
                    if variant not in variants:
                        variants.append(variant)
        
        # Add entity-focused query
        if analysis.entities:
            entity_query = " ".join(analysis.entities)
            if entity_query not in variants:
                variants.append(entity_query)
        
        # Limit to top 3 variants
        return variants[:3]
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query."""
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove special characters
        query = re.sub(r'[^\w\s\-\'\"?]', '', query)
        
        # Remove common filler words
        filler_words = {'um', 'uh', 'like', 'you know'}
        words = query.split()
        words = [w for w in words if w.lower() not in filler_words]
        
        return ' '.join(words)
    
    def _detect_intent(self, query: str) -> str:
        """Detect user intent."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['define', 'what is', 'explain']):
            return 'seek_definition'
        elif any(word in query_lower for word in ['how to', 'calculate', 'compute']):
            return 'seek_procedure'
        elif any(word in query_lower for word in ['example', 'show me']):
            return 'seek_example'
        elif any(word in query_lower for word in ['compare', 'versus', 'difference']):
            return 'seek_comparison'
        else:
            return 'general_inquiry'
    
    def _detect_query_type(self, query: str) -> str:
        """Detect query type using patterns."""
        query_lower = query.lower()
        
        for qtype, pattern in self.QUERY_PATTERNS.items():
            if re.search(pattern, query_lower):
                return qtype
        
        return 'general'
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query."""
        # Remove stopwords
        stopwords = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or',
            'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by'
        }
        
        words = query.lower().split()
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Identify multi-word terms (e.g., "Black Scholes")
        # Look for capitalized adjacent words in original query
        capitalized_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        multi_word_terms = re.findall(capitalized_pattern, query)
        
        key_terms.extend(multi_word_terms)
        
        return list(set(key_terms))
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities using spaCy."""
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(query)
            entities = [ent.text for ent in doc.ents]
            return entities
        except Exception as e:
            logger.debug(f"Entity extraction failed: {e}")
            return []
    
    def _calculate_complexity(self, query: str) -> float:
        """
        Calculate query complexity score.
        
        Factors:
        - Length
        - Technical terms
        - Question structure
        """
        # Base complexity from length
        word_count = len(query.split())
        length_score = min(word_count / 20, 1.0)
        
        # Technical terms increase complexity
        technical_indicators = ['formula', 'equation', 'calculate', 'derive', 'prove']
        has_technical = any(term in query.lower() for term in technical_indicators)
        technical_score = 0.3 if has_technical else 0.0
        
        # Multiple questions increase complexity
        question_marks = query.count('?')
        multi_question_score = min(question_marks * 0.2, 0.3)
        
        complexity = length_score + technical_score + multi_question_score
        return min(complexity, 1.0)
    
    def _generate_suggestions(self, query: str, key_terms: List[str]) -> List[str]:
        """Generate alternative search suggestions."""
        suggestions = []
        
        # Just the key terms
        if key_terms:
            suggestions.append(' '.join(key_terms[:3]))
        
        # Add "finance" or "financial" if not present
        if 'financ' not in query.lower():
            suggestions.append(f"{query} finance")
        
        # Add "definition" for unclear queries
        if len(query.split()) <= 3 and '?' not in query:
            suggestions.append(f"{query} definition")
        
        return list(set(suggestions))[:3]


# Example usage
if __name__ == "__main__":
    optimizer = QueryOptimizer(load_spacy=False)
    
    test_queries = [
        "What is the Sharpe Ratio?",
        "How to calculate Black-Scholes option pricing?",
        "Duration vs Convexity comparison",
        "VaR"
    ]
    
    for query in test_queries:
        analysis = optimizer.analyze_query(query)
        print(f"\nQuery: {query}")
        print(f"Type: {analysis.query_type}")
        print(f"Intent: {analysis.intent}")
        print(f"Key Terms: {analysis.key_terms}")
        print(f"Complexity: {analysis.complexity:.2f}")
        
        variants = optimizer.optimize_for_retrieval(query)
        print(f"Optimized Variants: {variants}")