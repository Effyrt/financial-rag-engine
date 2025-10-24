"""
Wikipedia Fallback Service - ENTERPRISE VERSION  
Intelligent Wikipedia integration for comprehensive concept coverage.
"""

from typing import Dict, Any, Optional
import wikipedia
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import re


class WikipediaFallback:
    """
    Enterprise Wikipedia fallback service.
    
    Features:
    - Intelligent page selection with disambiguation handling
    - Content extraction with section awareness
    - Confidence scoring based on relevance
    - Query optimization for financial concepts
    - Error handling with graceful degradation
    - Multi-attempt retrieval with fallback options
    """
    
    def __init__(self,
                 lang: str = "en",
                 sentences: int = 5,
                 auto_suggest: bool = True):
        """Initialize Wikipedia fallback service."""
        self.lang = lang
        self.sentences = sentences
        self.auto_suggest = auto_suggest
        wikipedia.set_lang(lang)
        
        logger.info(f"Wikipedia fallback initialized: lang={lang}, sentences={sentences}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def retrieve(self, query: str) -> Dict[str, Any]:
        """Retrieve content from Wikipedia with retry logic."""
        logger.info(f"Wikipedia retrieval for: '{query}'")
        
        try:
            clean_query = self._clean_query(query)
            search_results = wikipedia.search(clean_query, results=5)
            
            if not search_results:
                logger.warning(f"No Wikipedia results for '{query}'")
                return self._empty_result(query)
            
            # Try to get best matching page
            page = None
            for page_title in search_results:
                try:
                    page = wikipedia.page(page_title, auto_suggest=self.auto_suggest)
                    break
                except wikipedia.exceptions.DisambiguationError as e:
                    try:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        break
                    except:
                        continue
                except wikipedia.exceptions.PageError:
                    continue
                except Exception as e:
                    logger.warning(f"Error retrieving '{page_title}': {e}")
                    continue
            
            if not page:
                logger.warning(f"Could not retrieve Wikipedia page for '{query}'")
                return self._empty_result(query)
            
            # Extract content
            content = self._extract_content(page, clean_query)
            confidence = self._calculate_confidence(page, clean_query)
            
            result = {
                'page_title': page.title,
                'content': content,
                'url': page.url,
                'confidence': confidence,
                'summary': page.summary[:500]
            }
            
            logger.info(f"✓ Retrieved Wikipedia: '{page.title}' (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Wikipedia retrieval failed for '{query}': {e}")
            return self._empty_result(query, error=str(e))
    
    def _clean_query(self, query: str) -> str:
        """Clean and optimize query for Wikipedia search."""
        query = re.sub(r'\b(what is|explain|define|how to|tell me about)\b', '', query, flags=re.IGNORECASE)
        query = re.sub(r'[^\w\s-]', '', query)
        query = ' '.join(query.split())
        return query.strip()
    
    def _extract_content(self, page, query: str) -> str:
        """Extract relevant content from Wikipedia page."""
        content_parts = [page.summary]
        
        query_terms = set(query.lower().split())
        
        for section_title in page.sections[:10]:
            section_terms = set(section_title.lower().split())
            if query_terms & section_terms:
                try:
                    section_content = page.section(section_title)
                    if section_content and len(section_content) > 50:
                        content_parts.append(f"\n\n## {section_title}\n{section_content[:1000]}")
                except:
                    continue
        
        full_content = ''.join(content_parts)
        if len(full_content) > 5000:
            full_content = full_content[:5000] + "..."
        
        return full_content
    
    def _calculate_confidence(self, page, query: str) -> float:
        """Calculate confidence score for Wikipedia result."""
        confidence = 0.5
        
        query_lower = query.lower()
        title_lower = page.title.lower()
        
        if query_lower in title_lower or title_lower in query_lower:
            confidence += 0.2
        
        query_terms = set(query_lower.split())
        summary_terms = set(page.summary.lower().split())
        term_overlap = len(query_terms & summary_terms) / len(query_terms) if query_terms else 0
        confidence += term_overlap * 0.2
        
        if len(page.content) > 5000:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _empty_result(self, query: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'page_title': '',
            'content': f"No Wikipedia information found for: {query}",
            'url': '',
            'confidence': 0.0,
            'summary': '',
            'error': error
        }
    
    def get_financial_concept(self, concept_name: str) -> Dict[str, Any]:
        """Specialized method for financial concepts with query expansion."""
        financial_terms = [
            concept_name,
            f"{concept_name} finance",
            f"{concept_name} financial",
            f"{concept_name} economics"
        ]
        
        best_result = None
        best_confidence = 0.0
        
        for term in financial_terms:
            result = self.retrieve(term)
            if result['confidence'] > best_confidence:
                best_result = result
                best_confidence = result['confidence']
            
            if best_confidence > 0.8:
                break
        
        return best_result or self._empty_result(concept_name)


if __name__ == "__main__":
    fallback = WikipediaFallback()
    
    test_queries = ["Sharpe Ratio", "Black-Scholes", "Duration", "VaR"]
    
    for query in test_queries:
        result = fallback.retrieve(query)
        print(f"\n{query}: {result['page_title']} ({result['confidence']:.2f})")