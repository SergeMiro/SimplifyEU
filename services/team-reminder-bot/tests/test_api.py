"""
Tests for API endpoints (using TestClient).
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Mock supabase before importing the app
with patch("src.db.client.create_client") as mock_create:
    mock_supabase = MagicMock()
    mock_create.return_value = mock_supabase
    from src.main import app

client = TestClient(app)

# Auth headers for test mode
HEADERS = {
    "X-API-Key": "sk_test_123",
    "X-Account-ID": "test-account-001",
    "X-User-ID": "test-user-001",
}


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "team-reminder-bot"

    def test_security_info(self):
        response = client.get("/security-info")
        assert response.status_code == 200
        data = response.json()
        assert "rate_limiting_enabled" in data


class TestRemindersAPI:
    """Test /v1/reminders endpoints."""

    @patch("src.core.reminder_scheduler.create_reminder", new_callable=AsyncMock)
    @patch("src.core.context_manager.log_event", new_callable=AsyncMock)
    def test_create_reminder(self, mock_log, mock_create):
        mock_create.return_value = {
            "id": "test-id",
            "task_text": "Test task",
            "status": "pending",
        }
        mock_log.return_value = {}

        response = client.post(
            "/v1/reminders",
            json={
                "target_user_id": "U_TARGET",
                "task_text": "Test task",
                "remind_at_text": "in 2 hours",
            },
            headers=HEADERS,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["task_text"] == "Test task"

    @patch("src.core.reminder_scheduler.list_reminders", new_callable=AsyncMock)
    def test_list_reminders(self, mock_list):
        mock_list.return_value = {
            "data": [],
            "total": 0,
            "page": 1,
            "limit": 20,
        }

        response = client.get("/v1/reminders", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    @patch("src.core.reminder_scheduler.get_reminder", new_callable=AsyncMock)
    def test_get_reminder_found(self, mock_get):
        mock_get.return_value = {"id": "test-id", "task_text": "Test"}

        response = client.get("/v1/reminders/test-id", headers=HEADERS)
        assert response.status_code == 200

    @patch("src.core.reminder_scheduler.get_reminder", new_callable=AsyncMock)
    def test_get_reminder_not_found(self, mock_get):
        mock_get.return_value = None

        response = client.get("/v1/reminders/nonexistent", headers=HEADERS)
        assert response.status_code == 404

    @patch("src.core.reminder_scheduler.delete_reminder", new_callable=AsyncMock)
    def test_delete_reminder(self, mock_delete):
        mock_delete.return_value = True

        response = client.delete("/v1/reminders/test-id", headers=HEADERS)
        assert response.status_code == 200

    @patch("src.core.reminder_scheduler.snooze_reminder", new_callable=AsyncMock)
    @patch("src.core.context_manager.log_event", new_callable=AsyncMock)
    def test_snooze_reminder(self, mock_log, mock_snooze):
        mock_snooze.return_value = {
            "id": "test-id",
            "status": "pending",
            "snooze_count": 1,
            "target_user_id": "U_TARGET",
        }
        mock_log.return_value = {}

        response = client.post(
            "/v1/reminders/test-id/snooze?minutes=15",
            headers=HEADERS,
        )
        assert response.status_code == 200


class TestAuthSecurity:
    """Test authentication security."""

    def test_missing_api_key(self):
        response = client.get(
            "/v1/reminders",
            headers={"X-Account-ID": "test"},
        )
        assert response.status_code == 401

    def test_missing_account_id(self):
        response = client.get(
            "/v1/reminders",
            headers={"X-API-Key": "sk_test_123"},
        )
        assert response.status_code == 422  # Missing required header
