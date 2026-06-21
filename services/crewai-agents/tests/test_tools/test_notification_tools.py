"""Tests for notification tools."""

import json
from unittest.mock import patch, MagicMock


def _session_cm(session):
    """Build a context-manager mock whose __enter__ yields `session`,
    matching `with SessionLocal() as db:` usage in the tools."""
    factory = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    factory.return_value = cm
    return factory


def _scalars(values):
    """Mock a db.scalars(...) result with .all()/.first()."""
    res = MagicMock()
    res.all.return_value = list(values)
    res.first.return_value = values[0] if values else None
    return res


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

    @patch("src.tools.notification_tools.SessionLocal")
    def test_save_in_app_notification(self, mock_factory):
        """Test saving an in-app notification."""
        import uuid

        new_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
        session = MagicMock()

        def _add(obj):
            obj.id = new_id
        session.add.side_effect = _add
        mock_factory.return_value = _session_cm(session).return_value

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
        assert data["notification_id"] == str(new_id)

    @patch("src.tools.notification_tools.SessionLocal")
    def test_save_in_app_notification_with_action_url(self, mock_factory):
        """Test saving in-app notification with action URL."""
        import uuid

        new_id = uuid.UUID("00000000-0000-0000-0000-000000000222")
        session = MagicMock()

        def _add(obj):
            obj.id = new_id
        session.add.side_effect = _add
        mock_factory.return_value = _session_cm(session).return_value

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

    @patch("src.tools.notification_tools.SessionLocal")
    def test_get_user_contact_info(self, mock_factory):
        """Test fetching user contact information."""
        setting = MagicMock()
        setting.notification_channels = ["whatsapp", "in_app"]
        setting.config = {
            "whatsapp_phone": "+33612345678",
            "notification_email": "user@example.com",
        }

        profile = MagicMock()
        profile.id = "00000000-0000-0000-0000-000000000333"
        profile.account_id = "test-123"
        profile.business_type = "micro_entrepreneur"
        profile.tax_regime = "micro"
        profile.declaration_frequency = "monthly"
        profile.tva_applicable = False
        profile.siret = None
        profile.created_at = None
        profile.updated_at = None

        session = MagicMock()
        # First scalars() -> agent_settings, second -> business_profiles
        session.scalars.side_effect = [_scalars([setting]), _scalars([profile])]
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.notification_tools import get_user_contact_info
        result = get_user_contact_info.run(account_id="test-123")
        data = json.loads(result)

        assert data["phone"] == "+33612345678"
        assert data["email"] == "user@example.com"
        assert "whatsapp" in data["channels"]

    @patch("src.tools.notification_tools.SessionLocal")
    def test_save_notification_error_handling(self, mock_factory):
        """Test error handling when saving notification fails."""
        mock_factory.side_effect = Exception("DB error")

        from src.tools.notification_tools import save_in_app_notification
        result = save_in_app_notification.run(
            account_id="test-123",
            title="Test",
            message="Test message",
        )
        data = json.loads(result)

        assert data["saved"] is False
        assert "error" in data
