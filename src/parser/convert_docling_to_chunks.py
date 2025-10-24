# convert_docling_to_chunks.py
import json
from pathlib import Path
from typing import Dict, List, Any

class DoclingParser:
    """Parse Docling's complex reference structure"""
    
    def __init__(self, docling_data: Dict[str, Any]):
        self.doc = docling_data
        
        # Build reference index
        self.texts = {item['self_ref']: item for item in docling_data.get('texts', [])}
        self.tables = {item['self_ref']: item for item in docling_data.get('tables', [])}
        self.pictures = {item['self_ref']: item for item in docling_data.get('pictures', [])}
        self.groups = {item['self_ref']: item for item in docling_data.get('groups', [])}
        
        # Page information
        self.pages_info = docling_data.get('pages', {})
    
    def resolve_ref(self, ref_obj: Dict[str, str]) -> Dict[str, Any]:
        """Resolve $ref references"""
        if not isinstance(ref_obj, dict):
            return {}
        
        ref = ref_obj.get('$ref', '')
        
        if ref.startswith('#/texts/'):
            return self.texts.get(ref, {})
        elif ref.startswith('#/tables/'):
            return self.tables.get(ref, {})
        elif ref.startswith('#/pictures/'):
            return self.pictures.get(ref, {})
        elif ref.startswith('#/groups/'):
            return self.groups.get(ref, {})
        
        return {}
    
    def extract_text_from_node(self, node: Dict[str, Any]) -> str:
        """Recursively extract text from node"""
        if not node:
            return ''
        
        # Resolve reference first if it's a reference
        if '$ref' in node:
            node = self.resolve_ref(node)
        
        # Direct text content
        if 'text' in node:
            return node['text']
        
        # Process children (recursive)
        if 'children' in node:
            texts = []
            for child_ref in node['children']:
                child_node = self.resolve_ref(child_ref)
                child_text = self.extract_text_from_node(child_node)
                if child_text.strip():
                    texts.append(child_text)
            return '\n'.join(texts)
        
        return ''
    
    def extract_table_text(self, table: Dict[str, Any]) -> str:
        """Extract table content"""
        if 'data' not in table or 'table_cells' not in table['data']:
            return ''
        
        cells = table['data']['table_cells']
        grid = table['data'].get('grid', [])
        
        if not grid:
            # No grid structure, concatenate directly
            return '\n'.join(cell.get('text', '') for cell in cells if cell.get('text', '').strip())
        
        # Use grid to maintain table format
        rows = []
        for row in grid:
            row_texts = []
            for cell in row:
                if isinstance(cell, dict) and cell.get('text', '').strip():
                    row_texts.append(cell['text'])
            if row_texts:
                rows.append(' | '.join(row_texts))
        
        return '\n'.join(rows)
    
    def get_page_number(self, node: Dict[str, Any]) -> int:
        """Get page number of node"""
        prov = node.get('prov', [])
        if prov and isinstance(prov, list) and len(prov) > 0:
            return prov[0].get('page_no', 1)
        return 1
    
    def parse_to_pages(self) -> List[Dict[str, Any]]:
        """Convert Docling structure to page-grouped format"""
        # Group content by page number
        pages_content = {}
        current_section = "Document Start"
        
        body = self.doc.get('body', {})
        children = body.get('children', [])
        
        for child_ref in children:
            node = self.resolve_ref(child_ref)
            if not node:
                continue
            
            label = node.get('label', '')
            page_no = self.get_page_number(node)
            
            # Initialize page
            if page_no not in pages_content:
                pages_content[page_no] = {
                    'texts': [],
                    'tables': [],
                    'figures': [],
                    'code_blocks': [],
                    'formulas': [],
                    'section': current_section
                }
            
            # Update section
            if label == 'section_header':
                section_text = self.extract_text_from_node(node)
                if section_text:
                    current_section = section_text
                    pages_content[page_no]['section'] = current_section
            
            # Extract text
            if label in ['text', 'paragraph', 'section_header']:
                text = self.extract_text_from_node(node)
                if text.strip():
                    pages_content[page_no]['texts'].append(text)
            
            # Extract tables
            elif 'table' in label.lower() or label == 'document_index':
                table_text = self.extract_table_text(node)
                if table_text.strip():
                    pages_content[page_no]['tables'].append(table_text)
            
            # Extract figure captions
            elif label == 'picture':
                caption = node.get('caption', '')
                if caption:
                    pages_content[page_no]['figures'].append(caption)
            
            # Extract code (if any)
            elif label == 'code':
                code = self.extract_text_from_node(node)
                if code.strip():
                    pages_content[page_no]['code_blocks'].append(code)
        
        # Convert to list format
        pages_list = []
        for page_no in sorted(pages_content.keys()):
            page_data = pages_content[page_no]
            
            # Combine page content
            content_parts = []
            content_parts.extend(page_data['texts'])
            
            if page_data['tables']:
                content_parts.append('\n[Table Content]\n' + '\n\n'.join(page_data['tables']))
            
            if page_data['code_blocks']:
                content_parts.append('\n[Code]\n' + '\n\n'.join(page_data['code_blocks']))
            
            full_content = '\n\n'.join(content_parts)
            
            pages_list.append({
                'page_no': page_no,
                'content': full_content,
                'section': page_data['section'],
                'tables': page_data['tables'],
                'figures': page_data['figures'],
                'code_blocks': page_data['code_blocks'],
                'formulas': page_data['formulas']
            })
        
        return pages_list


def detect_section(text):
    """Intelligently detect section"""
    if not text:
        return "Empty Page"
    
    text_lower = text.lower()
    first_line = text.split('\n')[0].strip() if text else ""
    
    # Keyword matching
    if "contact" in text_lower or "mathworks" in text_lower:
        return "Contact Information"
    elif "copyright" in text_lower or "©" in text or "trademark" in text_lower:
        return "Legal & Copyright"
    elif "revision" in text_lower or "history" in text_lower:
        return "Revision History"
    elif "contents" in text_lower and len(text) < 500:
        return "Table of Contents"
    elif "portfolio" in text_lower:
        return "Portfolio Management"
    elif "risk" in text_lower:
        return "Risk Analysis"
    elif "pricing" in text_lower or "valuation" in text_lower:
        return "Pricing & Valuation"
    elif "sharpe" in text_lower:
        return "Performance Metrics"
    elif "duration" in text_lower or "fixed income" in text_lower:
        return "Fixed Income"
    elif "getting started" in text_lower:
        return "Getting Started"
    elif "matrix" in text_lower and "function" in text_lower:
        return "Matrix Functions"
    elif "date" in text_lower and "format" in text_lower:
        return "Date Handling"
    elif "cash flow" in text_lower:
        return "Cash Flow Analysis"
    elif len(first_line) < 100 and first_line and not first_line.isdigit():
        return first_line
    else:
        return "Main Content"


def convert_docling_to_standard_format():
    """Convert Docling output to standard format"""
    
    # Read Docling output
    docling_file = Path("data/parsed/fintbx_docling.json")
    
    if not docling_file.exists():
        print(f"❌ Docling output file does not exist: {docling_file}")
        print("   Please run first: python docling_or_fallback_parser.py")
        return
    
    print(f"📖 Reading Docling output: {docling_file}")
    
    with open(docling_file, "r", encoding="utf-8") as f:
        docling_data = json.load(f)
    
    print(f"   ✓ Docling format: {docling_data.get('schema_name', 'Unknown')}")
    print(f"   ✓ Version: {docling_data.get('version', 'Unknown')}")
    
    # Use specialized parser
    parser = DoclingParser(docling_data)
    pages = parser.parse_to_pages()
    
    print(f"📄 Parsed {len(pages)} pages of content")
    
    # Convert to standard format
    standard_docs = []
    
    for page_data in pages:
        page_text = page_data['content']
        
        if not page_text or len(page_text.strip()) < 10:
            continue
        
        # Use default section or intelligent detection
        section = page_data.get('section', 'Main Content')
        if section == "Document Start":
            section = detect_section(page_text)
        
        title = page_text.split('\n')[0].strip()[:200] if page_text else "Untitled"
        
        # Build document
        doc = {
            "page": page_data['page_no'],
            "content": page_text.strip(),
            "section": section,
            "title": title,
            "source": "fintbx.pdf",
            
            "word_count": len(page_text.split()),
            "char_count": len(page_text),
            
            "code_blocks": page_data['code_blocks'],
            "code_count": len(page_data['code_blocks']),
            
            "formulas": page_data['formulas'],
            "formula_count": len(page_data['formulas']),
            
            "figure_captions": page_data['figures'],
            "figure_count": len(page_data['figures']),
            
            "table_captions": page_data['tables'],
            "table_count": len(page_data['tables']),
            
            "has_code": len(page_data['code_blocks']) > 0,
            "has_formulas": len(page_data['formulas']) > 0,
            "has_figures": len(page_data['figures']) > 0,
            "has_tables": len(page_data['tables']) > 0
        }
        
        standard_docs.append(doc)
    
    if not standard_docs:
        print("⚠️  Warning: No content parsed!")
        return None
    
    # Save standard format
    output_file = Path("data/parsed/chunks_full.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(standard_docs, f, indent=2, ensure_ascii=False)
    
    # Statistics
    total_code = sum(d["code_count"] for d in standard_docs)
    total_formulas = sum(d["formula_count"] for d in standard_docs)
    total_figures = sum(d["figure_count"] for d in standard_docs)
    total_tables = sum(d["table_count"] for d in standard_docs)
    total_words = sum(d["word_count"] for d in standard_docs)
    
    print(f"\n{'='*80}")
    print(f"✅ Conversion complete!")
    print(f"{'='*80}")
    print(f"📄 Total pages: {len(standard_docs)}")
    print(f"📝 Total words: {total_words:,}")
    print(f"💻 Code snippets: {total_code}")
    print(f"🔢 Math formulas: {total_formulas}")
    print(f"📊 Figure captions: {total_figures}")
    print(f"📋 Table captions: {total_tables}")
    print(f"💾 Saved to: {output_file}")
    print(f"{'='*80}\n")
    
    # Display sample from first few pages
    print("📋 Sample from first 3 pages:")
    print("-" * 80)
    for doc in standard_docs[:3]:
        print(f"\n[Page {doc['page']}] {doc['section']}")
        print(f"Title: {doc['title']}")
        print(f"Words: {doc['word_count']} | Tables: {doc['table_count']} | Figures: {doc['figure_count']}")
        preview = doc['content'][:200].replace('\n', ' ')
        print(f"Preview: {preview}...")
        print("-" * 80)
    
    return output_file


if __name__ == "__main__":
    convert_docling_to_standard_format()