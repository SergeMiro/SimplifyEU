import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest


@pytest.fixture
def sample_invoice_a():
    """Sample parsed invoice data."""
    return {
        "id": "inv-001",
        "account_id": "test-account",
        "filename": "invoice_2025_001.pdf",
        "file_hash": "abc123hash",
        "invoice_number": "INV-2025-001",
        "vendor_name": "Acme Corp EU",
        "invoice_date": "15/01/2026",
        "due_date": "15/02/2026",
        "total_amount": 1234.56,
        "currency": "EUR",
        "line_items": [
            {"quantity": 10, "description": "Consulting hours", "amount": 1000.00},
            {"quantity": 1, "description": "Travel expenses", "amount": 234.56},
        ],
        "raw_text": "Invoice No. INV-2025-001\nAcme Corp EU\nDate: 15/01/2026\nTotal: €1.234,56",
    }


@pytest.fixture
def sample_invoice_b():
    """Second invoice — similar to A (potential duplicate)."""
    return {
        "id": "inv-002",
        "account_id": "test-account",
        "filename": "facture_2025_001.pdf",
        "file_hash": "def456hash",
        "invoice_number": "INV-2025-001",
        "vendor_name": "ACME Corp EU",
        "invoice_date": "15/01/2026",
        "due_date": "15/02/2026",
        "total_amount": 1234.56,
        "currency": "EUR",
        "line_items": [
            {"quantity": 10, "description": "Consulting hours", "amount": 1000.00},
            {"quantity": 1, "description": "Travel expenses", "amount": 234.56},
        ],
        "raw_text": "Facture N° INV-2025-001\nACME Corp EU\nDate: 15/01/2026\nMontant TTC: €1.234,56",
    }


@pytest.fixture
def sample_invoice_c():
    """Third invoice — different from A."""
    return {
        "id": "inv-003",
        "account_id": "test-account",
        "filename": "rechnung_2025_042.pdf",
        "file_hash": "ghi789hash",
        "invoice_number": "RE-2025-042",
        "vendor_name": "Berlin GmbH",
        "invoice_date": "22/03/2026",
        "due_date": "22/04/2026",
        "total_amount": 5678.90,
        "currency": "EUR",
        "line_items": [
            {"quantity": 5, "description": "Software license", "amount": 5000.00},
            {"quantity": 1, "description": "Setup fee", "amount": 678.90},
        ],
        "raw_text": "Rechnung Nr. RE-2025-042\nBerlin GmbH\nDatum: 22.03.2026\nGesamt: €5.678,90",
    }
