# test.py - Test vector database (OpenAI version)
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Use OpenAI Embeddings (consistent with build_vectorstore.py)
try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    print("✅ Using langchain-chroma (new version)")
    print("✅ Using langchain-openai (new version)")
except ImportError:
    print("❌ Missing required packages")
    print("   Please install: pip install langchain-chroma langchain-openai")
    exit(1)

def test_vectorstore():
    """Test vectorstore content"""
    
    vectorstore_path = Path("data/vectorstore")
    
    if not vectorstore_path.exists():
        print("❌ Vectorstore does not exist!")
        print("   Please run first: python src/embeddings/build_vectorstore.py")
        return
    
    # Check API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set")
        print("   Please add to .env file: OPENAI_API_KEY=your-key-here")
        return
    
    print(f"📂 Loading vectorstore: {vectorstore_path}")
    
    # Initialize OpenAI embeddings (consistent with build_vectorstore.py)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # Load vectorstore
    db = Chroma(
        persist_directory=str(vectorstore_path),
        embedding_function=embeddings
    )
    
    # Get document count
    collection = db._collection
    doc_count = collection.count()
    
    print(f"📊 Vectorstore Statistics:")
    print(f"   - Total documents: {doc_count}")
    print(f"   - Embedding model: text-embedding-3-large")
    print(f"   - Embedding dimensions: 3072")
    
    # Check first 10 documents
    print(f"\n📄 First 10 Documents:")
    print("=" * 80)
    
    # Use meaningful query to retrieve documents
    all_docs = db.similarity_search("Financial Toolbox", k=min(10, doc_count))
    
    seen_content = set()
    duplicates = 0
    unique_pages = set()
    
    for i, doc in enumerate(all_docs, 1):
        content = doc.page_content
        metadata = doc.metadata
        
        # Detect duplicates
        content_hash = hash(content[:100])
        is_duplicate = content_hash in seen_content
        
        if is_duplicate:
            duplicates += 1
            status = "🔴 Duplicate"
        else:
            status = "✅"
            seen_content.add(content_hash)
        
        page = metadata.get('page', 'N/A')
        section = metadata.get('section', 'N/A')
        unique_pages.add(page)
        
        # Special tags
        tags = []
        if metadata.get('has_tables'):
            tags.append("📊Table")
        if metadata.get('has_code'):
            tags.append("💻Code")
        if metadata.get('has_formulas'):
            tags.append("🔢Formula")
        tag_str = " ".join(tags)
        
        print(f"\n{status} [{i}] Page {page} | Section: {section} {tag_str}")
        print(f"Words: {len(content.split())} | Chars: {len(content)}")
        
        # Display content summary
        excerpt = content.replace('\n', ' ')[:100]
        print(f"Summary: {excerpt}...")
        print("-" * 80)
    
    # Statistics on duplicates
    print(f"\n📊 Content Analysis:")
    print(f"   - Documents checked: {len(all_docs)}")
    print(f"   - Duplicate documents: {duplicates}")
    print(f"   - Unique pages: {len(unique_pages)}")
    
    if duplicates > 0:
        print(f"\n⚠️  Found {duplicates} duplicate documents!")
        print("   Suggestions:")
        print("   1. Delete data/vectorstore folder")
        print("   2. Re-run: python src/embeddings/build_vectorstore.py")
    else:
        print("\n✅ No obvious duplicates found!")
    
    # Test query functionality
    print(f"\n{'='*80}")
    print("🔍 Testing Similarity Search")
    print("=" * 80)
    
    test_queries = [
        "How to handle dates in MATLAB?",
        "What is Financial Toolbox?",
        "Matrix operations",
        "Portfolio optimization",
        "Bond duration calculation"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = db.similarity_search_with_score(query, k=3)
        
        for i, (doc, score) in enumerate(results, 1):
            page = doc.metadata.get('page', 'N/A')
            section = doc.metadata.get('section', 'N/A')
            has_tables = doc.metadata.get('has_tables', False)
            has_code = doc.metadata.get('has_code', False)
            has_formulas = doc.metadata.get('has_formulas', False)
            
            # Special tags
            tags = []
            if has_tables: tags.append("📊Table")
            if has_code: tags.append("💻Code")
            if has_formulas: tags.append("🔢Formula")
            tag_str = " ".join(tags) if tags else ""
            
            excerpt = doc.page_content.replace('\n', ' ')[:80]
            similarity = 1 - score  # Convert Chroma distance to similarity
            
            print(f"  [{i}] Page {page} | {section} {tag_str}")
            print(f"      Similarity: {similarity:.3f}")
            print(f"      {excerpt}...")
    
    print(f"\n{'='*80}")
    print("✅ Test complete!")
    print("=" * 80)


def check_chunks_json():
    """Check chunks_full.json"""
    chunks_file = Path("data/parsed/chunks_full.json")
    
    if not chunks_file.exists():
        print("⚠️  chunks_full.json does not exist")
        return
    
    print("\n" + "="*80)
    print("📋 Checking chunks_full.json")
    print("="*80)
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"Total chunks: {len(chunks)}")
    
    # Count pages
    page_counts = {}
    for chunk in chunks:
        page = chunk.get('page', 'unknown')
        page_counts[page] = page_counts.get(page, 0) + 1
    
    print(f"Unique pages: {len(page_counts)}")
    
    # Find duplicate pages
    duplicates = {page: count for page, count in page_counts.items() if count > 1}
    
    if duplicates:
        print(f"\n⚠️  Found duplicate pages:")
        for page, count in sorted(duplicates.items()):
            print(f"   - Page {page}: {count} times")
    else:
        print("✅ No duplicate pages")
    
    # Check content deduplication
    content_hashes = set()
    content_duplicates = 0
    
    for chunk in chunks:
        content = chunk.get('content', '')
        content_hash = hash(content[:200])
        
        if content_hash in content_hashes:
            content_duplicates += 1
        else:
            content_hashes.add(content_hash)
    
    if content_duplicates > 0:
        print(f"\n⚠️  Found {content_duplicates} chunks with duplicate content")
    else:
        print("\n✅ No duplicate content")


if __name__ == "__main__":
    # Check chunks_full.json first
    check_chunks_json()
    
    # Then test vectorstore
    print("\n")
    test_vectorstore()