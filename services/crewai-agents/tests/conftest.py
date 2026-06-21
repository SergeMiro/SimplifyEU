"""
Shared test fixtures for the CrewAI agents service.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

# Set test environment before any imports
os.environ["ENVIRONMENT"] = "development"
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/simplifyeu_db"
)


@pytest.fixture
def sample_account_id():
    return "test-account-123"


@pytest.fixture
def sample_business_profile():
    return {
        "id": "profile-1",
        "account_id": "test-account-123",
        "business_type": "micro_entrepreneur",
        "tax_regime": "micro",
        "declaration_frequency": "quarterly",
        "tva_applicable": False,
        "siret": "12345678901234",
    }


@pytest.fixture
def sample_transactions():
    return [
        {
            "id": "txn-1",
            "merchant_descriptor": "NETFLIX",
            "merchant_name": "Netflix",
            "category": "entertainment",
            "amount_avg": 13.99,
            "currency": "EUR",
            "frequency": "monthly",
            "is_subscription": True,
            "confidence_score": 0.95,
        },
        {
            "id": "txn-2",
            "merchant_descriptor": "LOYER BUREAU",
            "merchant_name": "Loyer Bureau",
            "category": "rent",
            "amount_avg": 800.00,
            "currency": "EUR",
            "frequency": "monthly",
            "is_subscription": True,
            "confidence_score": 0.99,
        },
    ]


@pytest.fixture
def sample_invoices():
    return [
        {
            "id": "inv-1",
            "account_id": "test-account-123",
            "filename": "facture_mars_2025.pdf",
            "vendor_name": "EDF",
            "total_amount": 156.78,
            "currency": "EUR",
            "invoice_date": "2025-03-15",
            "status": "pending",
        },
        {
            "id": "inv-2",
            "account_id": "test-account-123",
            "filename": "facture_loyer.pdf",
            "vendor_name": "SCI Bureau",
            "total_amount": 800.00,
            "currency": "EUR",
            "invoice_date": "2025-03-01",
            "status": "pending",
        },
    ]


@pytest.fixture
def sample_tax_obligations():
    return [
        {
            "id": "tax-1",
            "account_id": "test-account-123",
            "obligation_type": "declaration_ca",
            "title": "Déclaration CA - T1",
            "deadline": "2025-04-30T23:59:00",
            "status": "pending",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
        },
    ]
