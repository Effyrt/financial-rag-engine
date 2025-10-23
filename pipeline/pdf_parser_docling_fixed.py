"""
Fixed Docling PDF Parser - Works with current Docling API.

Strategy: Extract specific pages first, then process with Docling.
"""

import logging
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from pypdf import PdfReader, PdfWriter
import tempfile
from docling.document_converter import DocumentConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DoclingPDFParserFixed:
    """
    Docling-based PDF parser that handles page ranges efficiently.
    
    Features:
    - Extracts specific page ranges
    - Uses Docling for deep content extraction
    - Extracts code, images, formulas, tables, text
    - Preserves reading order and captions
    """
    
    def __init__(self, start_page: int = 1, max_pages: int = 20):
        """
        Initialize parser.
        
        Args:
            start_page: Starting page number (1-indexed)
            max_pages: Number of pages to process
        """
        self.start_page = start_page
        self.max_pages = max_pages
        self.converter = DocumentConverter()
        logger.info(f"DoclingPDFParserFixed initialized (pages {start_page}-{start_page+max_pages-1})")
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse PDF with Docling.
        
        Returns structured data with all content types.
        """
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Parsing: {pdf_path}")
        logger.info(f"Extracting pages {self.start_page} to {self.start_page + self.max_pages - 1}")
        
        # Step 1: Extract specific pages to a temporary PDF
        temp_pdf = self._extract_pages(pdf_path)
        
        try:
            # Step 2: Process with Docling
            logger.info("Processing with Docling (this may take 30-60 seconds)...")
            result = self.converter.convert(str(temp_pdf))
            doc = result.document
            
            # Step 3: Export to markdown (Docling's structured format)
            markdown_text = doc.export_to_markdown()
            
            # Step 4: Parse the markdown to extract structure
            parsed_data = self._parse_markdown(markdown_text)
            
            # Step 5: Add metadata
            parsed_data['metadata'] = {
                'filename': pdf_file.name,
                'start_page': self.start_page,
                'pages_processed': self.max_pages,
                'timestamp': datetime.now().isoformat(),
                'parser': 'Docling',
                'total_chars': len(markdown_text)
            }
            
            # Save parsed data
            output_filename = f"docling_parsed_{self.start_page}_{self.start_page+self.max_pages-1}.json"
            output_path = Path("data/processed") / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Parsed {self.max_pages} pages with Docling")
            logger.info(f"   Topics: {len(parsed_data.get('topics', []))}")
            logger.info(f"   Code blocks: {len(parsed_data.get('code_blocks', []))}")
            logger.info(f"   Tables: {len(parsed_data.get('tables', []))}")
            logger.info(f"   Images: {len(parsed_data.get('images', []))}")
            logger.info(f"   Figures: {len(parsed_data.get('figures', []))}")
            logger.info(f"   Formulas: {len(parsed_data.get('formulas', []))}")
            logger.info(f"Saved to: {output_path}")
            
            return parsed_data
            
        finally:
            # Clean up temp file
            if temp_pdf.exists():
                temp_pdf.unlink()
    
    def _extract_pages(self, pdf_path: str) -> Path:
        """
        Extract specific pages to a temporary PDF.
        """
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        total_pages = len(reader.pages)
        end_page = min(self.start_page + self.max_pages - 1, total_pages)
        
        logger.info(f"Extracting pages {self.start_page}-{end_page} from {total_pages} total pages")
        
        # Extract pages (convert to 0-indexed)
        for page_num in range(self.start_page - 1, end_page):
            if page_num < total_pages:
                writer.add_page(reader.pages[page_num])
        
        # Write to temp file
        temp_file = Path(tempfile.gettempdir()) / f"temp_pages_{self.start_page}_{end_page}.pdf"
        with open(temp_file, 'wb') as f:
            writer.write(f)
        
        logger.info(f"Created temporary PDF: {temp_file}")
        return temp_file
    
    def _parse_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        Parse Docling's markdown output to extract structured content.
        """
        lines = markdown_text.split('\n')
        
        topics = []
        code_blocks = []
        tables = []
        formulas = []
        images = []
        figures = []
        current_topic = None
        in_code_block = False
        in_table = False
        code_buffer = []
        table_buffer = []
        
        for i, line in enumerate(lines):
            # Detect headings (topics)
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                
                if level <= 2 and len(title) > 3:  # Main topics
                    topics.append({
                        'level': level,
                        'title': title,
                        'line': i
                    })
                    current_topic = title
            
            # Detect code blocks
            elif line.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    language = line[3:].strip() or 'unknown'
                    code_buffer = [language]
                else:
                    in_code_block = False
                    code_blocks.append({
                        'language': code_buffer[0],
                        'content': '\n'.join(code_buffer[1:]),
                        'line': i,
                        'topic': current_topic
                    })
                    code_buffer = []
            elif in_code_block:
                code_buffer.append(line)
            
            # Detect tables (markdown tables with |)
            elif '|' in line and not in_code_block:
                if not in_table:
                    in_table = True
                    table_buffer = [line]
                else:
                    table_buffer.append(line)
            elif in_table and not line.strip():
                in_table = False
                tables.append({
                    'content': '\n'.join(table_buffer),
                    'line': i,
                    'topic': current_topic
                })
                table_buffer = []
            elif in_table:
                table_buffer.append(line)
            
            # Detect formulas (LaTeX style: $...$ or $$...$$)
            elif '$' in line:
                formulas.append({
                    'content': line,
                    'line': i,
                    'topic': current_topic
                })
            
            # Detect images and figures (markdown syntax: ![...](...))
            elif line.strip().startswith('!['):
                # Extract image alt text and path
                img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line.strip())
                if img_match:
                    alt_text = img_match.group(1)
                    img_path = img_match.group(2)
                    images.append({
                        'alt_text': alt_text,
                        'path': img_path,
                        'line': i,
                        'topic': current_topic,
                        'full_line': line.strip()
                    })
            
            # Detect figure captions or references
            elif any(keyword in line.lower() for keyword in ['figure ', 'fig.', 'image ', 'graph ', 'chart ', 'diagram ']):
                # Look for figure references
                if re.search(r'figure\s+\d+', line.lower()) or re.search(r'fig\.\s*\d+', line.lower()):
                    figures.append({
                        'content': line.strip(),
                        'line': i,
                        'topic': current_topic,
                        'type': 'figure_reference'
                    })
        
        # Create topics for namespacing
        namespace_topics = []
        for i, topic in enumerate(topics):
            if topic['level'] <= 2:  # Only main topics
                namespace = self._create_namespace(topic['title'])
                namespace_topics.append({
                    'topic': namespace,
                    'title': topic['title'],
                    'level': topic['level'],
                    'start_line': topic['line']
                })
        
        return {
            'full_text': markdown_text,
            'topics': namespace_topics,
            'code_blocks': code_blocks,
            'tables': tables,
            'formulas': formulas,
            'images': images,
            'figures': figures,
            'total_lines': len(lines)
        }
    
    def _create_namespace(self, title: str) -> str:
        """Create namespace-friendly name from title."""
        import re
        # Remove special characters, lowercase, replace spaces with hyphens
        namespace = re.sub(r'[^\w\s-]', '', title.lower())
        namespace = re.sub(r'[-\s]+', '-', namespace)
        return namespace[:50]  # Limit length


if __name__ == "__main__":
    # Test the parser
    parser = DoclingPDFParserFixed(start_page=30, max_pages=20)
    
    pdf_path = "fintbx.pdf"
    if Path(pdf_path).exists():
        parsed_data = parser.parse_pdf(pdf_path)
        print("\n✅ Parsing complete!")
        print(f"   Topics: {len(parsed_data.get('topics', []))}")
        print(f"   Code blocks: {len(parsed_data.get('code_blocks', []))}")
        print(f"   Tables: {len(parsed_data.get('tables', []))}")
        print(f"   Formulas: {len(parsed_data.get('formulas', []))}")
    else:
        print(f"❌ PDF not found: {pdf_path}")

