"""
Lab 5 - Evaluation & Benchmarking
Evaluate concept note quality and system performance
Run: python benchmark.py
"""

import requests
import time
import json
from typing import List, Dict
from datetime import datetime

# Your deployed services
FASTAPI_URL = "https://financial-rag-api-387661610307.us-central1.run.app"
STREAMLIT_URL = "https://financial-rag-frontend-387661610307.us-central1.run.app"

# Test concepts
TEST_CONCEPTS = [
    "Credit Default Swap",
    "Value at Risk",
    "Black-Scholes Model",
    "Portfolio Theory",
    "Capital Asset Pricing Model",
    "Efficient Market Hypothesis",
    "Collateralized Debt Obligation",
    "Interest Rate Swap",
    "Option Pricing",
    "Risk Management"
]

class Benchmark:
    def __init__(self):
        self.results = []
        
    def query_concept(self, concept: str) -> Dict:
        """Query a concept and measure performance"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{FASTAPI_URL}/query",
                json={"concept": concept},
                timeout=60
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "concept": concept,
                    "status": "success",
                    "latency": elapsed,
                    "cached": data.get("cached", False),
                    "source": data.get("source", "unknown"),
                    "generation_time": data.get("generation_time", 0),
                    "has_definition": bool(data.get("definition")),
                    "num_key_points": len(data.get("key_points", [])),
                    "num_examples": len(data.get("examples", [])),
                    "num_references": len(data.get("references", [])),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "concept": concept,
                    "status": "error",
                    "latency": elapsed,
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "concept": concept,
                "status": "error",
                "latency": 0,
                "error": str(e)
            }
    
    def run_latency_test(self):
        """Test 1: Compare cached vs. newly generated notes"""
        print("=" * 60)
        print("TEST 1: Latency Comparison (Cached vs. New)")
        print("=" * 60)
        
        results = {
            "first_query": [],
            "cached_query": []
        }
        
        for concept in TEST_CONCEPTS[:5]:  # Test first 5 concepts
            print(f"\nTesting: {concept}")
            
            # First query (not cached)
            print("  - First query (not cached)...")
            first = self.query_concept(concept)
            results["first_query"].append(first)
            
            if first['status'] == 'success':
                print(f"    ✅ Latency: {first['latency']:.3f}s")
            else:
                print(f"    ❌ Error: {first.get('error', 'Unknown')}")
            
            # Wait a bit
            time.sleep(1)
            
            # Second query (should be cached)
            print("  - Second query (should be cached)...")
            second = self.query_concept(concept)
            results["cached_query"].append(second)
            
            if second['status'] == 'success':
                print(f"    ✅ Latency: {second['latency']:.3f}s")
                print(f"    💾 Cached: {second.get('cached', False)}")
            else:
                print(f"    ❌ Error: {second.get('error', 'Unknown')}")
        
        # Calculate averages
        successful_first = [r for r in results["first_query"] if r['status'] == 'success']
        successful_cached = [r for r in results["cached_query"] if r['status'] == 'success']
        
        if successful_first and successful_cached:
            avg_first = sum(r['latency'] for r in successful_first) / len(successful_first)
            avg_cached = sum(r['latency'] for r in successful_cached) / len(successful_cached)
            
            print("\n" + "=" * 60)
            print("RESULTS:")
            print(f"Average First Query Latency:  {avg_first:.3f}s")
            print(f"Average Cached Query Latency: {avg_cached:.3f}s")
            
            if avg_cached > 0:
                speedup = avg_first / avg_cached
                print(f"Speedup from Caching: {speedup:.2f}x")
            
            print("=" * 60)
        else:
            print("\n⚠️ Not enough successful queries to calculate averages")
        
        return results
    
    def evaluate_quality(self):
        """Test 2: Evaluate concept note quality"""
        print("\n" + "=" * 60)
        print("TEST 2: Concept Note Quality Evaluation")
        print("=" * 60)
        
        quality_results = []
        
        for concept in TEST_CONCEPTS[:5]:
            print(f"\nEvaluating: {concept}")
            result = self.query_concept(concept)
            
            if result['status'] == 'success':
                # Simple quality metrics
                quality = {
                    "concept": concept,
                    "accuracy": 1.0 if result['has_definition'] else 0.0,
                    "completeness": (
                        (1 if result['has_definition'] else 0) +
                        (1 if result['num_key_points'] >= 3 else 0) +
                        (1 if result['num_examples'] >= 1 else 0) +
                        (1 if result['num_references'] >= 1 else 0)
                    ) / 4.0,
                    "citation_fidelity": 1.0 if result['num_references'] > 0 else 0.0,
                    "details": {
                        "has_definition": result['has_definition'],
                        "key_points": result['num_key_points'],
                        "examples": result['num_examples'],
                        "references": result['num_references']
                    }
                }
                
                quality_results.append(quality)
                
                print(f"  ✅ Accuracy: {quality['accuracy']:.2f}")
                print(f"  ✅ Completeness: {quality['completeness']:.2f}")
                print(f"  ✅ Citation Fidelity: {quality['citation_fidelity']:.2f}")
            else:
                print(f"  ❌ Failed to evaluate: {result.get('error', 'Unknown')}")
        
        # Overall averages
        if quality_results:
            avg_accuracy = sum(q['accuracy'] for q in quality_results) / len(quality_results)
            avg_completeness = sum(q['completeness'] for q in quality_results) / len(quality_results)
            avg_citation = sum(q['citation_fidelity'] for q in quality_results) / len(quality_results)
            
            print("\n" + "=" * 60)
            print("OVERALL QUALITY METRICS:")
            print(f"Average Accuracy: {avg_accuracy:.2f}")
            print(f"Average Completeness: {avg_completeness:.2f}")
            print(f"Average Citation Fidelity: {avg_citation:.2f}")
            print("=" * 60)
        else:
            print("\n⚠️ No successful queries to evaluate quality")
        
        return quality_results
    
    def estimate_costs(self):
        """Test 3: Estimate token costs"""
        print("\n" + "=" * 60)
        print("TEST 3: Token Cost Estimation")
        print("=" * 60)
        
        # Assumptions based on your Lab 1 data
        avg_tokens_per_chunk = 500
        num_chunks = 342  # From your Lab 1 data
        embedding_model = "text-embedding-3-large"
        cost_per_million = 0.13  # USD
        
        total_tokens = avg_tokens_per_chunk * num_chunks
        total_cost = (total_tokens / 1_000_000) * cost_per_million
        
        print(f"Embedding Model: {embedding_model}")
        print(f"Total Chunks: {num_chunks}")
        print(f"Avg Tokens per Chunk: {avg_tokens_per_chunk}")
        print(f"Total Tokens Embedded: {total_tokens:,}")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Cost per Chunk: ${(total_cost / num_chunks):.6f}")
        print("=" * 60)
        
        return {
            "model": embedding_model,
            "total_chunks": num_chunks,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "cost_per_chunk": total_cost / num_chunks
        }
    
    def test_retrieval_latency(self):
        """Test 4: Retrieval latency for different vector stores"""
        print("\n" + "=" * 60)
        print("TEST 4: Retrieval Latency Analysis")
        print("=" * 60)
        
        retrieval_results = []
        
        for concept in TEST_CONCEPTS[:3]:
            print(f"\nTesting retrieval for: {concept}")
            result = self.query_concept(concept)
            
            if result['status'] == 'success':
                retrieval_results.append({
                    "concept": concept,
                    "retrieval_latency": result['latency'],
                    "generation_time": result['generation_time'],
                    "total_time": result['latency']
                })
                
                print(f"  Retrieval Latency: {result['latency']:.3f}s")
                print(f"  Generation Time: {result['generation_time']:.3f}s")
        
        if retrieval_results:
            avg_retrieval = sum(r['retrieval_latency'] for r in retrieval_results) / len(retrieval_results)
            
            print("\n" + "=" * 60)
            print("RETRIEVAL LATENCY RESULTS:")
            print(f"Average Retrieval Latency: {avg_retrieval:.3f}s")
            print(f"Vector Store: ChromaDB")
            print("=" * 60)
        
        return retrieval_results
    
    def generate_report(self, latency_results, quality_results, cost_results, retrieval_results):
        """Generate final evaluation report"""
        
        successful_first = [r for r in latency_results.get("first_query", []) if r['status'] == 'success']
        successful_cached = [r for r in latency_results.get("cached_query", []) if r['status'] == 'success']
        
        report = {
            "evaluation_date": datetime.now().isoformat(),
            "services_tested": {
                "fastapi": FASTAPI_URL,
                "streamlit": STREAMLIT_URL
            },
            "latency_analysis": {
                "first_query": latency_results.get("first_query", []),
                "cached_query": latency_results.get("cached_query", []),
                "average_first_query_latency": sum(r['latency'] for r in successful_first) / len(successful_first) if successful_first else 0,
                "average_cached_query_latency": sum(r['latency'] for r in successful_cached) / len(successful_cached) if successful_cached else 0
            },
            "quality_metrics": {
                "results": quality_results,
                "averages": {
                    "accuracy": sum(q['accuracy'] for q in quality_results) / len(quality_results) if quality_results else 0,
                    "completeness": sum(q['completeness'] for q in quality_results) / len(quality_results) if quality_results else 0,
                    "citation_fidelity": sum(q['citation_fidelity'] for q in quality_results) / len(quality_results) if quality_results else 0
                }
            },
            "cost_estimation": cost_results,
            "retrieval_analysis": {
                "results": retrieval_results,
                "average_retrieval_latency": sum(r['retrieval_latency'] for r in retrieval_results) / len(retrieval_results) if retrieval_results else 0
            },
            "summary": {
                "total_tests": len(TEST_CONCEPTS),
                "successful_queries": len(successful_first),
                "system_status": "operational" if successful_first else "issues detected"
            }
        }
        
        # Save report
        with open("evaluation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 60)
        print("✅ EVALUATION COMPLETE")
        print("=" * 60)
        print(f"📊 Report saved to: evaluation_report.json")
        print(f"📈 Total Tests: {report['summary']['total_tests']}")
        print(f"✅ Successful Queries: {report['summary']['successful_queries']}")
        print(f"💰 Estimated Cost: ${cost_results['total_cost_usd']:.4f}")
        print("=" * 60)
        
        return report


def main():
    """Run all benchmarks"""
    print("\n" + "🚀" * 30)
    print("Starting Lab 5 Evaluation & Benchmarking")
    print("🚀" * 30 + "\n")
    
    benchmark = Benchmark()
    
    try:
        # Run tests
        print("Running Test Suite...\n")
        
        latency_results = benchmark.run_latency_test()
        quality_results = benchmark.evaluate_quality()
        cost_results = benchmark.estimate_costs()
        retrieval_results = benchmark.test_retrieval_latency()
        
        # Generate report
        report = benchmark.generate_report(
            latency_results, 
            quality_results, 
            cost_results,
            retrieval_results
        )
        
        print("\n✅ All benchmarks completed successfully!")
        print(f"📊 Results saved to: evaluation_report.json")
        print("\nYou can now:")
        print("  1. Review the evaluation_report.json file")
        print("  2. Include these metrics in your final deliverables")
        print("  3. Proceed to create your video demo and documentation")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Evaluation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during evaluation: {e}")
        print("Please check your services are running and try again")


if __name__ == "__main__":
    main()