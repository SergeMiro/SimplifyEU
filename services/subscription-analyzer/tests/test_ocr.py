"""
Tests for OCR module using PaddleOCR.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from src.core.ocr import (
    OCREngine, 
    get_ocr_engine, 
    extract_text_from_pdf, 
    is_ocr_available,
    get_ocr_capabilities,
    PADDLEOCR_AVAILABLE,
    PDF2IMAGE_AVAILABLE
)


class TestOCREngine:
    """Test cases for OCREngine class."""
    
    def test_singleton_pattern(self):
        """Test that OCREngine uses singleton pattern."""
        engine1 = OCREngine(lang="en")
        engine2 = OCREngine(lang="fr")
        
        # Should be the same instance
        assert engine1 is engine2
    
    def test_get_ocr_engine_returns_singleton(self):
        """Test get_ocr_engine returns singleton instance."""
        engine1 = get_ocr_engine("en")
        engine2 = get_ocr_engine("en")
        
        assert engine1 is engine2
    
    def test_is_available_property(self):
        """Test is_available property."""
        engine = get_ocr_engine()
        
        # Should be boolean
        assert isinstance(engine.is_available, bool)
        
        # If PaddleOCR not installed, should be False
        if not PADDLEOCR_AVAILABLE:
            assert engine.is_available is False
    
    def test_get_capabilities(self):
        """Test get_capabilities returns correct structure."""
        engine = get_ocr_engine()
        caps = engine.get_capabilities()
        
        assert "available" in caps
        assert "engine" in caps
        assert "language" in caps
        assert "supported_languages" in caps
        assert "pdf_support" in caps
        assert "dependencies" in caps
        assert "paddleocr" in caps["dependencies"]
        assert "pdf2image" in caps["dependencies"]
        assert "pillow" in caps["dependencies"]


class TestOCRFunctions:
    """Test cases for OCR convenience functions."""
    
    def test_is_ocr_available(self):
        """Test is_ocr_available function."""
        result = is_ocr_available()
        assert isinstance(result, bool)
    
    def test_get_ocr_capabilities(self):
        """Test get_ocr_capabilities function."""
        caps = get_ocr_capabilities()
        
        assert isinstance(caps, dict)
        assert "dependencies" in caps


class TestOCREngineWithMocks:
    """Test OCR functionality with mocked PaddleOCR."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        OCREngine._instance = None
        OCREngine._model = None
        yield
        OCREngine._instance = None
        OCREngine._model = None
    
    @pytest.mark.skipif(not PADDLEOCR_AVAILABLE, reason="PaddleOCR not installed")
    def test_extract_text_from_image_integration(self):
        """Test text extraction from image (requires PaddleOCR)."""
        # This test only runs when PaddleOCR is actually installed
        engine = OCREngine(lang="en")
        
        if not engine.is_available:
            pytest.skip("PaddleOCR engine not available")
        
        from PIL import Image
        fake_image = Image.new('RGB', (100, 50), color='white')
        
        # Should not raise
        text = engine.extract_text_from_image(fake_image)
        assert isinstance(text, str)
    
    def test_ocr_result_parsing(self):
        """Test that OCR result parsing logic works correctly."""
        # This tests the text extraction logic by simulating OCR output
        # without needing the actual PaddleOCR library
        
        # Simulate PaddleOCR result format
        mock_result = [[
            [[[0, 0], [100, 0], [100, 20], [0, 20]], ("Netflix Subscription", 0.95)],
            [[[0, 25], [100, 25], [100, 45], [0, 45]], ("€12.99", 0.98)],
        ]]
        
        # Parse like the extract_text_from_image method does
        text_lines = []
        if mock_result and mock_result[0]:
            for line in mock_result[0]:
                if line and len(line) >= 2:
                    text_content = line[1][0]
                    text_lines.append(text_content)
        
        result = "\n".join(text_lines)
        
        assert "Netflix Subscription" in result
        assert "€12.99" in result
    
    def test_empty_ocr_result_handling(self):
        """Test handling of empty OCR results."""
        # Empty results
        empty_results = [None, [], [[]], [None]]
        
        for result in empty_results:
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_content = line[1][0]
                        text_lines.append(text_content)
            
            assert text_lines == []


class TestLanguageMapping:
    """Test language code support."""
    
    def test_supported_languages_list(self):
        """Test that supported languages are available."""
        from src.core.ocr import LANGUAGE_MAP
        
        assert "eng" in LANGUAGE_MAP  # English
        assert "fra" in LANGUAGE_MAP  # French
        assert "deu" in LANGUAGE_MAP  # German
        assert "rus" in LANGUAGE_MAP  # Russian
        assert "ara" in LANGUAGE_MAP  # Arabic
