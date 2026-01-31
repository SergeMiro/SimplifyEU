"""
OCR Engine using PaddleOCR for text extraction from images and PDFs.
Supports 109 languages including English, French, German, Russian, Arabic, and more.
"""
import io
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Check for PaddleOCR availability
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not installed. PDF OCR will be unavailable.")

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow not installed. Image processing will be unavailable.")


# Language code mapping: PaddleOCR uses different codes
LANGUAGE_MAP = {
    "eng": "en",
    "fra": "fr", 
    "deu": "german",
    "rus": "ru",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "ara": "ar",
    "chi_sim": "ch",
    "chi_tra": "chinese_cht",
    "jpn": "japan",
    "kor": "korean",
}


class OCREngine:
    """
    OCR Engine using PaddleOCR.
    
    Uses singleton pattern to avoid reloading the model multiple times.
    Model is loaded lazily on first use (~100MB download).
    """
    
    _instance: Optional['OCREngine'] = None
    _model: Optional['PaddleOCR'] = None
    
    def __new__(cls, lang: str = "en"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, lang: str = "en"):
        if self._initialized:
            return
            
        self.lang = lang
        self._initialized = True
        
        if not PADDLEOCR_AVAILABLE:
            logger.error("PaddleOCR not available. OCR will not work.")
            return
            
        logger.info(f"Initializing PaddleOCR with language: {lang}")
        
        try:
            # Initialize PaddleOCR with specified language
            # use_textline_orientation: detect rotated text
            # show_log: disable verbose logging
            self._model = PaddleOCR(
                use_textline_orientation=True,
                lang=lang,
                show_log=False,
                use_gpu=False,  # CPU for compatibility, set True for GPU
            )
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            self._model = None
    
    @property
    def is_available(self) -> bool:
        """Check if OCR engine is available."""
        return PADDLEOCR_AVAILABLE and self._model is not None
    
    def extract_text_from_image(self, image: 'Image.Image') -> str:
        """
        Extract text from a PIL Image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text as string
        """
        if not self.is_available:
            raise RuntimeError("PaddleOCR not available")
        
        # Convert PIL Image to numpy array for PaddleOCR
        import numpy as np
        img_array = np.array(image)
        
        # Run OCR
        result = self._model.ocr(img_array, cls=True)
        
        # Extract text from result
        # PaddleOCR returns: [[[box, (text, confidence)], ...], ...]
        text_lines = []
        
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text_content = line[1][0]  # (text, confidence)
                    text_lines.append(text_content)
        
        return "\n".join(text_lines)
    
    def extract_text_from_pdf(
        self, 
        pdf_content: bytes, 
        dpi: int = 200,
        max_pages: Optional[int] = None
    ) -> str:
        """
        Extract text from a PDF file using OCR.
        
        Args:
            pdf_content: Raw PDF bytes
            dpi: Resolution for PDF to image conversion (lower = faster)
            max_pages: Maximum pages to process (None = all)
            
        Returns:
            Extracted text from all pages
        """
        if not self.is_available:
            raise RuntimeError("PaddleOCR not available")
            
        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("pdf2image not available. Install with: pip install pdf2image")
        
        # Convert PDF pages to images
        logger.info("Converting PDF to images...")
        images = convert_from_bytes(pdf_content, dpi=dpi)
        
        if max_pages:
            images = images[:max_pages]
        
        text_parts = []
        total_pages = len(images)
        
        for i, image in enumerate(images):
            logger.info(f"Processing page {i + 1}/{total_pages} with PaddleOCR...")
            
            try:
                page_text = self.extract_text_from_image(image)
                if page_text:
                    text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
            except Exception as e:
                logger.warning(f"Failed to OCR page {i + 1}: {e}")
                continue
        
        return "\n\n".join(text_parts)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return information about OCR capabilities."""
        return {
            "engine": "PaddleOCR" if self.is_available else None,
            "available": self.is_available,
            "language": self.lang if self.is_available else None,
            "supported_languages": list(LANGUAGE_MAP.values()) if self.is_available else [],
            "pdf_support": PDF2IMAGE_AVAILABLE,
            "dependencies": {
                "paddleocr": PADDLEOCR_AVAILABLE,
                "pdf2image": PDF2IMAGE_AVAILABLE,
                "pillow": PILLOW_AVAILABLE,
            }
        }


# Convenience functions
def get_ocr_engine(lang: str = "en") -> OCREngine:
    """Get or create the OCR engine singleton."""
    return OCREngine(lang=lang)


def extract_text_from_pdf(pdf_content: bytes, lang: str = "en", dpi: int = 200) -> str:
    """
    Convenience function to extract text from PDF.
    
    Args:
        pdf_content: Raw PDF bytes
        lang: OCR language code (en, fr, german, ru, etc.)
        dpi: Image resolution (200 = good balance of speed/quality)
        
    Returns:
        Extracted text
    """
    engine = get_ocr_engine(lang)
    return engine.extract_text_from_pdf(pdf_content, dpi=dpi)


def is_ocr_available() -> bool:
    """Check if OCR is available."""
    return PADDLEOCR_AVAILABLE and PDF2IMAGE_AVAILABLE


def get_ocr_capabilities() -> Dict[str, Any]:
    """Get OCR capabilities info."""
    if not PADDLEOCR_AVAILABLE:
        return {
            "engine": None,
            "available": False,
            "pdf_support": PDF2IMAGE_AVAILABLE,
            "dependencies": {
                "paddleocr": False,
                "pdf2image": PDF2IMAGE_AVAILABLE,
                "pillow": PILLOW_AVAILABLE,
            }
        }
    
    engine = get_ocr_engine()
    return engine.get_capabilities()
