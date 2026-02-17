"""
PDF text extraction using pdfplumber (primary) and PyPDF2 (fallback).
"""
import logging
import hashlib
from pathlib import Path
from typing import Optional

import pdfplumber
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extract text from a PDF file.
    Uses pdfplumber first (better layout handling), falls back to PyPDF2.
    Returns None if both fail.
    """
    text = _extract_with_pdfplumber(file_path)
    if text and text.strip():
        return text.strip()

    logger.info(f"pdfplumber returned no text, trying PyPDF2: {file_path}")
    text = _extract_with_pypdf2(file_path)
    if text and text.strip():
        return text.strip()

    logger.warning(f"No text extracted from PDF by either method: {file_path}")
    return None


def _extract_with_pdfplumber(file_path: str) -> Optional[str]:
    """Extract text using pdfplumber."""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return None


def _extract_with_pypdf2(file_path: str) -> Optional[str]:
    """Extract text using PyPDF2."""
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file for dedup by exact content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def validate_file_magic(file_path: str) -> bool:
    """
    Validate file by checking magic bytes.
    Supports PDF (%PDF) and common image formats (JPEG, PNG, TIFF).
    """
    MAGIC_BYTES = {
        b"%PDF": "pdf",
        b"\xff\xd8\xff": "jpeg",
        b"\x89PNG": "png",
        b"II\x2a\x00": "tiff_le",
        b"MM\x00\x2a": "tiff_be",
    }

    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        for magic, fmt in MAGIC_BYTES.items():
            if header.startswith(magic):
                logger.debug(f"Valid magic bytes: {fmt}")
                return True
        logger.warning(f"Invalid magic bytes in file: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Failed to read file header: {e}")
        return False
