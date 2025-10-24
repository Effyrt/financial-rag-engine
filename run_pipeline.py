#!/usr/bin/env python3
"""
Flexible Pipeline Runner - Test with any page range.

Usage:
    python run_pipeline.py --pages 5          # First 5 pages
    python run_pipeline.py --pages 20         # First 20 pages
    python run_pipeline.py --pages 100        # First 100 pages
    python run_pipeline.py --pages all        # Full PDF (3,462 pages)
    python run_pipeline.py --start 10 --end 30  # Pages 10-30
"""

import argparse
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.pdf_parser_docling_fixed import DoclingPDFParserFixed
from pipeline.chunker_strategies import (
    RecursiveStrategy,
    SemanticStrategy,
    HeadingAwareStrategy,
    CodeAwareStrategy,
    HybridStrategy,
    ChunkingConfig
)
from pipeline.embedder import EmbeddingGenerator
from pipeline.vector_store_chroma import ChromaVectorStore

load_dotenv()


def estimate_cost(num_pages: int) -> dict:
    """Estimate processing cost based on pages."""
    # Average ~400 tokens per page (rough estimate)
    est_tokens = num_pages * 400
    cost_per_1k = 0.00013
    est_cost = (est_tokens / 1000) * cost_per_1k
    
    return {
        "pages": num_pages,
        "estimated_tokens": est_tokens,
        "estimated_cost_usd": round(est_cost, 4)
    }


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def run_pipeline(
    pdf_path: str,
    max_pages: int = None,
    start_page: int = 1,
    end_page: int = None,
    namespace_prefix: str = "",
    skip_embeddings: bool = False,
    skip_upload: bool = False,
    auto_confirm: bool = False,
    use_existing_parsed: str = None,
    use_chromadb: bool = False
):
    """
    Run the complete pipeline with configurable options.
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Number of pages to process (None = all)
        namespace_prefix: Prefix for Pinecone namespaces (e.g., "test-")
        skip_embeddings: Skip embedding generation (for testing parsing/chunking)
        skip_upload: Skip Pinecone upload (for testing embeddings only)
    """
    
    # Validate inputs
    if not pdf_path or not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if start_page < 1:
        raise ValueError("start_page must be >= 1")
    
    if end_page and end_page < start_page:
        raise ValueError("end_page must be >= start_page")
    
    # Ensure output directories exist
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)
    
    # Determine page range for display
    if end_page is not None:
        page_range = f"pages {start_page}-{end_page}"
        actual_pages = end_page - start_page + 1
        estimate = estimate_cost(actual_pages)
        print_header(f"PIPELINE RUN: {page_range}")
        print(f"📊 Estimated cost: ${estimate['estimated_cost_usd']:.4f}")
        print(f"   (~{estimate['estimated_tokens']:,} tokens)")
    elif max_pages:
        estimate = estimate_cost(max_pages)
        print_header(f"PIPELINE RUN: First {max_pages} pages")
        print(f"📊 Estimated cost: ${estimate['estimated_cost_usd']:.4f}")
        print(f"   (~{estimate['estimated_tokens']:,} tokens)")
    else:
        print_header("PIPELINE RUN: FULL PDF")
        print("⚠️  This will process ALL pages!")
        
        # Get actual page count
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        estimate = estimate_cost(total_pages)
        
        print(f"📊 Total pages: {total_pages:,}")
        print(f"   Estimated cost: ${estimate['estimated_cost_usd']:.2f}")
        print(f"   Estimated tokens: {estimate['estimated_tokens']:,}")
        
        if not auto_confirm:
            confirm = input("\n⚠️  Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Cancelled")
                return
        else:
            print("\n✅ Auto-confirmed with --yes flag")
    
    print()
    
    # Set up output directory early (needed for loading existing parsed data)
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # STEP 1: Parse PDF or Load Existing Parsed Data
    if use_existing_parsed:
        print_header("STEP 1: LOADING EXISTING PARSED DATA")
        
        parsed_file_path = output_dir / use_existing_parsed
        if not parsed_file_path.exists():
            parsed_file_path = Path("data/processed") / use_existing_parsed
            
        if not parsed_file_path.exists():
            print(f"❌ Parsed data file not found: {use_existing_parsed}")
            print(f"   Tried: {parsed_file_path}")
            return
            
        print(f"📁 Loading: {parsed_file_path.name}")
        with open(parsed_file_path, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
        
        print(f"✅ Loaded existing parsed data")
    else:
        print_header("STEP 1: PDF PARSING (Docling)")
        
        # Set up parser with correct page range
        if end_page is not None:
            # Use start/end range
            parser = DoclingPDFParserFixed(start_page=start_page, max_pages=end_page-start_page+1)
        elif max_pages is None:
            # Full PDF
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            parser = DoclingPDFParserFixed(start_page=start_page, max_pages=total_pages)
        else:
            # Use max_pages from start_page
            parser = DoclingPDFParserFixed(start_page=start_page, max_pages=max_pages)
        
        parsed_data = parser.parse_pdf(pdf_path)
    
    print(f"✅ Parsed {parsed_data['metadata']['pages_processed']} pages")
    print(f"   Topics: {len(parsed_data['topics'])}")
    for topic in parsed_data['topics'][:5]:  # Show first 5
        print(f"   - [{topic['topic']}] {topic['title']}")
    if len(parsed_data['topics']) > 5:
        print(f"   ... and {len(parsed_data['topics']) - 5} more")
    
    # Determine pages_suffix for output files
    if use_existing_parsed:
        # Extract suffix from the filename (e.g., "docling_parsed_1_500.json" -> "1_500")
        import re
        match = re.search(r'(\d+_\d+|\d+p)', use_existing_parsed)
        if match:
            pages_suffix = match.group(1)
        else:
            pages_suffix = "resumed"
    elif end_page is not None:
        pages_suffix = f"{start_page}_{end_page}"
    elif max_pages:
        pages_suffix = f"{max_pages}p"
    else:
        pages_suffix = "full"
    
    # STEP 2: Chunk with Multiple Strategies & Auto-Select Best
    print_header("STEP 2: CHUNKING (Multi-Strategy Evaluation)")
    
    # Define all strategies to test
    strategies_to_test = [
        {
            "name": "recursive_500_50",
            "class": RecursiveStrategy,
            "config": ChunkingConfig(
                name="recursive_500_50",
                chunk_size=500,
                chunk_overlap=50,
                description="Small chunks, minimal overlap"
            )
        },
        {
            "name": "recursive_1000_100",
            "class": RecursiveStrategy,
            "config": ChunkingConfig(
                name="recursive_1000_100",
                chunk_size=1000,
                chunk_overlap=100,
                description="Baseline, balanced approach"
            )
        },
        {
            "name": "recursive_1500_200",
            "class": RecursiveStrategy,
            "config": ChunkingConfig(
                name="recursive_1500_200",
                chunk_size=1500,
                chunk_overlap=200,
                description="Large chunks, more context"
            )
        },
        {
            "name": "semantic_1200_150",
            "class": SemanticStrategy,
            "config": ChunkingConfig(
                name="semantic_1200_150",
                chunk_size=1200,
                chunk_overlap=150,
                description="Semantic boundary-aware"
            )
        },
        {
            "name": "heading_aware_1000_100",
            "class": HeadingAwareStrategy,
            "config": ChunkingConfig(
                name="heading_aware_1000_100",
                chunk_size=1000,
                chunk_overlap=100,
                description="Structure-preserving"
            )
        },
        {
            "name": "code_aware_1000_100",
            "class": CodeAwareStrategy,
            "config": ChunkingConfig(
                name="code_aware_1000_100",
                chunk_size=1000,
                chunk_overlap=100,
                description="Code block-aware"
            )
        },
        {
            "name": "hybrid_1000_100",
            "class": HybridStrategy,
            "config": ChunkingConfig(
                name="hybrid_1000_100",
                chunk_size=1000,
                chunk_overlap=100,
                description="Combined approach"
            )
        }
    ]
    
    print(f"   Testing {len(strategies_to_test)} strategies on first 10 pages...")
    print()
    
    # Test all strategies on first portion of text
    # Get text from parsed data (handle both formats)
    if 'pages' in parsed_data:
        test_pages = parsed_data['pages'][:min(10, len(parsed_data['pages']))]
        test_text = "\n\n".join([p['text'] for p in test_pages])
    elif 'full_text' in parsed_data:
        # For Docling format, use first ~10,000 chars (roughly 10 pages)
        test_text = parsed_data['full_text'][:10000]
    else:
        raise ValueError("Parsed data missing 'pages' or 'full_text' field")
    
    strategy_results = []
    
    for strategy_def in strategies_to_test:
        chunker = strategy_def['class'](strategy_def['config'])
        test_chunks = chunker.chunk(test_text, {'page_number': 1, 'source': pdf_path})
        
        # Calculate metrics (handle both field names)
        chunk_sizes = []
        for c in test_chunks:
            size = c.get('chunk_size', c.get('char_count', len(c.get('text', ''))))
            chunk_sizes.append(size)
        
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        
        # Optimal percentage (800-1200 chars)
        optimal_count = sum(1 for size in chunk_sizes if 800 <= size <= 1200)
        optimal_pct = (optimal_count / len(chunk_sizes) * 100) if chunk_sizes else 0
        
        # Variance
        variance = sum((size - avg_size) ** 2 for size in chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        
        result = {
            "name": strategy_def['name'],
            "class": strategy_def['class'],
            "config": strategy_def['config'],
            "chunks": len(test_chunks),
            "avg_size": int(avg_size),
            "optimal_pct": round(optimal_pct, 1),
            "variance": int(variance)
        }
        strategy_results.append(result)
        
        print(f"   ✓ {strategy_def['name']:<25} | Chunks: {len(test_chunks):>3} | Avg: {int(avg_size):>4} | Optimal: {optimal_pct:>5.1f}%")
    
    # Select best strategy - prioritize code-aware for financial documents
    # First try to find code_aware strategy, otherwise use highest optimal percentage
    code_aware_strategy = next((s for s in strategy_results if 'code_aware' in s['name']), None)
    
    if code_aware_strategy:
        best_strategy = code_aware_strategy
        print()
        print(f"   🏆 WINNER: {best_strategy['name']} (Code-Aware Selected)")
        print(f"      Optimal chunks: {best_strategy['optimal_pct']}%")
        print(f"      Average size: {best_strategy['avg_size']} chars")
        print(f"      Rationale: Code-aware chunking for financial documents with code blocks")
    else:
        best_strategy = max(strategy_results, key=lambda x: x['optimal_pct'])
        print()
        print(f"   🏆 WINNER: {best_strategy['name']}")
        print(f"      Optimal chunks: {best_strategy['optimal_pct']}%")
        print(f"      Average size: {best_strategy['avg_size']} chars")
        print(f"      Rationale: Highest % of chunks in optimal 800-1200 range")
    
    print()
    print(f"   Using {best_strategy['name']} for full document...")
    print()
    
    # Use best strategy for full document
    chunker = best_strategy['class'](best_strategy['config'])
    
    def enhance_chunk_with_structured_elements(chunk, parsed_data, topic_name=None):
        """Enhance chunk with references to nearby structured elements."""
        chunk_text = chunk.get('chunk_text', chunk.get('text', ''))
        
        # Add metadata about what types of content are in this chunk
        enhanced_chunk = chunk.copy()
        
        # Check for table references in this chunk's text
        tables_in_chunk = []
        for table in parsed_data.get('tables', []):
            table_content = str(table.get('content', ''))[:100]  # First 100 chars
            if table_content.lower() in chunk_text.lower()[-200:] or table_content.lower() in chunk_text.lower()[:200]:
                tables_in_chunk.append({
                    'table_id': f"table_{len(tables_in_chunk)}",
                    'content_preview': table_content,
                    'topic': table.get('topic', 'unknown')
                })
        
        # Check for code references
        code_in_chunk = []
        for code in parsed_data.get('code_blocks', []):
            code_content = str(code.get('content', '')).strip()
            # Only add code references if there's actual content
            if code_content and len(code_content) > 10:  # Minimum 10 chars for meaningful code
                if code_content.lower() in chunk_text.lower()[-200:] or code_content.lower() in chunk_text.lower()[:200]:
                    code_in_chunk.append({
                        'code_id': f"code_{len(code_in_chunk)}",
                        'content_preview': code_content[:100],
                        'language': code.get('language', 'unknown')
                    })
        
        # Check for images and figures in chunk
        images_in_chunk = []
        for img in parsed_data.get('images', []):
            if img.get('alt_text', '') and img.get('alt_text', '').lower() in chunk_text.lower():
                images_in_chunk.append({
                    'image_id': f"img_{len(images_in_chunk)}",
                    'alt_text': img.get('alt_text', ''),
                    'path': img.get('path', '')
                })
        
        figures_in_chunk = []
        for fig in parsed_data.get('figures', []):
            if fig.get('content', '') and fig.get('content', '').lower() in chunk_text.lower():
                figures_in_chunk.append({
                    'figure_id': f"fig_{len(figures_in_chunk)}",
                    'content': fig.get('content', ''),
                    'type': fig.get('type', 'reference')
                })
        
        # Add structured element references
        enhanced_chunk['has_tables'] = len(tables_in_chunk) > 0
        enhanced_chunk['has_code'] = len(code_in_chunk) > 0
        enhanced_chunk['has_formulas'] = '$' in chunk_text or 'formula' in chunk_text.lower()
        enhanced_chunk['has_images'] = len(images_in_chunk) > 0
        enhanced_chunk['has_figures'] = len(figures_in_chunk) > 0
        
        if tables_in_chunk:
            enhanced_chunk['table_references'] = tables_in_chunk
        if code_in_chunk:
            enhanced_chunk['code_references'] = code_in_chunk
        if images_in_chunk:
            enhanced_chunk['image_references'] = images_in_chunk
        if figures_in_chunk:
            enhanced_chunk['figure_references'] = figures_in_chunk
            
        return enhanced_chunk
    
    # Chunk all text
    all_chunks = []
    
    if 'pages' in parsed_data:
        # Original format with pages
        for page in parsed_data['pages']:
            page_chunks = chunker.chunk(
                text=page['text'],
                metadata={
                    'page_number': page['page_number'],
                    'source': pdf_path
                }
            )
            all_chunks.extend(page_chunks)
    elif 'full_text' in parsed_data:
        # Docling format with full_text
        full_text = parsed_data['full_text']
        page_chunks = chunker.chunk(
            text=full_text,
            metadata={
                'page_number': 1,  # Will be updated based on topics
                'source': pdf_path
            }
        )
        all_chunks.extend(page_chunks)
    
        # Post-process chunks to improve quality
        print("   🔧 Post-processing chunks for quality improvement...")
        
        def clean_chunk_text(text):
            """Clean chunk text by removing HTML artifacts and improving formatting"""
            if not text:
                return text
            
            # Remove HTML image placeholders
            text = text.replace('<!-- image -->', '[IMAGE]')
            text = text.replace('<!-- figure -->', '[FIGURE]')
            text = text.replace('<!-- table -->', '[TABLE]')
            
            # Clean up excessive whitespace
            import re
            text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 newlines
            text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
            
            return text.strip()
        
        # Clean all chunks
        for chunk in all_chunks:
            chunk_text = chunk.get('chunk_text', chunk.get('text', ''))
            cleaned_text = clean_chunk_text(chunk_text)
            chunk['chunk_text'] = cleaned_text
            chunk['chunk_size'] = len(cleaned_text)
            chunk['word_count'] = len(cleaned_text.split())
        
        # Filter out chunks that are too small (quality control)
        MIN_CHUNK_SIZE = 50  # Minimum 50 characters for meaningful content
        original_count = len(all_chunks)
        all_chunks = [
            chunk for chunk in all_chunks 
            if len(chunk.get('chunk_text', chunk.get('text', '')).strip()) >= MIN_CHUNK_SIZE
        ]
        filtered_count = original_count - len(all_chunks)
        
        if filtered_count > 0:
            print(f"   🧹 Filtered out {filtered_count} chunks smaller than {MIN_CHUNK_SIZE} characters")
        
        # Count cleaned artifacts
        html_artifacts = sum(1 for chunk in all_chunks if '[IMAGE]' in chunk.get('chunk_text', ''))
        print(f"   ✨ Cleaned HTML artifacts: {html_artifacts} chunks now have proper placeholders")
    
    # Organize chunks by topic
    chunks_by_topic = {}
    
    # For Docling format, distribute chunks across topics
    if parsed_data['topics'] and 'start_line' in parsed_data['topics'][0]:
        # Distribute chunks across topics (round-robin)
        topics = parsed_data['topics']
        for i, chunk in enumerate(all_chunks):
            topic_index = i % len(topics)
            matching_topic = topics[topic_index]['topic']
            
            if matching_topic not in chunks_by_topic:
                chunks_by_topic[matching_topic] = []
            
            # Convert to expected format (handle different field names)
            chunk_text = chunk.get('chunk_text', chunk.get('text', ''))
            chunk_size = chunk.get('chunk_size', chunk.get('char_count', len(chunk_text)))
            word_count = chunk.get('word_count', len(chunk_text.split()))
            page_num = chunk.get('page_number', chunk.get('metadata', {}).get('page_number', 1))
            
            # Provide base chunk for enhancement
            base_chunk = {
                "chunk_id": chunk['chunk_id'],
                "chunk_text": chunk_text,
                "chunk_size": chunk_size,
                "word_count": word_count,
                "topic": matching_topic,
                "source_file": pdf_path,
                "page_number": page_num,
                "strategy": best_strategy['name']
            }
            
            # Enhance chunk with structured element references
            enhanced_chunk = enhance_chunk_with_structured_elements(base_chunk, parsed_data, matching_topic)
            chunks_by_topic[matching_topic].append(enhanced_chunk)
    else:
        # Original logic for other formats
        for chunk in all_chunks:
            # Find which topic this chunk belongs to based on page number
            page_num = chunk.get('page_number', chunk.get('metadata', {}).get('page_number', 1))
            
            # Find matching topic
            matching_topic = None
            for topic in parsed_data['topics']:
                if 'start_page' in topic and 'end_page' in topic:
                    if topic['start_page'] <= page_num <= topic['end_page']:
                        matching_topic = topic['topic']
                        break
            
            if not matching_topic:
                matching_topic = "default"
            
            if matching_topic not in chunks_by_topic:
                chunks_by_topic[matching_topic] = []
            
            # Convert to expected format (handle different field names)
            chunk_text = chunk.get('chunk_text', chunk.get('text', ''))
            chunk_size = chunk.get('chunk_size', chunk.get('char_count', len(chunk_text)))
            word_count = chunk.get('word_count', len(chunk_text.split()))
            
            # Provide base chunk for enhancement
            base_chunk = {
                "chunk_id": chunk['chunk_id'],
                "chunk_text": chunk_text,
                "chunk_size": chunk_size,
                "word_count": word_count,
                "topic": matching_topic,
                "source_file": pdf_path,
                "page_number": page_num,
                "strategy": best_strategy['name']
            }
            
            # Enhance chunk with structured element references
            enhanced_chunk = enhance_chunk_with_structured_elements(base_chunk, parsed_data, matching_topic)
            chunks_by_topic[matching_topic].append(enhanced_chunk)
    
    total_chunks = sum(len(chunks) for chunks in chunks_by_topic.values())
    print(f"✅ Created {total_chunks} chunks across {len(chunks_by_topic)} topics")
    
    # Save chunks
    chunks_file = output_dir / f"chunks_{pages_suffix}.json"
    with open(chunks_file, 'w') as f:
        json.dump(chunks_by_topic, f, indent=2)
    
    # Save structured elements (tables, code, formulas, images) as separate retrievable items
    structured_elements = {
        "tables": parsed_data.get('tables', []),
        "code_blocks": parsed_data.get('code_blocks', []),
        "formulas": parsed_data.get('formulas', []),
        "images": parsed_data.get('images', []),
        "figures": parsed_data.get('figures', []),
        "metadata": {
            "total_tables": len(parsed_data.get('tables', [])),
            "total_code_blocks": len(parsed_data.get('code_blocks', [])),
            "total_formulas": len(parsed_data.get('formulas', [])),
            "total_images": len(parsed_data.get('images', [])),
            "total_figures": len(parsed_data.get('figures', [])),
            "source_file": pdf_path,
            "pages_processed": pages_suffix
        }
    }
    
    # Add structured elements file
    elements_file = output_dir / f"structured_elements_{pages_suffix}.json"
    with open(elements_file, 'w') as f:
        json.dump(structured_elements, f, indent=2)
    
    print(f"✅ Saved structured elements: {elements_file.name}")
    print(f"   • Tables: {len(structured_elements['tables'])}")
    print(f"   • Code blocks: {len(structured_elements['code_blocks'])}")
    print(f"   • Formulas: {len(structured_elements['formulas'])}")
    print(f"   • Images: {len(structured_elements['images'])}")
    print(f"   • Figures: {len(structured_elements['figures'])}")
    
    if skip_embeddings:
        print("\n⏭️  Skipping embeddings (--skip-embeddings)")
        print_summary(parsed_data, chunks_by_topic, None, False)
        return
    
    # STEP 3: Generate embeddings
    print_header("STEP 3: EMBEDDINGS")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in .env")
        print("   Add it to continue with embeddings")
        return
    
    generator = EmbeddingGenerator(
        model="text-embedding-3-large",
        dimension=3072
    )
    
    chunks_with_embeddings = {}
    for namespace, chunks in chunks_by_topic.items():
        print(f"   Processing: {namespace} ({len(chunks)} chunks)")
        chunks_with_emb = generator.embed_chunks(chunks)
        
        # Add namespace prefix if provided
        if namespace_prefix:
            new_namespace = f"{namespace_prefix}{namespace}"
            for chunk in chunks_with_emb:
                chunk['namespace'] = new_namespace
            chunks_with_embeddings[new_namespace] = chunks_with_emb
        else:
            chunks_with_embeddings[namespace] = chunks_with_emb
    
    cost_summary = generator.get_cost_summary()
    print(f"\n✅ Generated embeddings for {total_chunks} chunks")
    print(f"   Actual tokens: {cost_summary['total_tokens']:,}")
    print(f"   Actual cost: ${cost_summary['total_cost_usd']:.4f}")
    
    if skip_upload:
        print("\n⏭️  Skipping Pinecone upload (--skip-upload)")
        print_summary(parsed_data, chunks_by_topic, cost_summary, False)
        return
    
    # STEP 4: Upload to Vector Database
    if use_chromadb:
        print_header("STEP 4: CHROMADB UPLOAD")
        
        try:
            from pipeline.vector_store_chroma import ChromaVectorStore
            
            vector_store = ChromaVectorStore(
                collection_name="financial-concepts",
                dimension=3072,
                distance_metric="cosine"
            )
            
            # Upload all chunks at once (ChromaDB handles topic organization internally)
            all_chunks = []
            for namespace, chunks in chunks_with_embeddings.items():
                all_chunks.extend(chunks)
            
            print(f"   Uploading {len(all_chunks)} vectors to ChromaDB...")
            result = vector_store.upsert_vectors(chunks=all_chunks)
            print(f"   ✅ Uploaded {result['upserted_count']} vectors")
            print(f"   Topics processed: {result['topics_processed']}")
            
            # Get stats
            stats = vector_store.get_collection_stats()
            print(f"\n✅ Upload complete!")
            print(f"   Total collections: {stats['total_collections']}")
            print(f"   Collections: {list(stats['collections'].keys())[:5]}...")
            
        except ImportError:
            print("❌ ChromaDB not installed. Install with: pip install chromadb")
            print("   Falling back to Pinecone...")
            use_chromadb = False
    
    if not use_chromadb:
        print_header("STEP 4: PINECONE UPLOAD")
        
        if not os.getenv("PINECONE_API_KEY"):
            print("❌ PINECONE_API_KEY not found in .env")
            print("   Add it to continue with upload")
            return
        
        # Fallback to Pinecone (if available)
        try:
            from pipeline.vector_store_pinecone import PineconeVectorStore
            vector_store = PineconeVectorStore(
                index_name="financial-concepts",
                dimension=3072,
                metric="cosine"
            )
        except ImportError:
            print("❌ Neither ChromaDB nor Pinecone available. Please install one of them.")
            return
        
        print("   Ensuring index exists...")
        vector_store.create_index_if_not_exists()
        
        # Upload by namespace
        for namespace, chunks in chunks_with_embeddings.items():
            print(f"   Uploading: {namespace} ({len(chunks)} vectors)")
            result = vector_store.upsert_vectors(chunks=chunks, namespace=namespace)
            print(f"   ✅ Uploaded {result['upserted_count']} vectors")
        
        # Get stats
        import time
        print("\n   Waiting for index sync...")
        time.sleep(3)
        
        stats = vector_store.get_index_stats()
        print(f"\n✅ Upload complete!")
        print(f"   Total vectors in index: {stats['total_vector_count']}")
        print(f"   Namespaces: {len(stats.get('namespaces', {}))}")
    
    print_summary(parsed_data, chunks_by_topic, cost_summary, True)


def print_summary(parsed_data, chunks_by_topic, cost_summary, uploaded):
    """Print final summary."""
    print_header("SUMMARY")
    
    print(f"✅ Parsed: {parsed_data['metadata']['pages_processed']} pages")
    print(f"✅ Topics: {len(parsed_data['topics'])}")
    
    total_chunks = sum(len(c) for c in chunks_by_topic.values())
    print(f"✅ Chunks: {total_chunks} across {len(chunks_by_topic)} namespaces")
    
    if cost_summary:
        print(f"✅ Embeddings: {cost_summary['total_tokens']:,} tokens")
        print(f"   Cost: ${cost_summary['total_cost_usd']:.4f}")
    
    if uploaded:
        print(f"✅ Uploaded to Pinecone")
    
    print("\n" + "="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run the Financial RAG pipeline with configurable options"
    )
    
    parser.add_argument(
        "--pages",
        type=str,
        default="5",
        help="Number of pages to process (or 'all' for full PDF)"
    )
    
    parser.add_argument(
        "--pdf",
        type=str,
        default="fintbx.pdf",
        help="Path to PDF file"
    )
    
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting page number (1-indexed)"
    )
    
    parser.add_argument(
        "--end",
        type=int,
        help="Ending page number (inclusive, 1-indexed)"
    )
    
    parser.add_argument(
        "--namespace-prefix",
        type=str,
        default="",
        help="Prefix for Pinecone namespaces (e.g., 'test-')"
    )
    
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding generation (test parsing/chunking only)"
    )
    
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip Pinecone upload (test embeddings only)"
    )
    
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-confirm (skip confirmation prompt)"
    )
    
    parser.add_argument(
        "--use-existing-parsed",
        type=str,
        help="Use existing parsed data file instead of parsing (provide filename like 'docling_parsed_1_500.json')"
    )
    
    parser.add_argument(
        "--use-chromadb",
        action="store_true",
        help="Use ChromaDB instead of Pinecone (no namespace limitations)"
    )
    
    args = parser.parse_args()
    
    # Parse pages argument
    start_page = args.start
    end_page = args.end
    
    if args.end is not None:
        # Use start/end range
        max_pages = None  # Not used for range
        pages_text = f"pages {start_page}-{end_page}"
    elif args.pages.lower() == "all":
        max_pages = None
        start_page = 1
        end_page = None
        pages_text = "all pages"
    else:
        try:
            max_pages = int(args.pages)
            start_page = 1
            end_page = max_pages
            pages_text = f"first {max_pages} pages"
        except ValueError:
            print(f"❌ Invalid --pages value: {args.pages}")
            print("   Use a number (e.g., 5, 20, 100) or 'all'")
            return
    
    # Check PDF exists
    if not Path(args.pdf).exists():
        print(f"❌ PDF not found: {args.pdf}")
        return
    
    # Run pipeline
    run_pipeline(
        pdf_path=args.pdf,
        max_pages=max_pages,
        start_page=start_page,
        end_page=end_page,
        namespace_prefix=args.namespace_prefix,
        skip_embeddings=args.skip_embeddings,
        skip_upload=args.skip_upload,
        auto_confirm=args.yes,
        use_existing_parsed=args.use_existing_parsed,
        use_chromadb=args.use_chromadb
    )


if __name__ == "__main__":
    main()

