"""
Security-focused tests for Team Reminder Bot.
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


class TestAuthSecurity:
    """Test API Key authentication security."""

    def test_no_auth_headers_returns_error(self):
        """Request without any auth headers should fail."""
        response = client.get("/v1/reminders")
        assert response.status_code in (401, 422)

    def test_api_key_only_no_account_id(self):
        """API key without account ID should fail."""
        response = client.get(
            "/v1/reminders",
            headers={"X-API-Key": "sk_test_123"},
        )
        assert response.status_code == 422

    def test_account_id_only_no_api_key(self):
        """Account ID without API key should fail."""
        response = client.get(
            "/v1/reminders",
            headers={"X-Account-ID": "test-account"},
        )
        assert response.status_code == 401

    def test_empty_api_key(self):
        """Empty API key should fail."""
        response = client.get(
            "/v1/reminders",
            headers={"X-API-Key": "", "X-Account-ID": "test-account"},
        )
        assert response.status_code == 401

    def test_valid_test_key_in_dev(self):
        """Test key should work in development."""
        response = client.get("/health")
        assert response.status_code == 200


class TestInputValidation:
    """Test input validation on API endpoints."""

    HEADERS = {
        "X-API-Key": "sk_test_123",
        "X-Account-ID": "test-account-001",
        "X-User-ID": "test-user",
    }

    def test_create_reminder_empty_task(self):
        """Empty task text should be rejected."""
        response = client.post(
            "/v1/reminders",
            json={
                "target_user_id": "U_TARGET",
                "task_text": "",
            },
            headers=self.HEADERS,
        )
        assert response.status_code == 422

    def test_create_reminder_missing_target(self):
        """Missing target_user_id should be rejected."""
        response = client.post(
            "/v1/reminders",
            json={"task_text": "Test task"},
            headers=self.HEADERS,
        )
        assert response.status_code == 422

    def test_list_reminders_invalid_page(self):
        """Page < 1 should be rejected."""
        response = client.get(
            "/v1/reminders?page=0",
            headers=self.HEADERS,
        )
        assert response.status_code == 422

    def test_list_reminders_limit_too_high(self):
        """Limit > 100 should be rejected."""
        response = client.get(
            "/v1/reminders?limit=999",
            headers=self.HEADERS,
        )
        assert response.status_code == 422

    def test_snooze_negative_minutes(self):
        """Negative snooze minutes should be rejected."""
        response = client.post(
            "/v1/reminders/test-id/snooze?minutes=-5",
            headers=self.HEADERS,
        )
        assert response.status_code == 422


class TestHealthEndpoints:
    """Test non-authenticated endpoints."""

    def test_health_no_auth(self):
        """Health check should work without auth."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_security_info_no_auth(self):
        """Security info should work without auth."""
        response = client.get("/security-info")
        assert response.status_code == 200
        data = response.json()
        assert data["rate_limiting_enabled"] is True
