"""
OCR processor for image-based invoices and scanned PDFs.
Uses pytesseract with retry logic and exponential backoff.
"""
import logging
import time
from typing import Optional
from pathlib import Path

from PIL import Image

from ..config import settings

logger = logging.getLogger(__name__)


def ocr_image(file_path: str, language: Optional[str] = None) -> Optional[str]:
    """
    Run OCR on an image file with retry logic.
    Returns extracted text or None on failure.
    """
    if not settings.OCR_ENABLED:
        logger.info("OCR is disabled via configuration")
        return None

    lang = language or settings.OCR_LANGUAGE
    last_error = None

    for attempt in range(1, settings.OCR_RETRY_MAX + 1):
        try:
            import pytesseract

            image = Image.open(file_path)

            # Convert to RGB if necessary (e.g., RGBA PNGs)
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")

            text = pytesseract.image_to_string(image, lang=lang)

            if text and text.strip():
                logger.info(f"OCR successful on attempt {attempt}: {len(text)} chars")
                return text.strip()
            else:
                logger.warning(f"OCR attempt {attempt}: no text extracted")
                return None

        except ImportError:
            logger.error("pytesseract is not installed. OCR unavailable.")
            return None
        except Exception as e:
            last_error = e
            wait = settings.OCR_RETRY_BACKOFF_BASE ** attempt
            logger.warning(f"OCR attempt {attempt} failed: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)

    logger.error(f"OCR failed after {settings.OCR_RETRY_MAX} attempts: {last_error}")
    return None


def ocr_pdf_pages(file_path: str, language: Optional[str] = None) -> Optional[str]:
    """
    Convert each page of a PDF to image and run OCR.
    Useful for scanned PDFs that contain no extractable text.
    """
    try:
        # Try pdf2image if available
        from pdf2image import convert_from_path

        images = convert_from_path(file_path, dpi=300)
        text_parts = []

        for i, image in enumerate(images):
            temp_path = f"/tmp/ocr_page_{i}.png"
            image.save(temp_path, "PNG")

            page_text = ocr_image(temp_path, language)
            if page_text:
                text_parts.append(page_text)

            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

        return "\n".join(text_parts) if text_parts else None

    except ImportError:
        logger.warning("pdf2image not installed. Cannot OCR PDF pages.")
        return None
    except Exception as e:
        logger.error(f"PDF OCR failed: {e}")
        return None
