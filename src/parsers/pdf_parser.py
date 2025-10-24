"""
Enterprise-grade PDF parser for financial documents.
Extracts text, tables, formulas, and images with citation metadata.
"""

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
import re
from pathlib import Path
import io


@dataclass
class ParsedElement:
    """Structured representation of a parsed PDF element."""
    content: str
    element_type: str  # 'text', 'table', 'formula', 'code', 'image'
    page_number: int
    section_title: Optional[str] = None
    subsection_title: Optional[str] = None
    bounding_box: Optional[tuple] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class ParsedDocument:
    """Complete parsed PDF document."""
    elements: List[ParsedElement]
    total_pages: int
    document_metadata: Dict[str, Any]
    section_hierarchy: Dict[str, List[str]]


class FinancialPDFParser:
    """
    Production-grade PDF parser optimized for financial documents.
    
    Features:
    - Multi-strategy parsing (PyMuPDF + pdfplumber)
    - Table extraction with structure preservation
    - Formula and equation detection
    - Code block identification
    - Image extraction with OCR fallback
    - Section hierarchy tracking
    - Citation metadata preservation
    """
    
    def __init__(self, 
                 extract_images: bool = True,
                 extract_tables: bool = True,
                 ocr_enabled: bool = True):
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.ocr_enabled = ocr_enabled
        self.section_pattern = re.compile(r'^(\d+\.)*\d+\s+[A-Z]')
        self.formula_pattern = re.compile(r'[∫∑∏√±×÷≤≥≠∂∆∇∈∉⊂⊃∪∩]|\\[a-z]+\{')
        
    def parse(self, pdf_path: str) -> ParsedDocument:
        """
        Parse PDF and extract all elements with metadata.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParsedDocument with all extracted elements
        """
        logger.info(f"Starting PDF parsing: {pdf_path}")
        
        elements = []
        section_hierarchy = {}
        current_section = None
        current_subsection = None
        
        # Open with PyMuPDF for primary extraction
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # Open with pdfplumber for table extraction
        with pdfplumber.open(pdf_path) as pdf_plumber:
            
            for page_num in range(total_pages):
                logger.debug(f"Processing page {page_num + 1}/{total_pages}")
                
                # Get pages from both libraries
                fitz_page = doc[page_num]
                plumber_page = pdf_plumber.pages[page_num]
                
                # Extract text blocks with position info
                text_blocks = fitz_page.get_text("blocks")
                
                for block in text_blocks:
                    x0, y0, x1, y1, text, block_num, block_type = block
                    
                    if not text.strip():
                        continue
                        
                    # Detect element type
                    element_type = self._classify_element(text)
                    
                    # Update section tracking
                    if self._is_section_header(text):
                        current_section = text.strip()
                        section_hierarchy[current_section] = []
                    elif self._is_subsection_header(text):
                        current_subsection = text.strip()
                        if current_section:
                            section_hierarchy[current_section].append(current_subsection)
                    
                    # Create parsed element
                    element = ParsedElement(
                        content=text.strip(),
                        element_type=element_type,
                        page_number=page_num + 1,
                        section_title=current_section,
                        subsection_title=current_subsection,
                        bounding_box=(x0, y0, x1, y1),
                        metadata={
                            'block_number': block_num,
                            'block_type': block_type
                        }
                    )
                    elements.append(element)
                
                # Extract tables
                if self.extract_tables:
                    tables = self._extract_tables(plumber_page, page_num + 1,
                                                  current_section, current_subsection)
                    elements.extend(tables)
                
                # Extract images
                if self.extract_images:
                    images = self._extract_images(fitz_page, page_num + 1,
                                                  current_section, current_subsection)
                    elements.extend(images)
        
        doc.close()
        
        # Create document metadata
        document_metadata = {
            'file_path': pdf_path,
            'total_pages': total_pages,
            'total_elements': len(elements),
            'sections_count': len(section_hierarchy)
        }
        
        logger.info(f"Parsing complete. Extracted {len(elements)} elements from {total_pages} pages")
        
        return ParsedDocument(
            elements=elements,
            total_pages=total_pages,
            document_metadata=document_metadata,
            section_hierarchy=section_hierarchy
        )
    
    def _classify_element(self, text: str) -> str:
        """Classify element type based on content patterns."""
        text_lower = text.lower()
        
        # Check for code blocks (MATLAB, Python, etc.)
        if any(keyword in text_lower for keyword in ['function', 'return', 'import', 'class', '=']):
            if re.search(r'[(){}\[\];]', text):
                return 'code'
        
        # Check for formulas
        if self.formula_pattern.search(text) or '$$' in text or '$' in text:
            return 'formula'
        
        # Check for tables (basic heuristic)
        if text.count('\t') > 3 or text.count('|') > 2:
            return 'table'
        
        return 'text'
    
    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header."""
        text = text.strip()
        # Match patterns like "1.2 Section Name" or "Chapter 3"
        return bool(self.section_pattern.match(text)) or \
               (text.isupper() and len(text.split()) <= 5)
    
    def _is_subsection_header(self, text: str) -> bool:
        """Detect if text is a subsection header."""
        text = text.strip()
        # Match numbered subsections
        return bool(re.match(r'^(\d+\.){2,}\d+\s+\w', text))
    
    def _extract_tables(self, page, page_num: int,
                       section: Optional[str], subsection: Optional[str]) -> List[ParsedElement]:
        """Extract tables from pdfplumber page."""
        tables = []
        extracted_tables = page.extract_tables()
        
        for idx, table in enumerate(extracted_tables):
            if not table:
                continue
                
            # Convert table to formatted string
            table_str = self._format_table(table)
            
            element = ParsedElement(
                content=table_str,
                element_type='table',
                page_number=page_num,
                section_title=section,
                subsection_title=subsection,
                metadata={
                    'table_index': idx,
                    'rows': len(table),
                    'columns': len(table[0]) if table else 0
                }
            )
            tables.append(element)
        
        return tables
    
    def _format_table(self, table: List[List[str]]) -> str:
        """Format table as markdown-style string."""
        if not table:
            return ""
        
        # Create markdown table
        lines = []
        for row in table:
            row_str = " | ".join(str(cell) if cell else "" for cell in row)
            lines.append(f"| {row_str} |")
            
            # Add separator after header
            if len(lines) == 1:
                separator = " | ".join(["---"] * len(row))
                lines.append(f"| {separator} |")
        
        return "\n".join(lines)
    
    def _extract_images(self, page, page_num: int,
                       section: Optional[str], subsection: Optional[str]) -> List[ParsedElement]:
        """Extract images and apply OCR if enabled."""
        images = []
        image_list = page.get_images()
        
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            
            try:
                # Extract image
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Apply OCR if enabled
                text_content = ""
                if self.ocr_enabled:
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    text_content = pytesseract.image_to_string(pil_image)
                
                # Create element for image
                element = ParsedElement(
                    content=text_content if text_content else "[Image]",
                    element_type='image',
                    page_number=page_num,
                    section_title=section,
                    subsection_title=subsection,
                    metadata={
                        'image_index': img_idx,
                        'image_format': base_image["ext"],
                        'has_ocr_text': bool(text_content),
                        'xref': xref
                    }
                )
                images.append(element)
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_idx} on page {page_num}: {e}")
        
        return images
    
    def save_elements_to_json(self, parsed_doc: ParsedDocument, output_path: str):
        """Save parsed elements to JSON for further processing."""
        import json
        from dataclasses import asdict
        
        output = {
            'document_metadata': parsed_doc.document_metadata,
            'section_hierarchy': parsed_doc.section_hierarchy,
            'elements': [asdict(elem) for elem in parsed_doc.elements]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved parsed elements to {output_path}")


# Example usage
if __name__ == "__main__":
    parser = FinancialPDFParser(
        extract_images=True,
        extract_tables=True,
        ocr_enabled=True
    )
    
    parsed_doc = parser.parse("data/raw/fintbx.pdf")
    parser.save_elements_to_json(parsed_doc, "data/processed/parsed_elements.json")