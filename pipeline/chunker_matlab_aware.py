"""
MATLAB Function-Aware Chunking Strategy.

This chunking strategy specifically preserves MATLAB function information
and creates function-specific chunks for better retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

logger = logging.getLogger(__name__)


class MATLABFunctionAwareChunker:
    """
    Chunking strategy that preserves MATLAB function information.
    
    Features:
    - Creates function-specific chunks
    - Preserves function signatures with documentation
    - Maintains code examples with explanations
    - Groups related functions together
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        """Initialize chunker."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # MATLAB function patterns
        self.function_patterns = [
            r'\b(bnd\w+)\s*\(',  # Bond functions
            r'\b(port\w+)\s*\(',  # Portfolio functions
            r'\b(datetime|datenum|datestr)\s*\(',  # Date functions
            r'\b(busdate|holidays)\s*\(',  # Business functions
            r'\b(irr|npv|xirr)\s*\(',  # Financial calculations
        ]
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Chunk text with MATLAB function awareness."""
        if metadata is None:
            metadata = {}
        
        # First, extract MATLAB functions and their context
        function_chunks = self._create_function_chunks(text, metadata)
        
        # Then, create regular text chunks
        regular_chunks = self._create_regular_chunks(text, metadata)
        
        # Combine and deduplicate
        all_chunks = function_chunks + regular_chunks
        all_chunks = self._deduplicate_chunks(all_chunks)
        
        # Add chunk metadata
        for i, chunk in enumerate(all_chunks):
            chunk['chunk_id'] = f"{metadata.get('topic', 'general')}_{i}"
            chunk['chunk_type'] = chunk.get('chunk_type', 'text')
            chunk['char_count'] = len(chunk['chunk_text'])
        
        logger.info(f"Created {len(all_chunks)} chunks ({len(function_chunks)} function-specific)")
        return all_chunks
    
    def _create_function_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks specifically for MATLAB functions."""
        function_chunks = []
        
        # Find all function occurrences
        functions_found = set()
        for pattern in self.function_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                func_name = match.group(1)
                functions_found.add(func_name)
        
        # Create chunks for each function
        for func_name in functions_found:
            func_chunk = self._extract_function_chunk(text, func_name, metadata)
            if func_chunk:
                function_chunks.append(func_chunk)
        
        return function_chunks
    
    def _extract_function_chunk(self, text: str, func_name: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract comprehensive information about a specific function."""
        lines = text.split('\n')
        func_info = {
            'function_name': func_name,
            'signatures': [],
            'examples': [],
            'descriptions': [],
            'related_functions': []
        }
        
        # Find all occurrences of this function
        for i, line in enumerate(lines):
            if func_name.lower() in line.lower():
                line = line.strip()
                
                # Check if it's a function signature/example
                if self._is_function_signature(line):
                    func_info['signatures'].append(line)
                elif self._is_function_example(line):
                    func_info['examples'].append(line)
                elif self._is_function_description(line):
                    func_info['descriptions'].append(line)
        
        # Create chunk text
        chunk_text_parts = []
        
        # Add function name and category
        chunk_text_parts.append(f"MATLAB Function: {func_name}")
        chunk_text_parts.append(f"Category: {self._categorize_function(func_name)}")
        
        # Add signatures
        if func_info['signatures']:
            chunk_text_parts.append("Function Signatures:")
            for sig in func_info['signatures'][:3]:  # Limit to 3 signatures
                chunk_text_parts.append(f"  {sig}")
        
        # Add examples
        if func_info['examples']:
            chunk_text_parts.append("Usage Examples:")
            for example in func_info['examples'][:3]:  # Limit to 3 examples
                chunk_text_parts.append(f"  {example}")
        
        # Add descriptions
        if func_info['descriptions']:
            chunk_text_parts.append("Description:")
            for desc in func_info['descriptions'][:2]:  # Limit to 2 descriptions
                chunk_text_parts.append(f"  {desc}")
        
        chunk_text = '\n'.join(chunk_text_parts)
        
        if len(chunk_text) > 50:  # Only create chunk if substantial content
            return {
                'chunk_text': chunk_text,
                'chunk_type': 'matlab_function',
                'function_name': func_name,
                'function_category': self._categorize_function(func_name),
                'signature_count': len(func_info['signatures']),
                'example_count': len(func_info['examples']),
                'metadata': metadata
            }
        
        return None
    
    def _create_regular_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create regular text chunks."""
        chunks = self.text_splitter.split_text(text)
        
        regular_chunks = []
        for i, chunk_text in enumerate(chunks):
            if len(chunk_text.strip()) > 50:  # Only meaningful chunks
                regular_chunks.append({
                    'chunk_text': chunk_text.strip(),
                    'chunk_type': 'text',
                    'metadata': metadata
                })
        
        return regular_chunks
    
    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks."""
        seen_texts = set()
        unique_chunks = []
        
        for chunk in chunks:
            text_hash = hash(chunk['chunk_text'])
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _is_function_signature(self, line: str) -> bool:
        """Check if line contains a function signature."""
        return bool(re.search(r'\w+\s*\([^)]*\)\s*(?:=|ans\s*=)', line))
    
    def _is_function_example(self, line: str) -> bool:
        """Check if line is a function usage example."""
        return bool(re.search(r'\w+\s*\([^)]*\)\s*(?:ans\s*=|\w+\s*=)', line))
    
    def _is_function_description(self, line: str) -> bool:
        """Check if line describes a function."""
        # Look for descriptive text that's not a function call
        if re.search(r'\w+\s*\([^)]*\)', line):
            return False
        
        # Check for descriptive keywords
        desc_keywords = ['function', 'calculates', 'computes', 'returns', 'determines']
        return any(keyword in line.lower() for keyword in desc_keywords)
    
    def _categorize_function(self, func_name: str) -> str:
        """Categorize MATLAB function."""
        func_lower = func_name.lower()
        
        if func_lower.startswith('bnd'):
            return 'bond_functions'
        elif func_lower.startswith('port'):
            return 'portfolio_functions'
        elif 'date' in func_lower:
            return 'date_functions'
        elif func_lower in ['irr', 'npv', 'xirr']:
            return 'financial_calculations'
        else:
            return 'other_functions'


class MATLABFunctionChunkingStrategy:
    """Wrapper class for the MATLAB function-aware chunking strategy."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        """Initialize strategy."""
        self.chunker = MATLABFunctionAwareChunker(chunk_size, chunk_overlap)
        self.name = f"matlab_function_aware_{chunk_size}_{chunk_overlap}"
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Chunk text using MATLAB function-aware strategy."""
        return self.chunker.chunk_text(text, metadata)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information."""
        return {
            'name': self.name,
            'description': 'MATLAB function-aware chunking that preserves function signatures and examples',
            'chunk_size': self.chunker.chunk_size,
            'chunk_overlap': self.chunker.chunk_overlap,
            'features': [
                'Function-specific chunks',
                'Preserved signatures',
                'Code examples with context',
                'Function categorization'
            ]
        }


def main():
    """Test the MATLAB function-aware chunking strategy."""
    # Sample MATLAB documentation text
    sample_text = """
    Bond Pricing Functions
    
    The bndprice function calculates the price of a bond given its yield to maturity.
    
    Syntax:
    Price = bndprice(Yield, CouponRate, Settle, Maturity)
    
    Example:
    Yield = 0.07;
    CouponRate = 0.08;
    Settle = datenum('17-May-2000');
    Maturity = datenum('01-Oct-2000');
    Price = bndprice(Yield, CouponRate, Settle, Maturity)
    ans = 100.3503
    
    The bndyield function calculates the yield to maturity given the bond price.
    
    Syntax:
    Yield = bndyield(Price, CouponRate, Settle, Maturity)
    
    Example:
    Price = 100.3503;
    Yield = bndyield(Price, CouponRate, Settle, Maturity)
    ans = 0.07
    """
    
    strategy = MATLABFunctionChunkingStrategy(chunk_size=500, chunk_overlap=50)
    chunks = strategy.chunk_text(sample_text, {'topic': 'bond_functions'})
    
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n{i}. Type: {chunk.get('chunk_type', 'text')}")
        print(f"   Text: {chunk['chunk_text'][:200]}...")
        if chunk.get('chunk_type') == 'matlab_function':
            print(f"   Function: {chunk.get('function_name')}")
            print(f"   Category: {chunk.get('function_category')}")


if __name__ == "__main__":
    main()
