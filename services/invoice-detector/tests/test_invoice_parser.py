"""
Tests for the invoice text parser.
"""
import pytest
from src.core.invoice_parser import parse_invoice_text, _parse_amount


class TestParseAmount:
    """Test amount parsing with European and standard formats."""

    def test_european_format(self):
        assert _parse_amount("1.234,56") == 1234.56

    def test_standard_format(self):
        assert _parse_amount("1,234.56") == 1234.56

    def test_european_no_thousands(self):
        assert _parse_amount("234,56") == 234.56

    def test_spaces_european(self):
        assert _parse_amount("1 234,56") == 1234.56

    def test_simple_integer(self):
        assert _parse_amount("1000") == 1000.0

    def test_none_input(self):
        assert _parse_amount(None) is None

    def test_empty_string(self):
        assert _parse_amount("") is None

    def test_invalid_string(self):
        assert _parse_amount("abc") is None


class TestParseInvoiceText:
    """Test full invoice text parsing."""

    def test_english_invoice(self):
        text = """
        Acme Corporation
        Invoice No. INV-2025-001
        Date: 15/01/2026
        Due Date: 15/02/2026
        Total: €1.234,56
        """
        result = parse_invoice_text(text)
        assert result.invoice_number == "INV-2025-001"
        assert result.total_amount == 1234.56
        assert result.invoice_date == "15/01/2026"
        assert result.currency == "EUR"

    def test_french_invoice(self):
        text = """
        Société Française SA
        Facture N° FAC-2025-042
        Date: 22/03/2026
        Échéance: 22/04/2026
        Montant TTC: €5.678,90
        """
        result = parse_invoice_text(text)
        assert result.invoice_number is not None
        assert result.total_amount == 5678.90
        assert result.currency == "EUR"

    def test_german_invoice(self):
        text = """
        Berlin GmbH
        Rechnung Nr. RE-2025-100
        Datum: 01.06.2026
        Gesamt: €999,99
        """
        result = parse_invoice_text(text)
        assert result.invoice_number is not None
        assert result.total_amount == 999.99

    def test_empty_text(self):
        result = parse_invoice_text("")
        assert result.invoice_number is None
        assert result.total_amount is None
        assert result.raw_text == ""

    def test_none_text(self):
        result = parse_invoice_text(None)
        assert result.invoice_number is None

    def test_vendor_from_first_line(self):
        text = "Acme Corporation\nInvoice No. INV-001\nTotal: €100,00"
        result = parse_invoice_text(text)
        assert result.vendor_name is not None

    def test_currency_detection_usd(self):
        text = "Total: $500.00"
        result = parse_invoice_text(text)
        assert result.currency == "USD"

    def test_currency_detection_gbp(self):
        text = "Total: £500.00"
        result = parse_invoice_text(text)
        assert result.currency == "GBP"

    def test_line_items_extraction(self):
        text = """
        Invoice No. INV-001
        10 Consulting hours            1000,00
        1  Travel expenses              234,56
        Total: €1.234,56
        """
        result = parse_invoice_text(text)
        assert len(result.line_items) >= 1
