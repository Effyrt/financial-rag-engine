"""
Embedding Generation Module using OpenAI.

This module provides functionality to generate embeddings for text chunks
using OpenAI's text-embedding-3-large model.
"""

import logging
import time
from typing import List, Dict, Any, Optional
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using OpenAI's text-embedding-3-large model.
    
    Attributes:
        client: OpenAI client instance
        model: Embedding model name
        dimension: Embedding dimension (3072 for text-embedding-3-large)
        batch_size: Number of texts to process in one API call
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-large",
        dimension: int = 3072,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """
        Initialize EmbeddingGenerator.
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: OpenAI embedding model name
            dimension: Embedding dimension
            batch_size: Number of texts per batch
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.dimension = dimension
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        
        # Pricing (as of 2025): text-embedding-3-large is $0.13 per 1M tokens
        self.cost_per_million_tokens = 0.13
        
        logger.info(
            f"EmbeddingGenerator initialized: "
            f"model={model}, dimension={dimension}, batch_size={batch_size}"
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        embeddings = self.generate_embeddings_batch([text])
        return embeddings[0]
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        
        if len(valid_texts) < len(texts):
            logger.warning(
                f"Filtered out {len(texts) - len(valid_texts)} empty texts"
            )
        
        if not valid_texts:
            return []
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i:i + self.batch_size]
            
            if show_progress:
                logger.info(
                    f"Processing batch {i // self.batch_size + 1}/"
                    f"{(len(valid_texts) + self.batch_size - 1) // self.batch_size}"
                )
            
            # Generate embeddings with retry logic
            batch_embeddings = self._generate_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
        
        logger.info(
            f"Generated {len(all_embeddings)} embeddings "
            f"(Total tokens: {self.total_tokens:,}, "
            f"Estimated cost: ${self.total_cost:.4f})"
        )
        
        return all_embeddings
    
    def _generate_with_retry(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings with exponential backoff retry.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self.dimension
                )
                
                # Update cost tracking
                tokens_used = response.usage.total_tokens
                self.total_tokens += tokens_used
                self.total_cost += (tokens_used / 1_000_000) * self.cost_per_million_tokens
                
                # Extract embeddings
                embeddings = [item.embedding for item in response.data]
                
                return embeddings
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Error generating embeddings (attempt {attempt + 1}/"
                        f"{self.max_retries}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to generate embeddings after {self.max_retries} attempts")
                    raise
    
    def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        text_key: str = "chunk_text"
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks with metadata.
        
        Args:
            chunks: List of chunk dictionaries
            text_key: Key in chunk dict containing the text
            
        Returns:
            List of chunks with added 'embedding' field
        """
        if not chunks:
            return []
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        # Extract texts
        texts = [chunk.get(text_key, "") for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings_batch(texts, show_progress=True)
        
        # Add embeddings to chunks
        chunks_with_embeddings = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_copy = chunk.copy()
            chunk_copy["embedding"] = embedding
            chunk_copy["embedding_model"] = self.model
            chunk_copy["embedding_dimension"] = len(embedding)
            chunks_with_embeddings.append(chunk_copy)
        
        return chunks_with_embeddings
    
    def estimate_cost(self, num_tokens: int) -> float:
        """
        Estimate cost for a given number of tokens.
        
        Args:
            num_tokens: Number of tokens
            
        Returns:
            Estimated cost in USD
        """
        return (num_tokens / 1_000_000) * self.cost_per_million_tokens
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get summary of costs incurred.
        
        Returns:
            Dictionary with cost information
        """
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "cost_per_million_tokens": self.cost_per_million_tokens,
            "model": self.model
        }


def main():
    """Test the embedding generator."""
    import json
    from pathlib import Path
    
    print("\n" + "="*60)
    print("EMBEDDING GENERATOR TEST")
    print("="*60 + "\n")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("\nTo test embeddings, create a .env file with:")
        print("OPENAI_API_KEY=your_api_key_here")
        print("\nSkipping embedding generation test.")
        print("✅ EmbeddingGenerator class created successfully!")
        return
    
    # Load chunked data
    input_file = Path("data/processed/chunking_results.json")
    
    if not input_file.exists():
        print("❌ Please run chunker.py first!")
        return
    
    with open(input_file) as f:
        chunking_results = json.load(f)
    
    # Get sample chunks (first 3 chunks from 1000_100 strategy)
    sample_chunks = chunking_results["1000_100"]["chunks"]
    
    print(f"Testing with {len(sample_chunks)} sample chunks\n")
    
    # Initialize generator
    generator = EmbeddingGenerator(
        model="text-embedding-3-large",
        dimension=3072,
        batch_size=10
    )
    
    # Generate embeddings
    chunks_with_embeddings = generator.embed_chunks(sample_chunks)
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    for i, chunk in enumerate(chunks_with_embeddings, 1):
        print(f"\nChunk {i}:")
        print(f"  ID: {chunk['chunk_id']}")
        print(f"  Text length: {chunk['chunk_size']} chars")
        print(f"  Embedding dimension: {chunk['embedding_dimension']}")
        print(f"  First 5 values: {chunk['embedding'][:5]}")
    
    # Cost summary
    cost_summary = generator.get_cost_summary()
    print(f"\n💰 Cost Summary:")
    print(f"  Total tokens: {cost_summary['total_tokens']:,}")
    print(f"  Total cost: ${cost_summary['total_cost_usd']:.4f}")
    print(f"  Model: {cost_summary['model']}")
    
    # Save results
    output_file = Path("data/processed/sample_embeddings.json")
    
    # Remove embeddings for saving (too large)
    chunks_for_save = []
    for chunk in chunks_with_embeddings:
        chunk_copy = chunk.copy()
        chunk_copy["embedding"] = f"<{len(chunk['embedding'])} dimensions>"
        chunks_for_save.append(chunk_copy)
    
    with open(output_file, 'w') as f:
        json.dump({
            "chunks": chunks_for_save,
            "cost_summary": cost_summary
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n✅ Embedding generation test complete!")


if __name__ == "__main__":
    main()

