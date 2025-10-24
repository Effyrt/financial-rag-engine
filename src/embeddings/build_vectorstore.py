# build_vectorstore.py (Lab 1 version - using OpenAI Embeddings)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def chunk_docs(input_path="data/parsed/chunks_full.json"):
    """Read and split documents, preserving complete metadata"""
    
    if not Path(input_path).exists():
        print(f"❌ Error: {input_path} does not exist")
        print("   Please run first: python convert_docling_to_chunks.py")
        return None
    
    with open(input_path, "r", encoding="utf-8") as f:
        pages = json.load(f)
    
    print(f"📖 Read {len(pages)} original pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )
    
    chunks = []
    for page_data in pages:
        text = page_data["content"]
        
        # Split text
        split_texts = splitter.split_text(text)
        
        # Preserve complete metadata for each split
        for chunk_text in split_texts:
            chunks.append({
                "content": chunk_text,
                "page": page_data.get("page", "unknown"),
                "section": page_data.get("section", "N/A"),
                "title": page_data.get("title", ""),
                "source": page_data.get("source", "unknown"),
                "has_tables": page_data.get("has_tables", False),
                "has_code": page_data.get("has_code", False),
                "has_formulas": page_data.get("has_formulas", False)
            })
    
    print(f"✅ Generated {len(chunks)} chunks from {len(pages)} pages.")
    return chunks

def build_chroma(chunks):
    """Build vector database (using OpenAI text-embedding-3-large)"""
    
    if chunks is None:
        print("❌ No chunks to process")
        return None
    
    import shutil
    
    # Check OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not set")
        print("   Please add to .env file:")
        print("   OPENAI_API_KEY=your-key-here")
        return None
    
    # ⚠️ Delete old vectorstore to avoid duplication
    vectorstore_path = Path("data/vectorstore")
    if vectorstore_path.exists():
        print(f"🗑️  Removing old vectorstore: {vectorstore_path}")
        shutil.rmtree(vectorstore_path)
    
    # Use OpenAI text-embedding-3-large (Lab 1 requirement)
    print(f"\n🤖 Initializing OpenAI Embeddings")
    print(f"   Model: text-embedding-3-large")
    print(f"   Dimensions: 3072")
    print(f"   ⚠️  This will use OpenAI API (paid service)")
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # Convert to Document objects, preserving all metadata
    documents = []
    for c in chunks:
        doc = Document(
            page_content=c["content"],
            metadata={
                "page": c["page"],
                "section": c["section"],
                "title": c["title"],
                "source": c["source"],
                "has_tables": c["has_tables"],
                "has_code": c["has_code"],
                "has_formulas": c["has_formulas"]
            }
        )
        documents.append(doc)
    
    print(f"\n💾 Building vectorstore...")
    print(f"   Processing {len(documents)} documents...")
    
    # Build vectorstore
    try:
        db = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=str(vectorstore_path)
        )
        
        print("✅ Vectorstore built and saved in data/vectorstore")
        print(f"\n📊 Statistics:")
        print(f"   - Total documents: {len(documents)}")
        
        # Count metadata
        sections = set(d.metadata.get('section', 'N/A') for d in documents)
        pages = set(d.metadata.get('page', 'unknown') for d in documents)
        
        print(f"   - Unique pages: {len(pages)}")
        print(f"   - Unique sections: {len(sections)}")
        print(f"   - Chunks with tables: {sum(1 for d in documents if d.metadata.get('has_tables'))}")
        print(f"   - Chunks with code: {sum(1 for d in documents if d.metadata.get('has_code'))}")
        print(f"   - Chunks with formulas: {sum(1 for d in documents if d.metadata.get('has_formulas'))}")
        
        # Save configuration
        config = {
            'embedding_model': 'text-embedding-3-large',
            'embedding_dimension': 3072,
            'embedding_provider': 'OpenAI',
            'chunking_strategy': 'RecursiveCharacterTextSplitter',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'total_documents': len(documents),
            'unique_pages': len(pages),
            'unique_sections': len(sections)
        }
        
        config_file = Path("data/vectorstore_config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n💾 Configuration saved: {config_file}")
        
        # Test query
        print(f"\n🔍 Testing query functionality...")
        test_query = "What is Financial Toolbox?"
        results = db.similarity_search(test_query, k=3)
        
        print(f"   Query: '{test_query}'")
        for i, doc in enumerate(results, 1):
            page = doc.metadata.get('page', 'N/A')
            section = doc.metadata.get('section', 'N/A')
            preview = doc.page_content[:60].replace('\n', ' ')
            print(f"   [{i}] Page {page} | {section}")
            print(f"       {preview}...")
        
        print(f"\n{'='*80}")
        print("✅ Lab 1 Task 3 & 4 Complete!")
        print("="*80)
        print("\n✅ Used:")
        print("   - OpenAI text-embedding-3-large (3072 dimensions)")
        print("   - ChromaDB storage")
        print("   - Complete metadata (sections, pages)")
        print("\n💡 Next steps:")
        print("   - Test retrieval: python test.py")
        print("   - Evaluate performance: python src/experiments/retrieval_evaluation.py")
        
        return db
        
    except Exception as e:
        print(f"\n❌ Failed to build vectorstore: {e}")
        print("\nPossible reasons:")
        print("   1. Invalid OpenAI API Key")
        print("   2. Insufficient API quota")
        print("   3. Network connection issues")
        return None

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 Lab 1 - Build Vectorstore")
    print("="*80)
    print("\nUsing OpenAI text-embedding-3-large (Lab 1 requirement)")
    print("⚠️  This will use OpenAI API (paid service)")
    print("\nFor free alternative, use build_vectorstore_huggingface.py")
    print("="*80 + "\n")
    
    chunks = chunk_docs()
    
    if chunks:
        db = build_chroma(chunks)
        
        if db:
            print("\n🎉 Success!")
        else:
            print("\n❌ Failed, please check error messages")
    else:
        print("\n❌ Unable to read chunks")