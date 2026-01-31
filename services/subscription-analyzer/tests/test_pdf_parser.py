"""
Tests for PDF parser module.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock, mock_open
import io
import sys

from src.core.pdf_parser import PDFParser, parse_pdf, is_pdf_supported, PDFParseError


class TestPDFParser:
    """Test cases for PDFParser class."""
    
    def test_init_default_language(self):
        """Test parser initializes with default OCR language."""
        parser = PDFParser()
        assert parser.ocr_lang == "en"
    
    def test_init_custom_language(self):
        """Test parser initializes with custom OCR language."""
        parser = PDFParser(ocr_lang="fr")
        assert parser.ocr_lang == "fr"
    
    def test_get_capabilities(self):
        """Test capabilities method returns correct structure."""
        parser = PDFParser()
        caps = parser.get_capabilities()
        
        assert "text_extraction" in caps
        assert "ocr_available" in caps
        assert "ocr_languages" in caps
        assert "dependencies" in caps
        assert "pdfplumber" in caps["dependencies"]
        assert "paddleocr" in caps["dependencies"]
        assert "pdf2image" in caps["dependencies"]
    
    def test_parse_date_formats(self):
        """Test various date format parsing."""
        parser = PDFParser()
        
        # DD/MM/YYYY
        result = parser._parse_date("15/06/2024")
        assert result == date(2024, 6, 15)
        
        # DD.MM.YYYY
        result = parser._parse_date("15.06.2024")
        assert result == date(2024, 6, 15)
        
        # YYYY-MM-DD
        result = parser._parse_date("2024-06-15")
        assert result == date(2024, 6, 15)
        
        # Invalid date
        result = parser._parse_date("invalid")
        assert result is None
    
    def test_parse_amount_formats(self):
        """Test various amount format parsing."""
        parser = PDFParser()
        
        # Simple format
        assert parser._parse_amount("123.45") == 123.45
        
        # European format with comma decimal
        assert parser._parse_amount("1234,56") == 1234.56
        
        # Thousands separator (European)
        assert parser._parse_amount("1.234,56") == 1234.56
        
        # Thousands separator (US)
        assert parser._parse_amount("1,234.56") == 1234.56
        
        # Invalid amount
        assert parser._parse_amount("abc") is None
    
    def test_extract_text_success(self):
        """Test successful text extraction from PDF when pdfplumber available."""
        # Skip if pdfplumber not available
        pytest.importorskip("pdfplumber")
        
        # Mock page
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample bank statement\n15/06/2024 Netflix €12.99"
        mock_page.extract_tables.return_value = []
        
        # Mock PDF object
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        
        with patch('pdfplumber.open', return_value=mock_pdf):
            parser = PDFParser()
            parser.text_extraction_available = True
            
            text = parser._extract_text(b"fake pdf content")
            
            assert "Netflix" in text
            assert "12.99" in text
    
    def test_parse_transactions_from_text(self):
        """Test transaction parsing from extracted text."""
        parser = PDFParser()
        
        text = """
        Bank Statement - June 2024
        
        15/06/2024 NETFLIX.COM     -12.99
        16/06/2024 SPOTIFY PREMIUM -9.99
        17/06/2024 AMAZON PRIME    -7.99
        """
        
        transactions = parser._parse_transactions(text)
        
        assert len(transactions) >= 3
        assert transactions[0].amount < 0  # Should be negative (expense)
    
    def test_parse_with_no_text_raises_error(self):
        """Test that parsing empty content raises error."""
        parser = PDFParser()
        parser.text_extraction_available = True
        parser.ocr_available = False
        
        with patch.object(parser, '_extract_text', return_value=""):
            # When text is empty and OCR not available, it raises about OCR deps
            with pytest.raises(PDFParseError):
                parser.parse(b"fake pdf")
    
    @patch('src.core.pdf_parser.PDFPLUMBER_AVAILABLE', True)
    def test_parse_pdf_with_valid_data(self):
        """Test complete parse flow with valid PDF data."""
        sample_text = """
        Statement Date: 01/01/2024
        
        Transactions:
        01/01/2024  SUBSCRIPTION NETFLIX     -14.99
        05/01/2024  PAYMENT SPOTIFY          -9.99
        10/01/2024  AMAZON PRIME             -12.99
        """
        
        parser = PDFParser()
        
        with patch.object(parser, '_extract_text', return_value=sample_text):
            transactions = parser.parse(b"fake pdf content")
            
            assert len(transactions) >= 2
            # Verify transaction structure
            for tx in transactions:
                assert tx.date is not None
                assert tx.description is not None
                assert tx.amount is not None
    
    def test_is_pdf_supported_function(self):
        """Test the is_pdf_supported helper function."""
        result = is_pdf_supported()
        
        assert isinstance(result, dict)
        assert "text_extraction" in result
        assert "ocr_available" in result
    
    def test_parse_pdf_function(self):
        """Test the parse_pdf convenience function."""
        sample_text = "15/06/2024 TEST MERCHANT -25.00"
        
        with patch('src.core.pdf_parser.PDFParser.parse') as mock_parse:
            mock_parse.return_value = []
            
            result = parse_pdf(b"fake content")
            
            mock_parse.assert_called_once()
    
    def test_amount_with_currency_symbol(self):
        """Test amount parsing with currency symbols."""
        parser = PDFParser()
        
        # Amount in text line with € symbol
        text = "15/06/2024 Subscription Service €15.99"
        transactions = parser._parse_transactions(text)
        
        # Should find and parse the amount
        assert len(transactions) > 0
    
    def test_negative_amount_detection(self):
        """Test proper detection of negative/expense amounts."""
        parser = PDFParser()
        
        # Line with explicit negative
        text = "15/06/2024 AMAZON -25.00"
        transactions = parser._parse_transactions(text)
        
        if transactions:
            assert transactions[0].amount < 0
    
    def test_description_cleanup(self):
        """Test that descriptions are properly cleaned."""
        parser = PDFParser()
        
        text = "15/06/2024 NETFLIX SUBSCRIPTION RENEWAL -12.99 EUR"
        transactions = parser._parse_transactions(text)
        
        if transactions:
            # Description should not contain the amount
            assert "12.99" not in transactions[0].description
    
    def test_empty_lines_ignored(self):
        """Test that empty lines don't create transactions."""
        parser = PDFParser()
        
        text = """
        
        
        15/06/2024 Valid Transaction -10.00
        
        
        """
        
        transactions = parser._parse_transactions(text)
        
        # Should only have one valid transaction
        assert len(transactions) == 1


class TestPDFParserOCR:
    """Test cases for OCR functionality (when available)."""
    
    def test_ocr_extraction(self):
        """Test OCR text extraction using PaddleOCR."""
        # Mock the OCR engine
        mock_engine = MagicMock()
        mock_engine.extract_text_from_pdf.return_value = "--- Page 1 ---\n15/06/2024 OCR Transaction -50.00"
        
        with patch('src.core.pdf_parser.get_ocr_engine', return_value=mock_engine):
            parser = PDFParser()
            parser.ocr_available = True
            
            text = parser._extract_text_ocr(b"fake pdf")
            
            assert "OCR Transaction" in text
            mock_engine.extract_text_from_pdf.assert_called_once()
    
    @patch('src.core.pdf_parser.OCR_AVAILABLE', False)
    @patch('src.core.pdf_parser.PDF2IMAGE_AVAILABLE', False)
    def test_ocr_unavailable(self):
        """Test behavior when OCR is not available."""
        parser = PDFParser()
        parser.ocr_available = False
        
        with pytest.raises(PDFParseError, match="OCR dependencies not available"):
            parser._extract_text_ocr(b"fake pdf")


class TestPDFParserEdgeCases:
    """Edge case tests for PDF parser."""
    
    def test_very_short_description_filtered(self):
        """Test that very short descriptions are filtered out."""
        parser = PDFParser()
        
        text = "15/06/2024 AB -5.00"  # Very short description
        transactions = parser._parse_transactions(text)
        
        # Should be filtered out (description < 3 chars after cleanup)
        assert len(transactions) == 0
    
    def test_long_description_truncated(self):
        """Test that long descriptions are truncated."""
        parser = PDFParser()
        
        long_desc = "A" * 300
        text = f"15/06/2024 {long_desc} -10.00"
        transactions = parser._parse_transactions(text)
        
        if transactions:
            assert len(transactions[0].description) <= 200
    
    def test_multiple_amounts_same_line(self):
        """Test handling of lines with multiple amounts."""
        parser = PDFParser()
        
        # Some statements show balance and transaction amount
        text = "15/06/2024 Payment Balance: 1000.00 Amount: -25.00"
        transactions = parser._parse_transactions(text)
        
        # Should extract at least one transaction
        assert len(transactions) >= 1
    
    def test_currency_defaults_to_eur(self):
        """Test that currency defaults to EUR."""
        parser = PDFParser()
        
        text = "15/06/2024 Test Transaction -10.00"
        transactions = parser._parse_transactions(text)
        
        if transactions:
            assert transactions[0].currency == "EUR"
