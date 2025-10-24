# src/experiments/chunking_experiments.py 
"""
Lab 1 Task 2: Experiment with Multiple Chunking Strategies and Evaluate Retrieval Performance

Includes:
- Multiple chunking strategies
- Retrieval performance evaluation (Precision, Recall, MRR)
- Detailed comparison report
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import json
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

# Test query set (adjust based on your PDF)
TEST_QUERIES = [
    {
        "query": "How to calculate bond duration?",
        "relevant_keywords": ["bond", "duration", "calculate", "fixed", "income"],
        "expected_content": ["duration", "bond"]
    },
    {
        "query": "What is Sharpe Ratio?",
        "relevant_keywords": ["sharpe", "ratio", "performance", "risk", "return"],
        "expected_content": ["sharpe", "ratio"]
    },
    {
        "query": "Matrix operations in MATLAB",
        "relevant_keywords": ["matrix", "multiply", "operations", "matlab"],
        "expected_content": ["matrix", "multiply", "operations"]
    },
    {
        "query": "Portfolio optimization methods",
        "relevant_keywords": ["portfolio", "optimization", "efficient", "frontier"],
        "expected_content": ["portfolio", "optimiz"]
    },
    {
        "query": "How to handle dates?",
        "relevant_keywords": ["date", "format", "time", "convert"],
        "expected_content": ["date", "time"]
    }
]

def load_documents(input_path="data/parsed/chunks_full.json"):
    """Load parsed documents"""
    if not Path(input_path).exists():
        print(f"❌ Error: {input_path} does not exist")
        print("   Please run first: python convert_docling_to_chunks.py")
        return None
    
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)

def evaluate_retrieval_performance(chunks, strategy_name, chunk_params):
    """
    Evaluate retrieval performance
    
    Calculates:
    - Precision@k: Proportion of relevant documents in returned results
    - Recall@k: Proportion of relevant documents found out of all relevant documents
    - MRR: Mean Reciprocal Rank
    """
    
    print(f"\n   🔍 Evaluating retrieval performance...")
    
    # Check API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("   ⚠️  OPENAI_API_KEY not set, skipping retrieval evaluation")
        return None
    
    # Build temporary vectorstore
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # Convert to Document
    documents = [
        Document(page_content=chunk, metadata={"index": i})
        for i, chunk in enumerate(chunks)
    ]
    
    # Create temporary vectorstore
    temp_path = f"data/experiments/temp_{strategy_name.replace(' ', '_')}"
    if Path(temp_path).exists():
        shutil.rmtree(temp_path)
    
    try:
        db = Chroma.from_documents(documents, embeddings, persist_directory=temp_path)
    except Exception as e:
        print(f"   ⚠️  Cannot build vectorstore: {e}")
        return None
    
    # Evaluation metrics
    metrics = {
        "precision_at_3": [],
        "recall_at_3": [],
        "mrr": [],
        "retrieval_times": []
    }
    
    k = 3  # Top-k results
    
    for test in TEST_QUERIES:
        # Time the query
        start_time = time.time()
        results = db.similarity_search(test["query"], k=k)
        retrieval_time = time.time() - start_time
        metrics["retrieval_times"].append(retrieval_time)
        
        # Check relevance (based on keyword matching)
        relevant_found = 0
        first_relevant_rank = None
        
        for rank, doc in enumerate(results, 1):
            content_lower = doc.page_content.lower()
            # Consider relevant if contains any expected content keyword
            is_relevant = any(kw in content_lower for kw in test["expected_content"])
            
            if is_relevant:
                relevant_found += 1
                if first_relevant_rank is None:
                    first_relevant_rank = rank
        
        # Precision@3: Proportion of relevant results
        precision = relevant_found / k if k > 0 else 0
        metrics["precision_at_3"].append(precision)
        
        # Recall@3: Assume 2 relevant documents per query
        assumed_total_relevant = 2
        recall = relevant_found / assumed_total_relevant
        metrics["recall_at_3"].append(recall)
        
        # MRR: Mean Reciprocal Rank
        mrr = 1.0 / first_relevant_rank if first_relevant_rank else 0
        metrics["mrr"].append(mrr)
    
    # Clean up temporary vectorstore
    try:
        shutil.rmtree(temp_path)
    except:
        pass
    
    # Calculate averages
    avg_metrics = {
        "avg_precision": sum(metrics["precision_at_3"]) / len(metrics["precision_at_3"]),
        "avg_recall": sum(metrics["recall_at_3"]) / len(metrics["recall_at_3"]),
        "avg_mrr": sum(metrics["mrr"]) / len(metrics["mrr"]),
        "avg_retrieval_time": sum(metrics["retrieval_times"]) / len(metrics["retrieval_times"])
    }
    
    print(f"   📈 Retrieval Metrics:")
    print(f"      Precision@3: {avg_metrics['avg_precision']:.3f}")
    print(f"      Recall@3: {avg_metrics['avg_recall']:.3f}")
    print(f"      MRR: {avg_metrics['avg_mrr']:.3f}")
    print(f"      Average Retrieval Time: {avg_metrics['avg_retrieval_time']:.3f}s")
    
    return avg_metrics

def experiment_chunking_strategies():
    """Experiment with multiple chunking strategies"""
    
    print("\n" + "="*80)
    print("🧪 Lab 1 Task 2 - Chunking Strategy Experiments")
    print("="*80)
    
    docs = load_documents()
    if not docs:
        return None
    
    all_text = "\n\n".join([d["content"] for d in docs])
    
    print(f"\n📖 Loaded Documents:")
    print(f"   Total Pages: {len(docs)}")
    print(f"   Total Characters: {len(all_text):,}")
    
    # Define multiple strategies
    strategies = {
        "Strategy 1 - Small Chunks": {
            "splitter": RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100,
                separators=["\n\n", "\n", ".", " "]
            ),
            "params": {"chunk_size": 500, "overlap": 100}
        },
        "Strategy 2 - Medium Chunks": {
            "splitter": RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " "]
            ),
            "params": {"chunk_size": 1000, "overlap": 200}
        },
        "Strategy 3 - Large Chunks": {
            "splitter": RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=400,
                separators=["\n\n", "\n", ".", " "]
            ),
            "params": {"chunk_size": 2000, "overlap": 400}
        },
        "Strategy 4 - Paragraph-focused": {
            "splitter": RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " "]
            ),
            "params": {"chunk_size": 1000, "overlap": 150, "focus": "paragraphs"}
        }
    }
    
    results = {}
    
    for strategy_name, strategy_config in strategies.items():
        print(f"\n{'='*80}")
        print(f"📊 Testing: {strategy_name}")
        print(f"{'='*80}")
        
        splitter = strategy_config["splitter"]
        params = strategy_config["params"]
        
        print(f"   Parameters: {params}")
        
        # Chunk the text
        chunks = splitter.split_text(all_text)
        
        # Statistical metrics
        avg_chunk_size = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
        max_chunk_size = max(len(c) for c in chunks) if chunks else 0
        min_chunk_size = min(len(c) for c in chunks) if chunks else 0
        
        print(f"\n   📏 Chunking Statistics:")
        print(f"      Total Chunks: {len(chunks)}")
        print(f"      Average Chunk Size: {avg_chunk_size:.2f} chars")
        print(f"      Max Chunk Size: {max_chunk_size} chars")
        print(f"      Min Chunk Size: {min_chunk_size} chars")
        
        # Evaluate retrieval performance
        retrieval_metrics = evaluate_retrieval_performance(chunks, strategy_name, params)
        
        results[strategy_name] = {
            "params": params,
            "total_chunks": len(chunks),
            "avg_chunk_size": round(avg_chunk_size, 2),
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "sample_chunk": chunks[0][:200] if chunks else "",
            "retrieval_metrics": retrieval_metrics
        }
        
        print(f"\n   ✅ {strategy_name} completed")
    
    # Generate comparison report
    generate_comparison_report(results)
    
    # Save results
    output_file = Path("data/experiments/chunking_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"✅ Experiment results saved: {output_file}")
    print(f"{'='*80}")
    
    return results

def generate_comparison_report(results):
    """Generate detailed comparison report"""
    
    print(f"\n{'='*80}")
    print("📋 Strategy Comparison Report")
    print("="*80)
    
    # Table headers
    print(f"\n{'Strategy':<35} | {'Chunks':<8} | {'Avg Size':<10} | {'P@3':<6} | {'R@3':<6} | {'MRR':<6}")
    print("-" * 90)
    
    # Results for each strategy
    for strategy_name, metrics in results.items():
        display_name = strategy_name[:33]
        chunks = metrics['total_chunks']
        avg_size = metrics['avg_chunk_size']
        
        if metrics.get('retrieval_metrics'):
            rm = metrics['retrieval_metrics']
            precision = rm['avg_precision']
            recall = rm['avg_recall']
            mrr = rm['avg_mrr']
            
            print(f"{display_name:<35} | {chunks:<8} | {avg_size:<10.0f} | "
                  f"{precision:<6.3f} | {recall:<6.3f} | {mrr:<6.3f}")
        else:
            print(f"{display_name:<35} | {chunks:<8} | {avg_size:<10.0f} | "
                  f"{'N/A':<6} | {'N/A':<6} | {'N/A':<6}")
    
    # Find best strategies
    strategies_with_metrics = {
        name: metrics for name, metrics in results.items()
        if metrics.get('retrieval_metrics')
    }
    
    if strategies_with_metrics:
        best_by_precision = max(
            strategies_with_metrics.items(),
            key=lambda x: x[1]['retrieval_metrics']['avg_precision']
        )
        
        best_by_mrr = max(
            strategies_with_metrics.items(),
            key=lambda x: x[1]['retrieval_metrics']['avg_mrr']
        )
        
        print(f"\n🏆 Best Strategies:")
        print(f"   Precision: {best_by_precision[0]}")
        print(f"      → Precision@3: {best_by_precision[1]['retrieval_metrics']['avg_precision']:.3f}")
        
        print(f"\n   MRR: {best_by_mrr[0]}")
        print(f"      → MRR: {best_by_mrr[1]['retrieval_metrics']['avg_mrr']:.3f}")
    
    # Justification
    print(f"\n{'='*80}")
    print("💡 Strategy Selection Justification")
    print("="*80)
    
    print("\nBased on experimental results, consider these factors for strategy selection:")
    
    print("\n1. **Small Chunks Strategy (500 chars)**")
    print("   Pros: Precise matching, good for specific queries")
    print("   Cons: Lacks context, may cut important information")
    print("   Use case: Finding specific terms or short definitions")
    
    print("\n2. **Medium Chunks Strategy (1000 chars) ⭐ Recommended**")
    print("   Pros: Balances precision and context")
    print("   Cons: General purpose, may not be optimal for all scenarios")
    print("   Use case: Most RAG applications")
    
    print("\n3. **Large Chunks Strategy (2000 chars)**")
    print("   Pros: Preserves complete context and logic")
    print("   Cons: May include noise, reducing precision")
    print("   Use case: Scenarios requiring complete paragraphs or sections")
    
    print("\n4. **Paragraph-focused Strategy**")
    print("   Pros: Respects document structure, logically complete")
    print("   Cons: Uneven chunk sizes")
    print("   Use case: Structured documents like technical manuals")
    
    print("\n📊 Final Recommendation:")
    if strategies_with_metrics:
        best_strategy = best_by_mrr[0]
        print(f"   Recommended: {best_strategy}")
        print(f"   Reason: This strategy performs best on MRR metric,")
        print(f"           meaning most relevant documents rank higher")
    else:
        print("   Recommended: Strategy 2 - Medium Chunks")
        print("   Reason: Without retrieval evaluation,")
        print("           medium-sized chunks are usually the most balanced choice")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 Lab 1 - Chunking Strategy Experiments and Evaluation")
    print("="*80)
    print("\n⚠️  Note:")
    print("   - OPENAI_API_KEY required for retrieval evaluation")
    print("   - Experiment will call OpenAI API (paid service)")
    print("   - Estimated time: 2-5 minutes")
    print("="*80 + "\n")
    
    # Ensure directory exists
    Path("data/experiments").mkdir(parents=True, exist_ok=True)
    
    # Run experiments
    results = experiment_chunking_strategies()
    
    if results:
        print("\n🎉 Experiments completed!")
        print("\nNext steps:")
        print("   1. Review report: cat data/experiments/chunking_results.json")
        print("   2. Choose best strategy")
        print("   3. Update build_vectorstore.py parameters")
        print("   4. Build final vectorstore: python build_vectorstore.py")
    else:
        print("\n❌ Experiments failed, please check error messages")