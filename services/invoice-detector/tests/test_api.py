"""
Tests for API endpoints (using TestClient).
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.db.session import get_db

client = TestClient(app)

HEADERS = {
    "X-API-Key": "sk_test_123",
    "X-Account-ID": "test-account-001",
    "X-User-ID": "test-user-001",
}


def _override_db(session):
    """Install a get_db override that yields the given (mock) session."""
    def _dep():
        yield session
    app.dependency_overrides[get_db] = _dep


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "invoice-detector"

    def test_security_info(self):
        response = client.get("/security-info")
        assert response.status_code == 200
        data = response.json()
        assert data["rate_limiting_enabled"] is True


class TestInvoicesAPI:
    """Test /v1/invoices endpoints."""

    def test_list_invoices(self):
        session = MagicMock()
        session.scalar.return_value = 0
        session.scalars.return_value.all.return_value = []
        _override_db(session)

        response = client.get("/v1/invoices", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0

    def test_upload_no_file(self):
        response = client.post("/v1/invoices/upload", headers=HEADERS)
        assert response.status_code == 422


class TestDuplicatesAPI:
    """Test /v1/duplicates endpoints."""

    def test_list_duplicates(self):
        session = MagicMock()
        session.scalar.return_value = 0
        session.scalars.return_value.all.return_value = []
        _override_db(session)

        response = client.get("/v1/duplicates", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0


class TestAuthSecurity:
    """Test authentication."""

    def test_missing_api_key(self):
        response = client.get("/v1/invoices", headers={"X-Account-ID": "test"})
        assert response.status_code == 401

    def test_missing_account_id(self):
        response = client.get("/v1/invoices", headers={"X-API-Key": "sk_test_123"})
        assert response.status_code == 422

    def test_health_no_auth(self):
        response = client.get("/health")
        assert response.status_code == 200
