# src/experiments/retrieval_evaluation.py
"""
Evaluate retrieval system performance - using OpenAI text-embedding-3-large
"""

import os
from pathlib import Path

# Use OpenAI Embeddings (Lab 1 requirement)
try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    print("✅ Using OpenAI Embeddings (text-embedding-3-large)")
except ImportError:
    print("❌ Missing required packages")
    print("   Please install: pip install langchain-chroma langchain-openai")
    exit(1)

def evaluate_retrieval():
    """Evaluate retrieval performance"""
    
    print("\n" + "="*80)
    print("🔍 Retrieval System Evaluation (Lab 1)")
    print("="*80)
    
    # Check API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not set")
        print("   Please add to .env file: OPENAI_API_KEY=your-key-here")
        return
    
    # Check vectorstore
    vectorstore_path = Path("data/vectorstore")
    if not vectorstore_path.exists():
        print("\n❌ Error: Vectorstore does not exist")
        print("   Please run first: python build_vectorstore.py")
        return
    
    # Initialize OpenAI embeddings
    print(f"\n🤖 Initializing OpenAI Embeddings")
    print(f"   Model: text-embedding-3-large")
    print(f"   Dimensions: 3072")
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # Load vectorstore
    print(f"\n📂 Loading vectorstore: {vectorstore_path}")
    
    db = Chroma(
        persist_directory=str(vectorstore_path),
        embedding_function=embeddings
    )
    
    # Get statistics
    try:
        collection = db._collection
        doc_count = collection.count()
        print(f"   ✅ Total documents: {doc_count}")
    except:
        print("   ⚠️  Unable to retrieve document count")
    
    # Test queries
    test_queries = [
        "What is Sharpe Ratio?",
        "How to calculate bond duration?",
        "Explain portfolio optimization",
        "What is the Black-Scholes model?",
        "How to handle dates in MATLAB?",
        "Matrix operations in Financial Toolbox"
    ]
    
    print(f"\n📊 Evaluating {len(test_queries)} queries...")
    
    results_summary = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"❓ Query {i}/{len(test_queries)}: {query}")
        print("="*80)
        
        try:
            # Retrieve relevant documents (with similarity scores)
            search_results = db.similarity_search_with_score(query, k=5)
            
            if not search_results:
                print("⚠️  No relevant results found")
                results_summary.append({
                    'query': query,
                    'found': 0,
                    'avg_score': 0,
                    'best_score': 0
                })
                continue
            
            # Calculate metrics
            scores = [score for _, score in search_results]
            avg_score = sum(scores) / len(scores)
            best_score = min(scores)  # Chroma uses distance, lower is better
            
            results_summary.append({
                'query': query,
                'found': len(search_results),
                'avg_score': avg_score,
                'best_score': best_score
            })
            
            # Display results
            print(f"\n📄 Found {len(search_results)} relevant documents:")
            
            for rank, (doc, score) in enumerate(search_results, 1):
                page = doc.metadata.get('page', 'N/A')
                section = doc.metadata.get('section', 'N/A')
                
                # Special tags
                tags = []
                if doc.metadata.get('has_tables'):
                    tags.append("📊")
                if doc.metadata.get('has_code'):
                    tags.append("💻")
                if doc.metadata.get('has_formulas'):
                    tags.append("🔢")
                tag_str = "".join(tags)
                
                # Similarity (distance conversion)
                similarity = 1 - score  # Simple conversion
                
                # Content preview
                content_preview = doc.page_content.replace('\n', ' ')[:100]
                
                print(f"\n  [{rank}] Similarity: {similarity:.3f} | Page {page} | {section} {tag_str}")
                print(f"      {content_preview}...")
            
            # Display statistics
            print(f"\n📊 Statistics:")
            print(f"   Average similarity: {1 - avg_score:.3f}")
            print(f"   Best similarity: {1 - best_score:.3f}")
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            results_summary.append({
                'query': query,
                'found': 0,
                'avg_score': 0,
                'best_score': 0,
                'error': str(e)
            })
    
    # Overall evaluation
    print(f"\n{'='*80}")
    print("📈 Overall Evaluation Results")
    print("="*80)
    
    total_queries = len(test_queries)
    successful_queries = sum(1 for r in results_summary if r['found'] > 0)
    failed_queries = total_queries - successful_queries
    
    print(f"\nQuery Statistics:")
    print(f"   Total queries: {total_queries}")
    print(f"   Successful queries: {successful_queries}")
    print(f"   Failed queries: {failed_queries}")
    print(f"   Success rate: {successful_queries/total_queries*100:.1f}%")
    
    if successful_queries > 0:
        # Calculate average metrics
        avg_found = sum(r['found'] for r in results_summary if r['found'] > 0) / successful_queries
        avg_similarity = sum(1 - r['best_score'] for r in results_summary if r['found'] > 0) / successful_queries
        
        print(f"\nRetrieval Performance:")
        print(f"   Average documents found: {avg_found:.1f}")
        print(f"   Average best similarity: {avg_similarity:.3f}")
    
    # Find best and worst performing queries
    if results_summary:
        valid_results = [r for r in results_summary if r['found'] > 0]
        
        if valid_results:
            best_query = max(valid_results, key=lambda x: 1 - x['best_score'])
            worst_query = min(valid_results, key=lambda x: 1 - x['best_score'])
            
            print(f"\n🏆 Best performing query:")
            print(f"   Query: {best_query['query']}")
            print(f"   Best similarity: {1 - best_query['best_score']:.3f}")
            
            print(f"\n⚠️  Worst performing query:")
            print(f"   Query: {worst_query['query']}")
            print(f"   Best similarity: {1 - worst_query['best_score']:.3f}")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("💡 Improvement Suggestions")
    print("="*80)
    
    if failed_queries > 0:
        print("\n⚠️  Some queries failed, possible reasons:")
        print("   1. No relevant content in vectorstore")
        print("   2. Query terms differ too much from document content")
        print("   3. Need more data or adjust chunking strategy")
    
    if successful_queries > 0:
        if avg_similarity < 0.5:
            print("\n⚠️  Average similarity is low, suggestions:")
            print("   1. Experiment with different chunking strategies")
            print("   2. Adjust chunk_size and overlap")
            print("   3. Add more relevant content")
        elif avg_similarity > 0.7:
            print("\n✅ Retrieval system performing well!")
            print("   Consider further optimization:")
            print("   1. Adjust retrieval parameters (k value)")
            print("   2. Experiment with different reranking strategies")
            print("   3. Add hybrid retrieval (BM25 + vector)")
    
    print("\n" + "="*80)
    print("✅ Evaluation complete")
    print("="*80)
    
    # Save results
    import json
    output_file = Path("data/experiments/retrieval_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved: {output_file}")


def check_vectorstore_status():
    """Check vectorstore status"""
    
    print("\n" + "="*80)
    print("📊 Vectorstore Status Check")
    print("="*80)
    
    # Check configuration file
    config_file = Path("data/vectorstore_config.json")
    
    if config_file.exists():
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n✅ Configuration file exists")
        print(f"   Embedding model: {config.get('embedding_model', 'Unknown')}")
        print(f"   Embedding dimensions: {config.get('embedding_dimension', 'Unknown')}")
        print(f"   Chunking strategy: {config.get('chunking_strategy', 'Unknown')}")
        print(f"   Total documents: {config.get('total_documents', 'Unknown')}")
        
        if config.get('embedding_model') != 'text-embedding-3-large':
            print("\n⚠️  Warning: Vectorstore not using text-embedding-3-large")
            print("   Lab 1 requires OpenAI text-embedding-3-large")
            print("   Please run: python build_vectorstore.py")
            return False
    else:
        print("\n⚠️  Configuration file does not exist")
    
    # Check vectorstore
    vectorstore_path = Path("data/vectorstore")
    
    if not vectorstore_path.exists():
        print(f"\n❌ Vectorstore does not exist: {vectorstore_path}")
        print("   Please run: python build_vectorstore.py")
        return False
    
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        
        db = Chroma(
            persist_directory=str(vectorstore_path),
            embedding_function=embeddings
        )
        
        # Get statistics
        collection = db._collection
        doc_count = collection.count()
        
        print(f"\n✅ Vectorstore is healthy")
        print(f"   Total documents: {doc_count}")
        print(f"   Embedding model: text-embedding-3-large")
        print(f"   Embedding dimensions: 3072")
        
        # Try a simple query
        test_results = db.similarity_search("test", k=1)
        if test_results:
            print(f"   Query function: ✅ Working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Vectorstore error: {e}")
        print("\n💡 Suggestions:")
        print("   1. Confirm OPENAI_API_KEY is set")
        print("   2. Confirm data/vectorstore exists")
        print("   3. May need to rebuild: python build_vectorstore.py")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check database status first
    if check_vectorstore_status():
        # Run evaluation
        evaluate_retrieval()
    else:
        print("\n⚠️  Vectorstore has issues, please fix first")
        print("\n💡 Fix steps:")
        print("   1. Confirm OPENAI_API_KEY in .env")
        print("   2. Run: python build_vectorstore.py")
        print("   3. Run this script again")