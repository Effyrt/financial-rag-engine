# Phase 0.4: Docling PDF Parsing Test

**Duration:** 1-2 hours  
**Prerequisites:** Python environment, fintbx.pdf file

---

## Overview

Test and validate Docling's PDF parsing capabilities with the Financial Toolbox User's Guide.

## Tasks

### 1. Install Docling

```bash
# Activate virtual environment
source venv/bin/activate

# Install Docling and dependencies
pip install docling==2.1.3
pip install docling-core==2.1.1

# Update requirements
pip freeze | grep docling >> requirements.txt
```

### 2. Verify fintbx.pdf

```bash
# Check if PDF exists
ls -lh data/raw/fintbx.pdf

# If not present, download or copy it
# cp /path/to/fintbx.pdf data/raw/

# Get PDF info
pdfinfo data/raw/fintbx.pdf || echo "Install poppler-utils for pdfinfo"
```

### 3. Create Basic Docling Test Script

```python
# scripts/test_docling_basic.py
"""
Basic test of Docling PDF parsing capabilities.
"""
from pathlib import Path
from docling.document_converter import DocumentConverter
import json

def test_basic_parsing():
    """Test basic PDF parsing with Docling."""
    
    # Initialize converter
    converter = DocumentConverter()
    
    # Path to PDF
    pdf_path = Path("data/raw/fintbx.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return False
    
    print(f"📄 Parsing PDF: {pdf_path}")
    print(f"   File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        # Convert PDF
        result = converter.convert(str(pdf_path))
        
        # Get document
        doc = result.document
        
        # Print basic stats
        print(f"\n✅ Parsing successful!")
        print(f"   Pages: {len(doc.pages)}")
        print(f"   Text length: {len(doc.export_to_text())} characters")
        
        # Export to different formats
        output_dir = Path("data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export to markdown
        markdown_path = output_dir / "fintbx_parsed.md"
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(doc.export_to_markdown())
        print(f"   Markdown saved: {markdown_path}")
        
        # Export to JSON
        json_path = output_dir / "fintbx_parsed.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc.export_to_dict(), f, indent=2)
        print(f"   JSON saved: {json_path}")
        
        # Sample first page
        print(f"\n📝 First page preview:")
        first_page_text = doc.pages[0].export_to_text()
        print(first_page_text[:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_parsing()
    exit(0 if success else 1)
```

Run the test:

```bash
python scripts/test_docling_basic.py
```

### 4. Test Advanced Features

```python
# scripts/test_docling_advanced.py
"""
Advanced Docling features: tables, formulas, structure extraction.
"""
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import json

def test_advanced_parsing():
    """Test advanced parsing features."""
    
    # Configure pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True  # Extract table structure
    pipeline_options.do_ocr = False  # Disable OCR (not needed for text PDFs)
    
    # Initialize converter with options
    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    pdf_path = Path("data/raw/fintbx.pdf")
    
    print("📄 Parsing with advanced features...")
    result = converter.convert(str(pdf_path))
    doc = result.document
    
    # Analyze document structure
    print(f"\n📊 Document Structure Analysis:")
    
    # Count elements by type
    element_counts = {}
    for page in doc.pages:
        for element in page.elements:
            elem_type = type(element).__name__
            element_counts[elem_type] = element_counts.get(elem_type, 0) + 1
    
    print("   Element types found:")
    for elem_type, count in sorted(element_counts.items()):
        print(f"     - {elem_type}: {count}")
    
    # Extract tables
    print(f"\n📋 Table Extraction:")
    tables = []
    for page_num, page in enumerate(doc.pages, 1):
        for element in page.elements:
            if hasattr(element, 'table'):
                tables.append({
                    'page': page_num,
                    'table': element.table
                })
    
    print(f"   Found {len(tables)} tables")
    if tables:
        print(f"   First table on page {tables[0]['page']}")
    
    # Extract formulas/equations
    print(f"\n🔢 Formula Extraction:")
    formulas = []
    for page_num, page in enumerate(doc.pages, 1):
        for element in page.elements:
            if hasattr(element, 'formula') or 'equation' in str(type(element)).lower():
                formulas.append({
                    'page': page_num,
                    'content': str(element)
                })
    
    print(f"   Found {len(formulas)} formulas/equations")
    
    # Extract headings/sections
    print(f"\n📑 Document Structure:")
    headings = []
    for page_num, page in enumerate(doc.pages, 1):
        for element in page.elements:
            if hasattr(element, 'level') or 'heading' in str(type(element)).lower():
                headings.append({
                    'page': page_num,
                    'level': getattr(element, 'level', 'unknown'),
                    'text': str(element)[:100]
                })
    
    print(f"   Found {len(headings)} headings")
    if headings[:5]:
        print("   First 5 headings:")
        for h in headings[:5]:
            print(f"     Page {h['page']}: {h['text']}")
    
    # Save detailed analysis
    analysis = {
        'total_pages': len(doc.pages),
        'element_counts': element_counts,
        'tables_count': len(tables),
        'formulas_count': len(formulas),
        'headings_count': len(headings),
        'tables': tables[:5],  # First 5 tables
        'headings': headings[:20]  # First 20 headings
    }
    
    output_path = Path("data/processed/fintbx_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"\n✅ Analysis saved: {output_path}")
    return True

if __name__ == "__main__":
    success = test_advanced_parsing()
    exit(0 if success else 1)
```

Run advanced test:

```bash
python scripts/test_docling_advanced.py
```

### 5. Test Chunking Strategy

```python
# scripts/test_chunking.py
"""
Test different chunking strategies for the parsed PDF.
"""
from pathlib import Path
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from docling.document_converter import DocumentConverter

def test_chunking_strategies():
    """Test different chunking approaches."""
    
    # Parse PDF
    converter = DocumentConverter()
    result = converter.convert("data/raw/fintbx.pdf")
    doc = result.document
    full_text = doc.export_to_text()
    
    print(f"📄 Full document: {len(full_text)} characters")
    
    # Test different chunk sizes
    strategies = [
        {"chunk_size": 500, "chunk_overlap": 50},
        {"chunk_size": 1000, "chunk_overlap": 100},
        {"chunk_size": 1500, "chunk_overlap": 150},
    ]
    
    results = {}
    
    for strategy in strategies:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=strategy["chunk_size"],
            chunk_overlap=strategy["chunk_overlap"],
            length_function=len,
        )
        
        chunks = splitter.split_text(full_text)
        
        # Calculate stats
        chunk_lengths = [len(c) for c in chunks]
        avg_length = sum(chunk_lengths) / len(chunk_lengths)
        
        results[f"{strategy['chunk_size']}_{strategy['chunk_overlap']}"] = {
            "chunk_size": strategy["chunk_size"],
            "chunk_overlap": strategy["chunk_overlap"],
            "num_chunks": len(chunks),
            "avg_chunk_length": avg_length,
            "min_chunk_length": min(chunk_lengths),
            "max_chunk_length": max(chunk_lengths),
            "sample_chunk": chunks[0][:200] + "..."
        }
        
        print(f"\n📊 Strategy: {strategy['chunk_size']} chars, {strategy['chunk_overlap']} overlap")
        print(f"   Chunks created: {len(chunks)}")
        print(f"   Avg length: {avg_length:.0f} chars")
        print(f"   Range: {min(chunk_lengths)}-{max(chunk_lengths)} chars")
    
    # Save results
    output_path = Path("data/processed/chunking_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Chunking analysis saved: {output_path}")
    return True

if __name__ == "__main__":
    # Install langchain if needed
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        print("Installing langchain...")
        import subprocess
        subprocess.check_call(["pip", "install", "langchain==0.1.9"])
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    success = test_chunking_strategies()
    exit(0 if success else 1)
```

Run chunking test:

```bash
python scripts/test_chunking.py
```

### 6. Create Parsing Quality Report

```python
# scripts/generate_parsing_report.py
"""
Generate comprehensive parsing quality report.
"""
from pathlib import Path
import json
from datetime import datetime

def generate_report():
    """Generate parsing quality report."""
    
    # Load analysis files
    analysis_path = Path("data/processed/fintbx_analysis.json")
    chunking_path = Path("data/processed/chunking_analysis.json")
    
    if not analysis_path.exists():
        print("❌ Run test_docling_advanced.py first")
        return False
    
    with open(analysis_path) as f:
        analysis = json.load(f)
    
    with open(chunking_path) as f:
        chunking = json.load(f)
    
    # Generate report
    report = f"""
# Docling Parsing Quality Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Document Overview

- **Total Pages:** {analysis['total_pages']}
- **Tables Found:** {analysis['tables_count']}
- **Formulas Found:** {analysis['formulas_count']}
- **Headings Found:** {analysis['headings_count']}

## Element Types

"""
    
    for elem_type, count in sorted(analysis['element_counts'].items()):
        report += f"- **{elem_type}:** {count}\n"
    
    report += "\n## Chunking Strategy Comparison\n\n"
    report += "| Chunk Size | Overlap | Num Chunks | Avg Length | Min | Max |\n"
    report += "|------------|---------|------------|------------|-----|-----|\n"
    
    for strategy_name, data in chunking.items():
        report += f"| {data['chunk_size']} | {data['chunk_overlap']} | {data['num_chunks']} | {data['avg_chunk_length']:.0f} | {data['min_chunk_length']} | {data['max_chunk_length']} |\n"
    
    report += "\n## Recommendations\n\n"
    report += "1. **Parsing Quality:** "
    if analysis['tables_count'] > 0:
        report += "✅ Tables detected successfully\n"
    else:
        report += "⚠️ No tables detected - verify table extraction settings\n"
    
    report += "2. **Chunking Strategy:** "
    best_strategy = max(chunking.items(), key=lambda x: x[1]['num_chunks'])
    report += f"Recommend {best_strategy[1]['chunk_size']} chars with {best_strategy[1]['chunk_overlap']} overlap\n"
    
    report += "3. **Next Steps:**\n"
    report += "   - Review sample chunks for quality\n"
    report += "   - Test embedding generation\n"
    report += "   - Validate retrieval accuracy\n"
    
    # Save report
    report_path = Path("data/processed/parsing_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    print(report)
    print(f"\n✅ Report saved: {report_path}")
    return True

if __name__ == "__main__":
    success = generate_report()
    exit(0 if success else 1)
```

Run report generation:

```bash
python scripts/generate_parsing_report.py
```

## Verification Checklist

- [ ] Docling installed successfully
- [ ] fintbx.pdf file present in `data/raw/`
- [ ] Basic parsing test passed
- [ ] PDF converted to markdown
- [ ] PDF converted to JSON
- [ ] Advanced features tested (tables, formulas, structure)
- [ ] Chunking strategies compared
- [ ] Parsing quality report generated
- [ ] No critical parsing errors
- [ ] Sample output looks reasonable

## Expected Outputs

After running all tests, you should have:

```
data/processed/
├── fintbx_parsed.md          # Full document in markdown
├── fintbx_parsed.json         # Full document in JSON
├── fintbx_analysis.json       # Structure analysis
├── chunking_analysis.json     # Chunking comparison
└── parsing_report.md          # Quality report
```

## Troubleshooting

### Issue: Docling installation fails
```bash
# Try installing with specific versions
pip install --upgrade pip
pip install docling==2.1.3 docling-core==2.1.1

# If still fails, check Python version
python --version  # Should be 3.10+
```

### Issue: PDF not found
```bash
# Verify PDF location
ls -la data/raw/fintbx.pdf

# Copy PDF if needed
cp /path/to/fintbx.pdf data/raw/
```

### Issue: Memory errors
```bash
# Docling can be memory-intensive for large PDFs
# Monitor memory usage
# Consider processing in batches if needed
```

### Issue: Poor table extraction
```python
# Try different pipeline options
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
```

## Quality Assessment Criteria

✅ **Good parsing if:**
- All pages extracted
- Tables preserved
- Formulas captured
- Headings identified
- Text is coherent
- No major formatting issues

⚠️ **Review needed if:**
- Missing pages
- Tables corrupted
- Formulas lost
- Poor text quality
- Encoding issues

## Next Steps

1. **Review parsing quality** - Check generated markdown/JSON
2. **Select chunking strategy** - Based on analysis results
3. **Proceed to Phase 1** - Start building the ingestion pipeline
4. **Document any issues** - Note limitations or workarounds needed

## Resources

- [Docling Documentation](https://github.com/DS4SD/docling)
- [Docling Examples](https://github.com/DS4SD/docling/tree/main/examples)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [PDF Processing Best Practices](https://www.docugami.com/blog/pdf-processing-best-practices)

