"""
Tests for API endpoints (using TestClient).
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock supabase before importing the app
with patch("src.db.client.create_client") as mock_create:
    mock_supabase = MagicMock()
    mock_create.return_value = mock_supabase
    from src.main import app

client = TestClient(app)

HEADERS = {
    "X-API-Key": "sk_test_123",
    "X-Account-ID": "test-account-001",
}


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

    @patch("src.db.client.supabase")
    def test_list_invoices(self, mock_sb):
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        response = client.get("/v1/invoices", headers=HEADERS)
        assert response.status_code == 200

    def test_upload_no_file(self):
        response = client.post("/v1/invoices/upload", headers=HEADERS)
        assert response.status_code == 422


class TestDuplicatesAPI:
    """Test /v1/duplicates endpoints."""

    @patch("src.db.client.supabase")
    def test_list_duplicates(self, mock_sb):
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        response = client.get("/v1/duplicates", headers=HEADERS)
        assert response.status_code == 200


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
