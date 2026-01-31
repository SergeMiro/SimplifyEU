"""
PDF Parser with OCR support for bank statements.
Uses PaddleOCR for OCR and pdf2image for PDF conversion.
"""
import io
import re
import logging
from datetime import datetime, date
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Check for OCR module (PaddleOCR-based)
try:
    from .ocr import get_ocr_engine, is_ocr_available, get_ocr_capabilities
    OCR_AVAILABLE = is_ocr_available()
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR module not available. PDF OCR will be unavailable.")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not installed. PDF processing will be unavailable.")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed. Text-based PDF extraction will be unavailable.")


from ..db.models import Transaction


class PDFParseError(Exception):
    """Custom exception for PDF parsing errors."""
    pass


class PDFParser:
    """
    Parser for PDF bank statements.
    Supports both text-based PDFs and scanned images (OCR).
    """
    
    # Common date patterns in bank statements
    DATE_PATTERNS = [
        r'(\d{2}[./]\d{2}[./]\d{4})',  # DD/MM/YYYY or DD.MM.YYYY
        r'(\d{4}[.-]\d{2}[.-]\d{2})',  # YYYY-MM-DD
        r'(\d{2}[.-]\d{2}[.-]\d{2})',  # DD-MM-YY
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # 1 Jan 2025
    ]
    
    # Amount patterns (supports EUR, USD, negative values)
    AMOUNT_PATTERNS = [
        r'[-−]?\s*€?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',  # €1,234.56 or 1.234,56
        r'[-−]?\s*(\d{1,3}(?:\s?\d{3})*[.,]\d{2})\s*€?',   # 1 234,56 €
        r'[-−]?\s*EUR\s*(\d+[.,]\d{2})',                    # EUR 123.45
    ]
    
    def __init__(self, ocr_lang: str = "en"):
        """
        Initialize PDF parser.
        
        Args:
            ocr_lang: PaddleOCR language code (en, fr, german, ru, etc.)
        """
        self.ocr_lang = ocr_lang
        self.ocr_available = OCR_AVAILABLE and PDF2IMAGE_AVAILABLE
        self.text_extraction_available = PDFPLUMBER_AVAILABLE
        
    def parse(self, pdf_content: bytes) -> list[Transaction]:
        """
        Parse PDF bank statement and extract transactions.
        
        Args:
            pdf_content: Raw PDF file bytes
            
        Returns:
            List of Transaction objects
        """
        text = self._extract_text(pdf_content)
        
        if not text or len(text.strip()) < 50:
            # If text extraction failed/empty, try OCR
            if self.ocr_available:
                logger.info("Text extraction yielded little content, trying OCR...")
                text = self._extract_text_ocr(pdf_content)
            else:
                raise PDFParseError(
                    "PDF appears to be scanned but OCR dependencies are not installed. "
                    "Please install: pip install paddleocr paddlepaddle pdf2image pillow"
                )
        
        if not text:
            raise PDFParseError("Could not extract any text from PDF")
        
        transactions = self._parse_transactions(text)
        
        if not transactions:
            logger.warning("No transactions found in PDF. Raw text sample: %s", text[:500])
            
        return transactions
    
    def _extract_text(self, pdf_content: bytes) -> str:
        """Extract text from text-based PDF using pdfplumber."""
        if not self.text_extraction_available:
            return ""
        
        try:
            import pdfplumber
            text_parts = []
            
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                text_parts.append(" | ".join(str(cell) for cell in row if cell))
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return ""
    
    def _extract_text_ocr(self, pdf_content: bytes, dpi: int = 200) -> str:
        """Extract text from scanned PDF using PaddleOCR."""
        if not self.ocr_available:
            raise PDFParseError("OCR dependencies not available")
        
        try:
            # Use PaddleOCR engine from ocr.py module
            ocr_engine = get_ocr_engine(lang=self.ocr_lang)
            text = ocr_engine.extract_text_from_pdf(pdf_content, dpi=dpi)
            return text
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise PDFParseError(f"OCR failed: {str(e)}")
    
    def _preprocess_image(self, image: 'Image.Image') -> 'Image.Image':
        """Preprocess image for better OCR results."""
        from PIL import ImageEnhance, ImageFilter
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Slight sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        return image
    
    def _parse_transactions(self, text: str) -> list[Transaction]:
        """Parse transaction data from extracted text."""
        transactions = []
        lines = text.split('\n')
        
        current_date = None
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Try to extract date
            date_match = None
            for pattern in self.DATE_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    date_match = match.group(1)
                    break
            
            if date_match:
                parsed_date = self._parse_date(date_match)
                if parsed_date:
                    current_date = parsed_date
            
            # Try to extract amount
            amount = None
            is_negative = '-' in line or '−' in line or line.strip().startswith('-')
            
            for pattern in self.AMOUNT_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    amount_str = match.group(1)
                    amount = self._parse_amount(amount_str)
                    if amount and is_negative and amount > 0:
                        amount = -amount
                    break
            
            # If we have both date and amount, create transaction
            if current_date and amount is not None:
                # Clean description (remove date and amount from line)
                description = line
                for pattern in self.DATE_PATTERNS + self.AMOUNT_PATTERNS:
                    description = re.sub(pattern, '', description)
                description = re.sub(r'\s+', ' ', description).strip()
                description = re.sub(r'^[-−€EUR\s]+', '', description).strip()
                
                if description and len(description) >= 3:
                    transactions.append(Transaction(
                        date=current_date,
                        description=description[:200],  # Limit length
                        amount=amount,
                        currency="EUR"
                    ))
        
        return transactions
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        date_formats = [
            '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d', '%d-%m-%y',
            '%d %b %Y', '%d %B %Y', '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        try:
            # Remove spaces
            amount_str = amount_str.replace(' ', '')
            
            # Handle European format (1.234,56) vs US format (1,234.56)
            if ',' in amount_str and '.' in amount_str:
                if amount_str.rfind(',') > amount_str.rfind('.'):
                    # European: 1.234,56
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                else:
                    # US: 1,234.56
                    amount_str = amount_str.replace(',', '')
            elif ',' in amount_str:
                # Could be European decimal separator
                if len(amount_str.split(',')[-1]) == 2:
                    amount_str = amount_str.replace(',', '.')
                else:
                    amount_str = amount_str.replace(',', '')
            
            return float(amount_str)
        except ValueError:
            return None
    
    def get_capabilities(self) -> dict:
        """Return information about available parsing capabilities."""
        ocr_caps = get_ocr_capabilities() if OCR_AVAILABLE else {}
        return {
            "text_extraction": self.text_extraction_available,
            "ocr_available": self.ocr_available,
            "ocr_engine": ocr_caps.get("engine"),
            "ocr_languages": self.ocr_lang if self.ocr_available else None,
            "dependencies": {
                "pdfplumber": PDFPLUMBER_AVAILABLE,
                "paddleocr": OCR_AVAILABLE,
                "pdf2image": PDF2IMAGE_AVAILABLE,
            }
        }


# Convenience function
def parse_pdf(pdf_content: bytes, ocr_lang: str = "en") -> list[Transaction]:
    """
    Parse PDF bank statement.
    
    Args:
        pdf_content: Raw PDF bytes
        ocr_lang: PaddleOCR language code (en, fr, german, ru, etc.)
        
    Returns:
        List of Transaction objects
    """
    parser = PDFParser(ocr_lang=ocr_lang)
    return parser.parse(pdf_content)


def is_pdf_supported() -> dict:
    """Check if PDF parsing is available."""
    parser = PDFParser()
    return parser.get_capabilities()
