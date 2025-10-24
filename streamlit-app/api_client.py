import time
import random
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class ConceptNote(BaseModel):
    """Structured concept note"""
    concept: str
    definition: str
    key_points: list[str]
    examples: list[str]
    references: list[str]
    source: str  # "fintbx.pdf" or "wikipedia"
    cached: bool
    generation_time: Optional[float] = None
    timestamp: str


class MockAPIClient:
    """Mock FastAPI Client for developing Streamlit UI"""
    
    def __init__(self, use_real_api: bool = False, api_url: str = "http://localhost:8000"):
        self.use_real_api = use_real_api
        self.api_url = api_url
        
    def query_concept(self, concept: str) -> Dict[str, Any]:
        """
        Query concept note
        
        If use_real_api=True, calls real FastAPI
        Otherwise returns mock data
        """
        if self.use_real_api:
            return self._call_real_api(concept)
        else:
            return self._mock_query(concept)
    
    def _mock_query(self, concept: str) -> Dict[str, Any]:
        """Generate mock response"""
        
        # Simulate API latency
        time.sleep(random.uniform(0.5, 2.0))
        
        # Predefined financial concepts (simulating concepts in fintbx.pdf)
        fintbx_concepts = [
            "Credit Default Swap",
            "Collateralized Debt Obligation",
            "Value at Risk",
            "Black-Scholes Model",
            "Portfolio Theory",
            "Capital Asset Pricing Model",
            "Efficient Market Hypothesis"
        ]
        
        # Check if concept is in textbook
        is_in_textbook = any(c.lower() in concept.lower() for c in fintbx_concepts)
        
        # Check if cached (random simulation)
        is_cached = random.choice([True, False])
        
        if is_in_textbook:
            # Generate note from fintbx.pdf
            note = self._generate_fintbx_note(concept, is_cached)
        else:
            # Wikipedia fallback
            note = self._generate_wikipedia_note(concept)
        
        return note.dict()
    
    def _generate_fintbx_note(self, concept: str, is_cached: bool) -> ConceptNote:
        """Generate mock note from fintbx.pdf"""
        
        generation_time = 0.0 if is_cached else random.uniform(2.0, 5.0)
        
        return ConceptNote(
            concept=concept,
            definition=f"{concept} is an important financial concept involving risk management and asset pricing. It plays a key role in modern financial theory.",
            key_points=[
                f"Core principle of {concept} is based on market efficiency hypothesis",
                "Widely applied in risk assessment and portfolio management",
                "Requires consideration of market conditions and regulatory environment",
                "Closely related to other financial instruments and theories"
            ],
            examples=[
                f"Example 1: Application of {concept} in the 2008 financial crisis",
                f"Example 2: How modern investment banks use {concept}",
                f"Example 3: Risk management practices for {concept}"
            ],
            references=[
                "Chapter 4, Section 4.2 (Page 87-92)",
                "Chapter 7, Section 7.1 (Page 156-158)",
                "Appendix B (Page 342)"
            ],
            source="fintbx.pdf",
            cached=is_cached,
            generation_time=generation_time,
            timestamp=datetime.now().isoformat()
        )
    
    def _generate_wikipedia_note(self, concept: str) -> ConceptNote:
        """Generate mock note from Wikipedia"""
        
        return ConceptNote(
            concept=concept,
            definition=f"{concept} is a concept (Source: Wikipedia). Note: This content is not in the textbook.",
            key_points=[
                f"Basic introduction to {concept}",
                "Related background information",
                "Potential application areas"
            ],
            examples=[
                f"Wikipedia example 1",
                f"Wikipedia example 2"
            ],
            references=[
                "Wikipedia Article",
                "External Sources"
            ],
            source="wikipedia",
            cached=False,
            generation_time=random.uniform(3.0, 6.0),
            timestamp=datetime.now().isoformat()
        )
    
    def _call_real_api(self, concept: str) -> Dict[str, Any]:
        """Call real FastAPI"""
        import requests
        
        try:
            # Try POST first (correct method per assignment)
            response = requests.post(
                f"{self.api_url}/query",
                json={"concept": concept},
                timeout=60
            )
            
            # If POST returns 405, fall back to GET
            if response.status_code == 405:
                response = requests.get(
                    f"{self.api_url}/query",
                    params={"concept": concept},
                    timeout=60
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Ensure response has required fields
            if 'concept' not in data:
                data['concept'] = concept
            if 'cached' not in data:
                data['cached'] = False
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            if 'key_points' not in data:
                data['key_points'] = []
            if 'examples' not in data:
                data['examples'] = []
            if 'references' not in data:
                data['references'] = []
            
            return data
            
        except requests.exceptions.Timeout:
            raise Exception(f"API request timed out. The service might be starting up (cold start). Please try again.")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to API at {self.api_url}. Please check the URL and network connection.")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"API returned error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")


# Testing function
if __name__ == "__main__":
    client = MockAPIClient(use_real_api=False)
    
    # Test textbook concept
    print("=== Test: Credit Default Swap ===")
    result = client.query_concept("Credit Default Swap")
    print(f"Source: {result['source']}")
    print(f"Cached: {result['cached']}")
    print(f"Definition: {result['definition']}\n")
    
    # Test Wikipedia fallback
    print("=== Test: Quantum Computing ===")
    result = client.query_concept("Quantum Computing")
    print(f"Source: {result['source']}")
    print(f"Definition: {result['definition']}")