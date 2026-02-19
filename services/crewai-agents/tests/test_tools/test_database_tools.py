"""Tests for database tools."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestDatabaseTools:
    """Test suite for database access tools."""

    @patch("src.tools.database_tools.supabase")
    def test_get_recent_transactions_no_data(self, mock_db):
        """Test fetching transactions when no analyses exist."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value = mock_chain

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert "transactions" in data
        assert data["transactions"] == []

    @patch("src.tools.database_tools.supabase")
    def test_get_recent_transactions_with_data(self, mock_db):
        """Test fetching transactions with existing analysis."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain

        # First call returns analysis, second returns items
        mock_chain.execute.side_effect = [
            MagicMock(data=[{"id": "analysis-1"}]),
            MagicMock(data=[{"id": "item-1", "merchant_name": "Netflix"}]),
        ]
        mock_db.table.return_value = mock_chain

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert data["analysis_id"] == "analysis-1"
        assert len(data["transactions"]) == 1

    @patch("src.tools.database_tools.supabase")
    def test_get_invoices(self, mock_db):
        """Test fetching invoices."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "inv-1", "vendor_name": "EDF", "total_amount": 100},
        ])
        mock_db.table.return_value = mock_chain

        from src.tools.database_tools import get_invoices
        result = get_invoices.run(account_id="test-123", status_filter="all")
        data = json.loads(result)

        assert data["count"] == 1
        assert data["invoices"][0]["vendor_name"] == "EDF"

    @patch("src.tools.database_tools.supabase")
    def test_get_duplicate_pairs(self, mock_db):
        """Test fetching duplicate pairs."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value = mock_chain

        from src.tools.database_tools import get_duplicate_pairs
        result = get_duplicate_pairs.run(account_id="test-123")
        data = json.loads(result)

        assert "duplicates" in data
        assert data["count"] == 0

    @patch("src.tools.database_tools.supabase")
    def test_save_financial_insight(self, mock_db):
        """Test saving a financial insight."""
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "insight-1"}])
        mock_db.table.return_value = mock_chain

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
        assert data["insight_id"] == "insight-1"

    @patch("src.tools.database_tools.supabase")
    def test_save_tax_obligation(self, mock_db):
        """Test saving a tax obligation."""
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "tax-1"}])
        mock_db.table.return_value = mock_chain

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

    @patch("src.tools.database_tools.supabase")
    def test_get_business_profile(self, mock_db):
        """Test fetching business profile."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "business_type": "micro_entrepreneur",
            "tax_regime": "micro",
        }])
        mock_db.table.return_value = mock_chain

        from src.tools.database_tools import get_business_profile
        result = get_business_profile.run(account_id="test-123")
        data = json.loads(result)

        assert data["profile"]["business_type"] == "micro_entrepreneur"

    @patch("src.tools.database_tools.supabase")
    def test_log_agent_execution(self, mock_db):
        """Test logging an agent execution."""
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "log-1"}])
        mock_db.table.return_value = mock_chain

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

    @patch("src.tools.database_tools.supabase")
    def test_database_error_handling(self, mock_db):
        """Test that database errors are handled gracefully."""
        mock_db.table.side_effect = Exception("Connection failed")

        from src.tools.database_tools import get_recent_transactions
        result = get_recent_transactions.run(account_id="test-123", days=30)
        data = json.loads(result)

        assert "error" in data
