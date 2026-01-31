"""
Tests for Email Service functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, date
import smtplib

from src.core.email_service import EmailService, email_service
from src.db.models import Analysis, AnalysisItem


@pytest.fixture
def mock_analysis():
    """Create a mock Analysis object for testing."""
    return Analysis(
        id=uuid4(),
        account_id=uuid4(),
        user_id=uuid4(),
        status="completed",
        filename="test_transactions.csv",
        total_transactions=100,
        subscriptions_found=3,
        potential_savings_eur=45.99,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def mock_items():
    """Create mock AnalysisItem objects for testing."""
    analysis_id = uuid4()
    return [
        AnalysisItem(
            id=uuid4(),
            analysis_id=analysis_id,
            merchant_descriptor="NETFLIX COM",
            merchant_name="Netflix",
            is_subscription=True,
            confidence_score=0.95,
            frequency="monthly",
            amount_avg=12.99,
            occurrences=3,
            first_seen=date(2025, 1, 1),
            last_seen=date(2025, 3, 1),
            created_at=datetime.now()
        ),
        AnalysisItem(
            id=uuid4(),
            analysis_id=analysis_id,
            merchant_descriptor="SPOTIFY AB",
            merchant_name="Spotify",
            is_subscription=True,
            confidence_score=0.92,
            frequency="monthly",
            amount_avg=9.99,
            occurrences=3,
            first_seen=date(2025, 1, 1),
            last_seen=date(2025, 3, 1),
            created_at=datetime.now()
        ),
        AnalysisItem(
            id=uuid4(),
            analysis_id=analysis_id,
            merchant_descriptor="ADOBE CREATIVE",
            merchant_name="Adobe Creative Cloud",
            is_subscription=True,
            confidence_score=0.88,
            frequency="monthly",
            amount_avg=23.01,
            occurrences=3,
            first_seen=date(2025, 1, 1),
            last_seen=date(2025, 3, 1),
            created_at=datetime.now()
        ),
    ]


class TestEmailService:
    """Test cases for EmailService class."""

    def test_email_service_initialization(self):
        """Test that EmailService initializes with correct config values."""
        service = EmailService()
        
        assert service.host is not None
        assert service.port is not None
        assert service.user is not None
        assert service.password is not None
        assert service.sender_email is not None
        assert service.sender_name is not None

    def test_is_configured_with_defaults(self):
        """Test that is_configured returns False with placeholder values."""
        service = EmailService()
        # With default placeholder values, should return False
        assert service.is_configured() == False

    @patch.object(EmailService, '__init__', lambda x: None)
    def test_is_configured_with_real_values(self):
        """Test that is_configured returns True with real SMTP values."""
        service = EmailService()
        service.host = "smtp.gmail.com"
        service.user = "real@email.com"
        service.password = "real_password"
        
        assert service.is_configured() == True

    def test_generate_html_report(self, mock_analysis, mock_items):
        """Test HTML report generation."""
        service = EmailService()
        html = service._generate_html_report(mock_analysis, mock_items)
        
        # Check that HTML contains expected elements
        assert "SimplifyEU" in html
        assert "Netflix" in html
        assert "Spotify" in html
        assert "Adobe Creative Cloud" in html
        assert "€12.99" in html or "12.99" in html
        assert "€9.99" in html or "9.99" in html
        assert "Ежемесячно" in html
        assert mock_analysis.filename in html

    def test_generate_html_report_no_subscriptions(self, mock_analysis):
        """Test HTML report generation with no subscriptions."""
        service = EmailService()
        html = service._generate_html_report(mock_analysis, [])
        
        assert "SimplifyEU" in html
        assert "Подписок не обнаружено" in html

    def test_generate_plain_text_report(self, mock_analysis, mock_items):
        """Test plain text report generation."""
        service = EmailService()
        text = service._generate_plain_text_report(mock_analysis, mock_items)
        
        # Check that text contains expected elements
        assert "SimplifyEU" in text
        assert "Netflix" in text
        assert "Spotify" in text
        assert "Adobe Creative Cloud" in text
        assert str(mock_analysis.total_transactions) in text

    def test_generate_plain_text_report_no_subscriptions(self, mock_analysis):
        """Test plain text report with no subscriptions."""
        service = EmailService()
        text = service._generate_plain_text_report(mock_analysis, [])
        
        assert "Подписок не обнаружено" in text

    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_report_email_success(self, mock_smtp, mock_analysis, mock_items):
        """Test successful email sending."""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        # Create service with test config
        service = EmailService()
        service.host = "smtp.test.com"
        service.port = 587
        service.user = "test@test.com"
        service.password = "test_password"
        service.sender_email = "noreply@test.com"
        service.sender_name = "Test Sender"
        service.use_tls = True
        service.use_ssl = False
        
        result = await service.send_report_email(
            recipient_email="user@example.com",
            analysis=mock_analysis,
            items=mock_items
        )
        
        assert result["success"] == True
        assert "user@example.com" in result["message"]
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_report_email_with_pdf(self, mock_smtp, mock_analysis, mock_items):
        """Test email sending with PDF attachment."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        service = EmailService()
        service.host = "smtp.test.com"
        service.port = 587
        service.user = "test@test.com"
        service.password = "test_password"
        service.sender_email = "noreply@test.com"
        service.sender_name = "Test Sender"
        service.use_tls = True
        service.use_ssl = False
        
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        
        result = await service.send_report_email(
            recipient_email="user@example.com",
            analysis=mock_analysis,
            items=mock_items,
            pdf_bytes=pdf_bytes
        )
        
        assert result["success"] == True
        # Verify sendmail was called with email containing attachment
        mock_server.sendmail.assert_called_once()

    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_report_email_auth_error(self, mock_smtp, mock_analysis, mock_items):
        """Test email sending with authentication error."""
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp.return_value = mock_server
        
        service = EmailService()
        service.host = "smtp.test.com"
        service.port = 587
        service.user = "bad@test.com"
        service.password = "wrong_password"
        service.sender_email = "noreply@test.com"
        service.sender_name = "Test Sender"
        service.use_tls = True
        service.use_ssl = False
        
        result = await service.send_report_email(
            recipient_email="user@example.com",
            analysis=mock_analysis,
            items=mock_items
        )
        
        assert result["success"] == False
        assert "authentication" in result["message"].lower()

    @pytest.mark.asyncio
    @patch('smtplib.SMTP_SSL')
    async def test_send_report_email_ssl(self, mock_smtp_ssl, mock_analysis, mock_items):
        """Test email sending with SSL."""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        
        service = EmailService()
        service.host = "smtp.test.com"
        service.port = 465
        service.user = "test@test.com"
        service.password = "test_password"
        service.sender_email = "noreply@test.com"
        service.sender_name = "Test Sender"
        service.use_tls = False
        service.use_ssl = True
        
        result = await service.send_report_email(
            recipient_email="user@example.com",
            analysis=mock_analysis,
            items=mock_items
        )
        
        assert result["success"] == True
        mock_smtp_ssl.assert_called_once_with("smtp.test.com", 465)


class TestEmailServiceSingleton:
    """Test the singleton email_service instance."""

    def test_singleton_exists(self):
        """Test that singleton instance exists."""
        assert email_service is not None
        assert isinstance(email_service, EmailService)

    def test_singleton_has_config(self):
        """Test that singleton has configuration."""
        assert hasattr(email_service, 'host')
        assert hasattr(email_service, 'port')
        assert hasattr(email_service, 'user')
        assert hasattr(email_service, 'password')
