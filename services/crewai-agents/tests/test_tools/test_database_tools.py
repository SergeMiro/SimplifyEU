"""Tests for database tools (SQLAlchemy session layer)."""

import json
from unittest.mock import MagicMock, patch


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


class TestDatabaseTools:
    """Test suite for database access tools."""

    @patch("src.tools.database_tools.SessionLocal")
    def test_get_recent_transactions_no_data(self, mock_factory):
        """Test fetching transactions when no analyses exist."""
        session = MagicMock()
        session.scalars.return_value = _scalars([])
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert "transactions" in data
        assert data["transactions"] == []

    @patch("src.tools.database_tools.SessionLocal")
    def test_get_recent_transactions_with_data(self, mock_factory):
        """Test fetching transactions with existing analysis."""
        import uuid

        analysis = MagicMock()
        analysis.id = uuid.UUID("00000000-0000-0000-0000-0000000000a1")

        item = MagicMock()
        item.id = uuid.UUID("00000000-0000-0000-0000-0000000000b1")
        item.analysis_id = analysis.id
        item.merchant_descriptor = "NETFLIX"
        item.merchant_name = "Netflix"
        item.category = None
        item.amount_avg = 13.99
        item.amount_min = None
        item.amount_max = None
        item.currency = "EUR"
        item.frequency = "monthly"
        item.occurrences = 3
        item.first_seen = None
        item.last_seen = None
        item.confidence_score = None
        item.is_subscription = True
        item.tags = []
        item.recommendation = None
        item.created_at = None

        session = MagicMock()
        # First scalars() -> analysis lookup, second -> items
        session.scalars.side_effect = [_scalars([analysis]), _scalars([item])]
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert data["analysis_id"] == str(analysis.id)
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["merchant_name"] == "Netflix"

    @patch("src.tools.database_tools.SessionLocal")
    def test_get_invoices(self, mock_factory):
        """Test fetching invoices."""
        import uuid

        inv = MagicMock()
        inv.id = uuid.UUID("00000000-0000-0000-0000-0000000000c1")
        inv.account_id = uuid.UUID("00000000-0000-0000-0000-0000000000c2")
        inv.stripe_invoice_id = "in_123"
        inv.amount = 100
        inv.currency = "eur"
        inv.status = "draft"
        inv.pdf_url = None
        inv.created_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([inv])
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import get_invoices
        result = get_invoices.run(account_id="test-123", status_filter="all")
        data = json.loads(result)

        assert data["count"] == 1
        assert data["invoices"][0]["status"] == "draft"

    @patch("src.tools.database_tools.SessionLocal")
    def test_get_duplicate_pairs(self, mock_factory):
        """Test fetching duplicate pairs."""
        session = MagicMock()
        session.scalars.return_value = _scalars([])
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import get_duplicate_pairs
        result = get_duplicate_pairs.run(account_id="test-123")
        data = json.loads(result)

        assert "duplicates" in data
        assert data["count"] == 0

    @patch("src.tools.database_tools.SessionLocal")
    def test_save_financial_insight(self, mock_factory):
        """Test saving a financial insight."""
        import uuid

        new_id = uuid.UUID("00000000-0000-0000-0000-0000000000d1")

        session = MagicMock()

        def _add(obj):
            obj.id = new_id
        session.add.side_effect = _add
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import save_financial_insight
        result = save_financial_insight.run(
            account_id="test-123",
            insight_type="anomaly",
            title="Large charge detected",
            description="Unusually large charge of 5000€",
            severity="warning",
            data='{"amount": 5000}',
        )
        data = json.loads(result)

        assert data["success"] is True
        assert data["insight_id"] == str(new_id)

    @patch("src.tools.database_tools.SessionLocal")
    def test_save_tax_obligation(self, mock_factory):
        """Test saving a tax obligation."""
        import uuid

        new_id = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
        session = MagicMock()

        def _add(obj):
            obj.id = new_id
        session.add.side_effect = _add
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import save_tax_obligation
        result = save_tax_obligation.run(
            account_id="test-123",
            obligation_type="declaration_ca",
            title="Déclaration CA T1",
            deadline="2025-04-30T23:59:00",
            description="Quarterly turnover declaration",
            service_url="https://autoentrepreneur.urssaf.fr",
        )
        data = json.loads(result)

        assert data["success"] is True

    @patch("src.tools.database_tools.SessionLocal")
    def test_get_business_profile(self, mock_factory):
        """Test fetching business profile."""
        import uuid

        profile = MagicMock()
        profile.id = uuid.UUID("00000000-0000-0000-0000-0000000000f1")
        profile.account_id = "test-123"
        profile.business_type = "micro_entrepreneur"
        profile.tax_regime = "micro"
        profile.declaration_frequency = "monthly"
        profile.tva_applicable = False
        profile.siret = None
        profile.created_at = None
        profile.updated_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([profile])
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import get_business_profile
        result = get_business_profile.run(account_id="test-123")
        data = json.loads(result)

        assert data["profile"]["business_type"] == "micro_entrepreneur"

    @patch("src.tools.database_tools.SessionLocal")
    def test_log_agent_execution(self, mock_factory):
        """Test logging an agent execution."""
        import uuid

        new_id = uuid.UUID("00000000-0000-0000-0000-000000000a11")
        session = MagicMock()

        def _add(obj):
            obj.id = new_id
        session.add.side_effect = _add
        mock_factory.return_value = _session_cm(session).return_value

        from src.tools.database_tools import log_agent_execution
        result = log_agent_execution.run(
            account_id="test-123",
            agent_type="financial_assistant",
            flow_name="financial",
            trigger="manual",
            status="completed",
        )
        data = json.loads(result)

        assert data["success"] is True

    @patch("src.tools.database_tools.SessionLocal")
    def test_database_error_handling(self, mock_factory):
        """Test that database errors are handled gracefully."""
        mock_factory.side_effect = Exception("Connection failed")

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert "error" in data
