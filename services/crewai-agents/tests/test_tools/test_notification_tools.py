"""Tests for notification tools."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestNotificationTools:
    """Test suite for notification delivery tools."""

    @patch("src.tools.notification_tools.settings")
    def test_whatsapp_not_configured(self, mock_settings):
        """Test WhatsApp notification when Twilio is not configured."""
        mock_settings.whatsapp_configured = False

        from src.tools.notification_tools import send_whatsapp_notification
        result = send_whatsapp_notification.run(
            phone_number="+33612345678",
            message="Test message",
        )
        data = json.loads(result)

        assert data["sent"] is False
        assert data["reason"] == "WhatsApp not configured"

    @patch("src.tools.notification_tools.settings")
    def test_email_not_configured(self, mock_settings):
        """Test email notification when SMTP is not configured."""
        mock_settings.smtp_configured = False

        from src.tools.notification_tools import send_email_notification
        result = send_email_notification.run(
            to_email="test@example.com",
            subject="Test Subject",
            body_html="<p>Test body</p>",
        )
        data = json.loads(result)

        assert data["sent"] is False
        assert data["reason"] == "SMTP not configured"

    @patch("src.tools.notification_tools.supabase")
    def test_save_in_app_notification(self, mock_db):
        """Test saving an in-app notification."""
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "notif-1"}])
        mock_db.table.return_value = mock_chain

        from src.tools.notification_tools import save_in_app_notification
        result = save_in_app_notification.run(
            account_id="test-123",
            title="Anomaly Detected",
            message="3 suspicious transactions found",
            notification_type="warning",
            agent_type="financial_assistant",
        )
        data = json.loads(result)

        assert data["saved"] is True
        assert data["notification_id"] == "notif-1"

    @patch("src.tools.notification_tools.supabase")
    def test_save_in_app_notification_with_action_url(self, mock_db):
        """Test saving in-app notification with action URL."""
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "notif-2"}])
        mock_db.table.return_value = mock_chain

        from src.tools.notification_tools import save_in_app_notification
        result = save_in_app_notification.run(
            account_id="test-123",
            title="Report Ready",
            message="Monthly report is ready",
            notification_type="success",
            action_url="/dashboard/reports/monthly",
        )
        data = json.loads(result)

        assert data["saved"] is True

    @patch("src.tools.notification_tools.supabase")
    def test_get_user_contact_info(self, mock_db):
        """Test fetching user contact information."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.side_effect = [
            MagicMock(data=[{
                "notification_channels": ["whatsapp", "in_app"],
                "config": {
                    "whatsapp_phone": "+33612345678",
                    "notification_email": "user@example.com",
                },
            }]),
            MagicMock(data=[{"business_type": "micro_entrepreneur"}]),
        ]
        mock_db.table.return_value = mock_chain

        from src.tools.notification_tools import get_user_contact_info
        result = get_user_contact_info.run(account_id="test-123")
        data = json.loads(result)

        assert data["phone"] == "+33612345678"
        assert data["email"] == "user@example.com"
        assert "whatsapp" in data["channels"]

    @patch("src.tools.notification_tools.supabase")
    def test_save_notification_error_handling(self, mock_db):
        """Test error handling when saving notification fails."""
        mock_db.table.side_effect = Exception("DB error")

        from src.tools.notification_tools import save_in_app_notification
        result = save_in_app_notification.run(
            account_id="test-123",
            title="Test",
            message="Test message",
        )
        data = json.loads(result)

        assert data["saved"] is False
        assert "error" in data
