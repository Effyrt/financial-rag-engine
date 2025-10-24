"""
Evaluation and Benchmarking Suite for AURELIA - ENTERPRISE VERSION
Comprehensive metrics for retrieval, generation, caching, and cost analysis.
"""

import time
import statistics
from typing import List, Dict, Any
from loguru import logger
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from embeddings.embedding_service import EmbeddingService
from vectordb.pinecone_client import PineconeVectorDB
from vectordb.chromadb_client import ChromaVectorDB
from retrieval.rag_retriever import RAGRetriever
from retrieval.wikipedia_fallback import WikipediaFallback
from concept_generator.concept_note_generator import ConceptNoteGenerator
from database.postgres_client import PostgresClient


class AureliaEvaluator:
    """
    Comprehensive evaluation system for AURELIA.
    
    Evaluates:
    1. Retrieval quality and performance
    2. Generation accuracy and completeness
    3. Caching effectiveness
    4. Cost analysis
    5. Vector DB comparison
    """
    
    def __init__(self, vector_db_type: str = "chromadb"):
        self.vector_db_type = vector_db_type
        
        # Initialize services
        self.embedding_service = EmbeddingService()
        
        if vector_db_type == "pinecone":
            self.vector_db = PineconeVectorDB()
        else:
            self.vector_db = ChromaVectorDB()
        
        self.wikipedia_fallback = WikipediaFallback()
        self.retriever = RAGRetriever(
            self.vector_db,
            self.embedding_service,
            self.wikipedia_fallback
        )
        self.generator = ConceptNoteGenerator()
        self.db_client = PostgresClient()
        
        logger.info(f"Evaluator initialized with {vector_db_type}")
    
    def evaluate_retrieval(self, test_queries: List[str]) -> Dict[str, Any]:
        """Evaluate retrieval quality."""
        logger.info(f"Evaluating retrieval for {len(test_queries)} queries")
        
        results = []
        retrieval_times = []
        confidence_scores = []
        sources = {"pdf": 0, "wikipedia": 0}
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                result = self.retriever.retrieve(query)
                
                retrieval_time = (time.time() - start_time) * 1000
                retrieval_times.append(retrieval_time)
                confidence_scores.append(result.confidence_score)
                
                if result.source.value == "fintbx_pdf":
                    sources["pdf"] += 1
                else:
                    sources["wikipedia"] += 1
                
                results.append({
                    "query": query,
                    "source": result.source.value,
                    "confidence": result.confidence_score,
                    "contexts_count": len(result.contexts),
                    "retrieval_time_ms": retrieval_time
                })
                
            except Exception as e:
                logger.error(f"Retrieval failed for '{query}': {e}")
                results.append({"query": query, "error": str(e)})
        
        return {
            "total_queries": len(test_queries),
            "successful_retrievals": len(retrieval_times),
            "avg_retrieval_time_ms": statistics.mean(retrieval_times) if retrieval_times else 0,
            "median_retrieval_time_ms": statistics.median(retrieval_times) if retrieval_times else 0,
            "avg_confidence": statistics.mean(confidence_scores) if confidence_scores else 0,
            "source_distribution": sources,
            "detailed_results": results
        }
    
    def evaluate_generation(self, test_concepts: List[str]) -> Dict[str, Any]:
        """Evaluate generation quality."""
        logger.info(f"Evaluating generation for {len(test_concepts)} concepts")
        
        results = []
        generation_times = []
        confidence_scores = []
        
        for concept in test_concepts:
            start_time = time.time()
            
            try:
                retrieval_result = self.retriever.retrieve(concept)
                
                from concept_generator.instructor_models import ConceptNoteRequest
                request = ConceptNoteRequest(
                    concept_name=concept,
                    context=retrieval_result.contexts,
                    source=retrieval_result.source.value,
                    include_code_examples=True
                )
                
                concept_note = self.generator.generate(request)
                
                generation_time = (time.time() - start_time) * 1000
                generation_times.append(generation_time)
                confidence_scores.append(concept_note.confidence_score)
                
                is_valid, issues = self.generator.validate_concept_note(concept_note)
                
                results.append({
                    "concept": concept,
                    "generation_time_ms": generation_time,
                    "confidence": concept_note.confidence_score,
                    "key_points_count": len(concept_note.key_points),
                    "citations_count": len(concept_note.citations),
                    "is_valid": is_valid,
                    "validation_issues": issues
                })
                
            except Exception as e:
                logger.error(f"Generation failed for '{concept}': {e}")
                results.append({"concept": concept, "error": str(e)})
        
        return {
            "total_concepts": len(test_concepts),
            "successful_generations": len(generation_times),
            "avg_generation_time_ms": statistics.mean(generation_times) if generation_times else 0,
            "avg_confidence": statistics.mean(confidence_scores) if confidence_scores else 0,
            "detailed_results": results
        }
    
    def run_full_evaluation(self, save_results: bool = True) -> Dict[str, Any]:
        """Run complete evaluation suite."""
        logger.info("Starting full AURELIA evaluation")
        
        test_concepts = [
            "Sharpe Ratio", "Black-Scholes Model", "Duration",
            "Value at Risk", "CAPM", "Beta Coefficient"
        ]
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "vector_db_type": self.vector_db_type,
            "retrieval_evaluation": self.evaluate_retrieval(test_concepts),
            "generation_evaluation": self.evaluate_generation(test_concepts[:3]),
            "cost_analysis": self.embedding_service.get_cost_summary()
        }
        
        if save_results:
            output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_file}")
        
        self._print_summary(results)
        return results
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print evaluation summary."""
        print("\n" + "="*70)
        print("AURELIA EVALUATION SUMMARY")
        print("="*70)
        
        ret = results['retrieval_evaluation']
        print(f"\n📥 RETRIEVAL:")
        print(f"  Avg Time: {ret['avg_retrieval_time_ms']:.2f}ms")
        print(f"  Avg Confidence: {ret['avg_confidence']:.2%}")
        print(f"  PDF/Wikipedia: {ret['source_distribution']['pdf']}/{ret['source_distribution']['wikipedia']}")
        
        gen = results['generation_evaluation']
        print(f"\n✨ GENERATION:")
        print(f"  Avg Time: {gen['avg_generation_time_ms']:.2f}ms")
        print(f"  Avg Confidence: {gen['avg_confidence']:.2%}")
        
        costs = results['cost_analysis']
        print(f"\n💰 COSTS:")
        print(f"  Total Tokens: {costs['total_tokens']:,}")
        print(f"  Total Cost: ${costs['total_cost_usd']:.4f}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    evaluator = AureliaEvaluator(vector_db_type="chromadb")
    results = evaluator.run_full_evaluation(save_results=True)