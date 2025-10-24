from pathlib import Path
import json
import sys
import traceback

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
    print("✅ Docling library loaded successfully")
except ImportError as e:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
    print(f"⚠️ Docling not installed: {e}")

try:
    from google.cloud import documentai_v1 as documentai
    DOCAI_AVAILABLE = True
    print("✅ Google Document AI library loaded successfully")
except ImportError as e:
    DOCAI_AVAILABLE = False
    print(f"⚠️ Google Document AI not installed: {e}")

# Import DocAI parser
try:
    from docai_parser import DocAIOCRParser
    DOCAI_PARSER_AVAILABLE = True
except ImportError:
    DOCAI_PARSER_AVAILABLE = False
    print("⚠️ Custom DocAI parser not found (docai_parser.py)")


class DoclingOrFallbackParser:
    """
    Parser that tries Docling first.
    If Docling fails or returns empty results, it falls back to Google Document AI OCR.
    If both fail, saves a fallback JSON with error information.
    """
    
    def __init__(self,
                 output_dir: str = "data/parsed/docling_or_fallback",
                 project_id: str = None,
                 location: str = "us",
                 processor_id: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize only if Docling is available
        if DOCLING_AVAILABLE:
            try:
                self.converter = DocumentConverter()
                print("✅ Docling DocumentConverter initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize Docling: {e}")
                self.converter = None
        else:
            self.converter = None
            print("⚠️ Docling unavailable, will skip to fallback")
        
        # Google Document AI configuration
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        
        print(f"\n{'='*60}")
        print("Parser Configuration:")
        print(f"  Docling Available: {DOCLING_AVAILABLE}")
        print(f"  Google DocAI Available: {DOCAI_AVAILABLE}")
        print(f"  Custom DocAI Parser: {DOCAI_PARSER_AVAILABLE}")
        print(f"  Output Directory: {self.output_dir}")
        if self.project_id:
            print(f"  GCP Project: {self.project_id}")
            print(f"  Processor ID: {self.processor_id}")
        print(f"{'='*60}\n")

    def parse_pdf(self, pdf_path: str, page_num: int = None):
        """
        Parse PDF using available methods in priority order:
        1. Docling
        2. Google Document AI OCR
        3. Fallback (save error info)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"❌ File not found: {pdf_path}")
            return None

        print(f"\n{'='*60}")
        print(f"🚀 Parsing: {pdf_path.name}")
        print(f"{'='*60}")

        # ==================== Step 1: Try Docling ====================
        if DOCLING_AVAILABLE and self.converter:
            try:
                print("🔄 [Method 1] Attempting Docling parser...")
                result = self.converter.convert(str(pdf_path))
                doc_dict = result.document.export_to_dict()

                # Check if there is content
                if not doc_dict.get("pages"):
                    raise ValueError("Docling returned no pages")

                # Save Docling result
                out_file = self.output_dir / f"{pdf_path.stem}_docling.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc_dict, f, indent=2, ensure_ascii=False)

                print(f"✅ [Docling Success] Saved to {out_file}")
                print(f"   Pages parsed: {len(doc_dict.get('pages', []))}")
                return out_file

            except Exception as e:
                print(f"⚠️ [Docling Failed] {str(e)[:100]}")
                print(f"   Switching to fallback method...")
        else:
            print("⏭️  [Method 1] Docling not available, skipping")

        # ==================== Step 2: Try Google Document AI ====================
        if (DOCAI_AVAILABLE or DOCAI_PARSER_AVAILABLE) and self.project_id and self.processor_id:
            try:
                print("🔄 [Method 2] Attempting Google Document AI OCR...")
                
                if DOCAI_PARSER_AVAILABLE:
                    # Use DocAI parser
                    docai_parser = DocAIOCRParser(
                        self.project_id,
                        self.location,
                        self.processor_id
                    )
                    
                    if page_num:
                        result = docai_parser.parse_pdf_page(pdf_path, page_num=page_num)
                    else:
                        result = docai_parser.parse_pdf(pdf_path)
                    
                    print(f"✅ [Google DocAI Success] Result: {result}")
                    return result
                else:
                    print("⚠️ Custom DocAI parser not available")
                    raise ImportError("DocAIOCRParser not found")
                
            except Exception as e2:
                print(f"⚠️ [Google DocAI Failed] {str(e2)[:100]}")
                print(f"   Falling back to basic save...")
        else:
            if not self.project_id or not self.processor_id:
                print("⏭️  [Method 2] Google Document AI not configured, skipping")
            else:
                print("⏭️  [Method 2] Google Document AI libraries not available, skipping")

        # ==================== Step 3: Ultimate Fallback ====================
        print("⚠️ [Method 3] All parsers failed, saving fallback info...")
        
        fallback_data = {
            "source": pdf_path.name,
            "parser": "fallback",
            "timestamp": str(Path(pdf_path).stat().st_mtime),
            "file_size_bytes": pdf_path.stat().st_size,
            "status": "parsing_failed",
            "errors": {
                "docling_available": DOCLING_AVAILABLE,
                "docai_available": DOCAI_AVAILABLE,
                "docai_configured": bool(self.project_id and self.processor_id)
            },
            "message": "Unable to parse PDF with available methods"
        }
        
        out_file = self.output_dir / f"{pdf_path.stem}_fallback.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(fallback_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 [Fallback] Saved error info to {out_file}")
        return out_file


# ==================== Main Execution ====================
if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("📄 PDF Parser Starting")
        print("="*60)
        
        # Initialize parser (without Google DocAI for now)
        parser = DoclingOrFallbackParser(
            output_dir="data/parsed"
            # Skip Google DocAI configuration, use Docling only
        )

        # Specify PDF to parse
        pdf_path = Path("data/raw/fintbx.pdf")
        
        if not pdf_path.exists():
            print(f"❌ File not found: {pdf_path}")
            print(f"   Please ensure fintbx.pdf is in the data/raw/ folder")
            sys.exit(1)
        
        print(f"\n📁 Found PDF: {pdf_path}")
        print(f"📦 File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Parse PDF
        print(f"\n🚀 Starting parse...")
        result = parser.parse_pdf(pdf_path)
        
        if result:
            print(f"\n{'='*60}")
            print(f"✅ Parsing successful!")
            print(f"{'='*60}")
            print(f"📄 Output file: {result}")
            print(f"\nNext step: Run convert_docling_to_chunks.py to process this file")
        else:
            print(f"\n❌ Parsing failed")
            
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)