"""Tests for the Financial Reconciliation Assistant agent."""

import pytest
from unittest.mock import patch, MagicMock


class TestFinancialAssistant:
    """Test suite for the Financial Assistant agent creation and configuration."""

    def test_create_financial_assistant(self):
        """Test that the financial assistant agent is created with correct config."""
        with patch("src.agents.financial_assistant.get_recent_transactions"), \
             patch("src.agents.financial_assistant.get_duplicate_pairs"), \
             patch("src.agents.financial_assistant.get_subscription_analysis"), \
             patch("src.agents.financial_assistant.get_financial_insights"), \
             patch("src.agents.financial_assistant.save_financial_insight"), \
             patch("src.agents.financial_assistant.send_whatsapp_notification"), \
             patch("src.agents.financial_assistant.send_email_notification"), \
             patch("src.agents.financial_assistant.save_in_app_notification"), \
             patch("src.agents.financial_assistant.get_user_contact_info"), \
             patch("src.agents.financial_assistant.log_agent_execution"):
            from src.agents.financial_assistant import create_financial_assistant

            agent = create_financial_assistant()

            assert agent.role == "Financial Reconciliation Assistant"
            assert "anomalies" in agent.goal.lower() or "anomal" in agent.goal.lower()
            assert "french" in agent.backstory.lower() or "French" in agent.backstory
            assert agent.allow_delegation is False
            assert len(agent.tools) == 10

    def test_financial_assistant_has_required_tools(self):
        """Test that the financial assistant has all required tools."""
        with patch("src.agents.financial_assistant.get_recent_transactions") as t1, \
             patch("src.agents.financial_assistant.get_duplicate_pairs") as t2, \
             patch("src.agents.financial_assistant.get_subscription_analysis") as t3, \
             patch("src.agents.financial_assistant.get_financial_insights") as t4, \
             patch("src.agents.financial_assistant.save_financial_insight") as t5, \
             patch("src.agents.financial_assistant.send_whatsapp_notification") as t6, \
             patch("src.agents.financial_assistant.send_email_notification") as t7, \
             patch("src.agents.financial_assistant.save_in_app_notification") as t8, \
             patch("src.agents.financial_assistant.get_user_contact_info") as t9, \
             patch("src.agents.financial_assistant.log_agent_execution") as t10:
            from src.agents.financial_assistant import create_financial_assistant

            agent = create_financial_assistant()
            tools = agent.tools

            assert t1 in tools
            assert t2 in tools
            assert t3 in tools
            assert t6 in tools
            assert t8 in tools


class TestTaxAssistant:
    """Test suite for the Tax Assistant agent creation."""

    def test_create_tax_assistant(self):
        """Test that the tax assistant agent is created with correct config."""
        with patch("src.agents.tax_assistant.get_tax_obligations"), \
             patch("src.agents.tax_assistant.save_tax_obligation"), \
             patch("src.agents.tax_assistant.get_business_profile"), \
             patch("src.agents.tax_assistant.generate_tax_calendar"), \
             patch("src.agents.tax_assistant.calculate_turnover_for_period"), \
             patch("src.agents.tax_assistant.check_upcoming_deadlines"), \
             patch("src.agents.tax_assistant.send_whatsapp_notification"), \
             patch("src.agents.tax_assistant.send_email_notification"), \
             patch("src.agents.tax_assistant.save_in_app_notification"), \
             patch("src.agents.tax_assistant.get_user_contact_info"), \
             patch("src.agents.tax_assistant.log_agent_execution"):
            from src.agents.tax_assistant import create_tax_assistant

            agent = create_tax_assistant()

            assert agent.role == "Tax and Reporting Assistant"
            assert "deadline" in agent.goal.lower()
            assert "micro-entrepreneur" in agent.backstory.lower() or "micro" in agent.backstory.lower()
            assert agent.allow_delegation is False


class TestDocumentManager:
    """Test suite for the Document Manager agent creation."""

    def test_create_document_manager(self):
        """Test that the document manager agent is created with correct config."""
        with patch("src.agents.document_manager.link_document_to_transaction"), \
             patch("src.agents.document_manager.search_documents"), \
             patch("src.agents.document_manager.get_unlinked_documents"), \
             patch("src.agents.document_manager.generate_accountant_package"), \
             patch("src.agents.document_manager.get_invoices"), \
             patch("src.agents.document_manager.get_recent_transactions"), \
             patch("src.agents.document_manager.save_in_app_notification"), \
             patch("src.agents.document_manager.get_user_contact_info"), \
             patch("src.agents.document_manager.log_agent_execution"):
            from src.agents.document_manager import create_document_manager

            agent = create_document_manager()

            assert agent.role == "Document Manager and Archivist"
            assert "document" in agent.goal.lower()
            assert agent.allow_delegation is False


class TestClientAssistant:
    """Test suite for the Client Assistant agent creation."""

    def test_create_client_assistant(self):
        """Test that the client assistant agent is created with correct config."""
        with patch("src.agents.client_assistant.get_invoices"), \
             patch("src.agents.client_assistant.send_whatsapp_notification"), \
             patch("src.agents.client_assistant.send_email_notification"), \
             patch("src.agents.client_assistant.save_in_app_notification"), \
             patch("src.agents.client_assistant.get_user_contact_info"), \
             patch("src.agents.client_assistant.log_agent_execution"):
            from src.agents.client_assistant import create_client_assistant

            agent = create_client_assistant()

            assert agent.role == "Client Communication Assistant"
            assert "reminder" in agent.goal.lower() or "communication" in agent.goal.lower()
            assert agent.allow_delegation is False


class TestOperationsCoordinator:
    """Test suite for the Operations Coordinator agent creation."""

    def test_create_operations_coordinator(self):
        """Test that the operations coordinator agent is created with correct config."""
        with patch("src.agents.operations_coordinator.get_recent_transactions"), \
             patch("src.agents.operations_coordinator.get_financial_insights"), \
             patch("src.agents.operations_coordinator.get_tax_obligations"), \
             patch("src.agents.operations_coordinator.get_duplicate_pairs"), \
             patch("src.agents.operations_coordinator.get_subscription_analysis"), \
             patch("src.agents.operations_coordinator.check_upcoming_deadlines"), \
             patch("src.agents.operations_coordinator.get_unlinked_documents"), \
             patch("src.agents.operations_coordinator.send_whatsapp_notification"), \
             patch("src.agents.operations_coordinator.send_email_notification"), \
             patch("src.agents.operations_coordinator.save_in_app_notification"), \
             patch("src.agents.operations_coordinator.get_user_contact_info"), \
             patch("src.agents.operations_coordinator.log_agent_execution"):
            from src.agents.operations_coordinator import create_operations_coordinator

            agent = create_operations_coordinator()

            assert agent.role == "Operations Coordinator — Chief of Staff"
            assert "weekly" in agent.goal.lower() or "briefing" in agent.goal.lower()
            assert agent.allow_delegation is True  # This one can delegate
