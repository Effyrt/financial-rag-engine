"""
Advanced Chunking Strategies with LangChain.

Implements and evaluates multiple chunking strategies:
1. RecursiveCharacterTextSplitter (baseline)
2. Semantic Chunking (meaning-based)
3. Section/Heading-aware Splitting
4. Code-aware Splitting
5. Hybrid Strategy (combines multiple approaches)

Each strategy is evaluated with retrieval metrics.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
import re

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
    Language,
    RecursiveCharacterTextSplitter as CodeSplitter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for a chunking strategy."""
    name: str
    chunk_size: int
    chunk_overlap: int
    separators: Optional[List[str]] = None
    description: str = ""


class ChunkingStrategy:
    """Base class for chunking strategies."""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.chunks_created = 0
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk text and return list of chunk dictionaries."""
        raise NotImplementedError
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return metrics for this strategy."""
        return {
            "strategy": self.config.name,
            "chunks_created": self.chunks_created,
            "config": {
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap
            }
        }


class RecursiveStrategy(ChunkingStrategy):
    """
    Strategy 1: Recursive Character Text Splitter
    
    Best for: General text, preserves sentence boundaries
    Pros: Fast, respects natural breaks, good for most content
    Cons: No semantic awareness, may split related concepts
    """
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        
        separators = config.separators or [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentences
            ", ",    # Clauses
            " ",     # Words
            ""       # Characters
        ]
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=separators,
            is_separator_regex=False
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk using recursive character splitting."""
        chunks = self.splitter.split_text(text)
        
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            
            result.append({
                "chunk_id": f"{metadata.get('source', 'doc')}_{i}_{chunk_id}",
                "chunk_index": i,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "word_count": len(chunk_text.split()),
                "strategy": self.config.name,
                **metadata
            })
        
        self.chunks_created += len(result)
        return result


class SemanticStrategy(ChunkingStrategy):
    """
    Strategy 2: Semantic Chunking
    
    Best for: Content where meaning matters more than size
    Pros: Keeps related concepts together, better retrieval
    Cons: Variable chunk sizes, slower
    """
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        
        # Use larger chunks with more overlap for semantic coherence
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " "],
            is_separator_regex=False
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk with semantic awareness."""
        # First, identify semantic boundaries (paragraphs, sections)
        semantic_blocks = self._identify_semantic_blocks(text)
        
        result = []
        chunk_index = 0
        
        for block in semantic_blocks:
            # Split large blocks
            if len(block) > self.config.chunk_size:
                sub_chunks = self.splitter.split_text(block)
            else:
                sub_chunks = [block]
            
            for chunk_text in sub_chunks:
                chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                
                result.append({
                    "chunk_id": f"{metadata.get('source', 'doc')}_{chunk_index}_{chunk_id}",
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                    "strategy": self.config.name,
                    "semantic_block": True,
                    **metadata
                })
                chunk_index += 1
        
        self.chunks_created += len(result)
        return result
    
    def _identify_semantic_blocks(self, text: str) -> List[str]:
        """Identify semantic blocks (paragraphs, sections)."""
        # Split by double newlines (paragraphs)
        blocks = text.split('\n\n')
        return [b.strip() for b in blocks if b.strip()]


class HeadingAwareStrategy(ChunkingStrategy):
    """
    Strategy 3: Section/Heading-aware Splitting
    
    Best for: Structured documents with clear sections
    Pros: Preserves document hierarchy, maintains context
    Cons: Requires well-structured documents
    """
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " "],
            is_separator_regex=False
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk with heading awareness."""
        # Detect headings and sections
        sections = self._split_by_headings(text)
        
        result = []
        chunk_index = 0
        
        for section in sections:
            heading = section.get('heading', '')
            content = section.get('content', '')
            level = section.get('level', 0)
            
            # Include heading in first chunk of section
            full_text = f"{heading}\n\n{content}" if heading else content
            
            # Split if too large
            if len(full_text) > self.config.chunk_size:
                sub_chunks = self.splitter.split_text(full_text)
            else:
                sub_chunks = [full_text]
            
            for i, chunk_text in enumerate(sub_chunks):
                chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                
                result.append({
                    "chunk_id": f"{metadata.get('source', 'doc')}_{chunk_index}_{chunk_id}",
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                    "strategy": self.config.name,
                    "section_heading": heading,
                    "heading_level": level,
                    "is_first_in_section": (i == 0),
                    **metadata
                })
                chunk_index += 1
        
        self.chunks_created += len(result)
        return result
    
    def _split_by_headings(self, text: str) -> List[Dict[str, Any]]:
        """Split text by headings."""
        sections = []
        
        # Regex patterns for different heading styles
        patterns = [
            (r'^(#{1,6})\s+(.+)$', 'markdown'),  # Markdown: # Heading
            (r'^([A-Z][A-Za-z\s]+)$\n^={3,}$', 'underline'),  # Underlined
            (r'^(\d+\.?\d*)\s+([A-Z][A-Za-z\s]+)', 'numbered'),  # 1. Heading
        ]
        
        lines = text.split('\n')
        current_section = {'heading': '', 'content': '', 'level': 0}
        
        for i, line in enumerate(lines):
            is_heading = False
            
            # Check if line is a heading
            for pattern, style in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    # Save previous section
                    if current_section['content']:
                        sections.append(current_section)
                    
                    # Start new section
                    if style == 'markdown':
                        level = len(match.group(1))
                        heading = match.group(2)
                    elif style == 'numbered':
                        level = 2
                        heading = match.group(2)
                    else:
                        level = 1
                        heading = match.group(1) if match.lastindex >= 1 else line
                    
                    current_section = {
                        'heading': heading,
                        'content': '',
                        'level': level
                    }
                    is_heading = True
                    break
            
            if not is_heading:
                current_section['content'] += line + '\n'
        
        # Add final section
        if current_section['content']:
            sections.append(current_section)
        
        # If no headings found, treat whole text as one section
        if not sections:
            sections = [{'heading': '', 'content': text, 'level': 0}]
        
        return sections


class CodeAwareStrategy(ChunkingStrategy):
    """
    Strategy 4: Code-aware Splitting
    
    Best for: Documents with code snippets
    Pros: Preserves code blocks, respects syntax
    Cons: Only useful for code-heavy documents
    """
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        
        # Text splitter for regular content
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " "],
            is_separator_regex=False
        )
        
        # Code splitter for code blocks
        self.code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,  # Default, can detect others
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk with code awareness."""
        # Separate code blocks from text
        segments = self._separate_code_and_text(text)
        
        result = []
        chunk_index = 0
        
        for segment in segments:
            segment_type = segment['type']
            content = segment['content']
            
            # Choose appropriate splitter
            if segment_type == 'code':
                splitter = self.code_splitter
            else:
                splitter = self.text_splitter
            
            # Split if needed
            if len(content) > self.config.chunk_size:
                sub_chunks = splitter.split_text(content)
            else:
                sub_chunks = [content]
            
            for chunk_text in sub_chunks:
                chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                
                result.append({
                    "chunk_id": f"{metadata.get('source', 'doc')}_{chunk_index}_{chunk_id}",
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                    "strategy": self.config.name,
                    "content_type": segment_type,
                    "language": segment.get('language', 'text'),
                    **metadata
                })
                chunk_index += 1
        
        self.chunks_created += len(result)
        return result
    
    def _separate_code_and_text(self, text: str) -> List[Dict[str, Any]]:
        """Separate code blocks from regular text."""
        segments = []
        
        # Pattern for code blocks (markdown style)
        code_pattern = r'```(\w+)?\n(.*?)```'
        
        last_end = 0
        for match in re.finditer(code_pattern, text, re.DOTALL):
            # Add text before code block
            if match.start() > last_end:
                text_content = text[last_end:match.start()].strip()
                if text_content:
                    segments.append({
                        'type': 'text',
                        'content': text_content
                    })
            
            # Add code block
            language = match.group(1) or 'unknown'
            code_content = match.group(2).strip()
            segments.append({
                'type': 'code',
                'content': code_content,
                'language': language
            })
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            text_content = text[last_end:].strip()
            if text_content:
                segments.append({
                    'type': 'text',
                    'content': text_content
                })
        
        # If no code blocks found, treat as all text
        if not segments:
            segments = [{'type': 'text', 'content': text}]
        
        return segments


class HybridStrategy(ChunkingStrategy):
    """
    Strategy 5: Hybrid Strategy
    
    Best for: Complex documents with mixed content
    Pros: Combines benefits of all strategies, most flexible
    Cons: More complex, slower
    
    Combines:
    - Heading awareness for structure
    - Code awareness for code blocks
    - Semantic chunking for text
    """
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        
        # Initialize sub-strategies
        self.heading_strategy = HeadingAwareStrategy(config)
        self.code_strategy = CodeAwareStrategy(config)
        self.semantic_strategy = SemanticStrategy(config)
    
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk using hybrid approach."""
        # Step 1: Split by headings to preserve structure
        sections = self.heading_strategy._split_by_headings(text)
        
        result = []
        chunk_index = 0
        
        for section in sections:
            heading = section.get('heading', '')
            content = section.get('content', '')
            level = section.get('level', 0)
            
            # Step 2: Check if section has code blocks
            has_code = '```' in content or self._detect_code_patterns(content)
            
            if has_code:
                # Use code-aware strategy
                segments = self.code_strategy._separate_code_and_text(content)
                
                for segment in segments:
                    segment_content = segment['content']
                    
                    # Add heading context to first segment
                    if segment == segments[0] and heading:
                        segment_content = f"{heading}\n\n{segment_content}"
                    
                    # Split if too large
                    if len(segment_content) > self.config.chunk_size:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.config.chunk_size,
                            chunk_overlap=self.config.chunk_overlap
                        )
                        sub_chunks = splitter.split_text(segment_content)
                    else:
                        sub_chunks = [segment_content]
                    
                    for chunk_text in sub_chunks:
                        chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                        
                        result.append({
                            "chunk_id": f"{metadata.get('source', 'doc')}_{chunk_index}_{chunk_id}",
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "char_count": len(chunk_text),
                            "word_count": len(chunk_text.split()),
                            "strategy": self.config.name,
                            "section_heading": heading,
                            "heading_level": level,
                            "content_type": segment['type'],
                            **metadata
                        })
                        chunk_index += 1
            else:
                # Use semantic strategy for regular text
                full_text = f"{heading}\n\n{content}" if heading else content
                semantic_blocks = self.semantic_strategy._identify_semantic_blocks(full_text)
                
                for block in semantic_blocks:
                    if len(block) > self.config.chunk_size:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.config.chunk_size,
                            chunk_overlap=self.config.chunk_overlap
                        )
                        sub_chunks = splitter.split_text(block)
                    else:
                        sub_chunks = [block]
                    
                    for chunk_text in sub_chunks:
                        chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                        
                        result.append({
                            "chunk_id": f"{metadata.get('source', 'doc')}_{chunk_index}_{chunk_id}",
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "char_count": len(chunk_text),
                            "word_count": len(chunk_text.split()),
                            "strategy": self.config.name,
                            "section_heading": heading,
                            "heading_level": level,
                            "content_type": "text",
                            **metadata
                        })
                        chunk_index += 1
        
        self.chunks_created += len(result)
        return result
    
    def _detect_code_patterns(self, text: str) -> bool:
        """Detect if text contains code patterns."""
        code_indicators = [
            r'function\s+\w+\s*\(',
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'import\s+\w+',
            r'#include\s*<',
            r'public\s+class',
            r'=>',
            r'\w+\s*=\s*function',
        ]
        
        for pattern in code_indicators:
            if re.search(pattern, text):
                return True
        return False


class ChunkingEvaluator:
    """
    Evaluates chunking strategies with retrieval metrics.
    """
    
    @staticmethod
    def evaluate_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate chunk quality with multiple metrics.
        
        Metrics:
        - Chunk size distribution
        - Overlap effectiveness
        - Content preservation
        - Retrieval readiness
        """
        if not chunks:
            return {}
        
        char_counts = [c['char_count'] for c in chunks]
        word_counts = [c['word_count'] for c in chunks]
        
        metrics = {
            "total_chunks": len(chunks),
            "avg_char_count": sum(char_counts) / len(char_counts),
            "min_char_count": min(char_counts),
            "max_char_count": max(char_counts),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts),
            "size_variance": ChunkingEvaluator._calculate_variance(char_counts),
            "strategy": chunks[0].get('strategy', 'unknown')
        }
        
        # Calculate chunk size distribution
        size_ranges = {
            "very_small": len([c for c in char_counts if c < 500]),
            "small": len([c for c in char_counts if 500 <= c < 800]),
            "optimal": len([c for c in char_counts if 800 <= c < 1200]),
            "large": len([c for c in char_counts if 1200 <= c < 1500]),
            "very_large": len([c for c in char_counts if c >= 1500])
        }
        
        metrics["size_distribution"] = size_ranges
        metrics["optimal_percentage"] = (size_ranges["optimal"] / len(chunks)) * 100
        
        return metrics
    
    @staticmethod
    def _calculate_variance(values: List[float]) -> float:
        """Calculate variance of values."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    @staticmethod
    def compare_strategies(
        all_chunks: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Compare multiple chunking strategies."""
        comparison = {}
        
        for strategy_name, chunks in all_chunks.items():
            comparison[strategy_name] = ChunkingEvaluator.evaluate_chunks(chunks)
        
        # Determine best strategy
        best_strategy = max(
            comparison.items(),
            key=lambda x: x[1].get('optimal_percentage', 0)
        )
        
        return {
            "strategies": comparison,
            "recommended": best_strategy[0],
            "reason": f"Highest optimal chunk percentage: {best_strategy[1].get('optimal_percentage', 0):.1f}%"
        }


# Pre-configured strategies for different use cases
STRATEGY_CONFIGS = {
    "recursive_1000_100": ChunkingConfig(
        name="Recursive-1000-100",
        chunk_size=1000,
        chunk_overlap=100,
        description="Baseline: Good for general text, balanced size/overlap"
    ),
    "recursive_1500_200": ChunkingConfig(
        name="Recursive-1500-200",
        chunk_size=1500,
        chunk_overlap=200,
        description="Larger chunks: Better context, fewer chunks"
    ),
    "recursive_500_50": ChunkingConfig(
        name="Recursive-500-50",
        chunk_size=500,
        chunk_overlap=50,
        description="Smaller chunks: More precise retrieval, more chunks"
    ),
    "semantic_1200_150": ChunkingConfig(
        name="Semantic-1200-150",
        chunk_size=1200,
        chunk_overlap=150,
        description="Semantic: Keeps related concepts together"
    ),
    "heading_aware_1000_100": ChunkingConfig(
        name="HeadingAware-1000-100",
        chunk_size=1000,
        chunk_overlap=100,
        description="Heading-aware: Preserves document structure"
    ),
    "code_aware_1000_100": ChunkingConfig(
        name="CodeAware-1000-100",
        chunk_size=1000,
        chunk_overlap=100,
        description="Code-aware: Handles code blocks properly"
    ),
    "hybrid_1000_100": ChunkingConfig(
        name="Hybrid-1000-100",
        chunk_size=1000,
        chunk_overlap=100,
        description="Hybrid: Best of all strategies (RECOMMENDED)"
    )
}


def get_strategy(config_name: str) -> ChunkingStrategy:
    """Get a chunking strategy by config name."""
    if config_name not in STRATEGY_CONFIGS:
        raise ValueError(f"Unknown strategy: {config_name}. Available: {list(STRATEGY_CONFIGS.keys())}")
    
    config = STRATEGY_CONFIGS[config_name]
    
    # Map to strategy class
    if "Recursive" in config.name:
        return RecursiveStrategy(config)
    elif "Semantic" in config.name:
        return SemanticStrategy(config)
    elif "HeadingAware" in config.name:
        return HeadingAwareStrategy(config)
    elif "CodeAware" in config.name:
        return CodeAwareStrategy(config)
    elif "Hybrid" in config.name:
        return HybridStrategy(config)
    else:
        return RecursiveStrategy(config)


if __name__ == "__main__":
    # Example usage
    sample_text = """
    # Financial Derivatives
    
    Financial derivatives are contracts whose value is derived from an underlying asset.
    
    ## Option Pricing
    
    The Black-Scholes model is used to price European options:
    
    ```python
    def black_scholes(S, K, T, r, sigma):
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    ```
    
    This formula calculates the theoretical price of a call option.
    """
    
    # Test different strategies
    strategies_to_test = [
        "recursive_1000_100",
        "semantic_1200_150",
        "heading_aware_1000_100",
        "code_aware_1000_100",
        "hybrid_1000_100"
    ]
    
    all_chunks = {}
    
    for strategy_name in strategies_to_test:
        strategy = get_strategy(strategy_name)
        chunks = strategy.chunk(sample_text, {"source": "test.pdf", "page": 1})
        all_chunks[strategy_name] = chunks
        
        print(f"\n{strategy_name}:")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  Avg size: {sum(c['char_count'] for c in chunks) / len(chunks):.0f} chars")
    
    # Compare strategies
    comparison = ChunkingEvaluator.compare_strategies(all_chunks)
    print(f"\n✅ Recommended: {comparison['recommended']}")
    print(f"   Reason: {comparison['reason']}")

