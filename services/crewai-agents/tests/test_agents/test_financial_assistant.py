"""Tests for all agent creation and configuration."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set a dummy key so CrewAI Agent doesn't fail on LLM init
os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-testing"


@pytest.fixture(autouse=True)
def mock_llm():
    """Mock the LLM so agents can be created without a real API key."""
    mock = MagicMock()
    mock.model = "test-model"
    with patch("crewai.utilities.llm_utils.create_llm", return_value=mock):
        yield mock


class TestFinancialAssistant:
    """Test suite for the Financial Assistant agent."""

    def test_create_financial_assistant(self):
        from src.agents.financial_assistant import create_financial_assistant

        agent = create_financial_assistant()

        assert agent.role == "Financial Reconciliation Assistant"
        assert "anomal" in agent.goal.lower()
        assert "french" in agent.backstory.lower()
        assert agent.allow_delegation is False
        assert len(agent.tools) == 10

    def test_financial_assistant_tools_are_crewai_tools(self):
        from src.agents.financial_assistant import create_financial_assistant
        from crewai.tools import BaseTool

        agent = create_financial_assistant()
        for tool in agent.tools:
            assert isinstance(tool, BaseTool), f"{tool} is not a BaseTool"


class TestTaxAssistant:
    """Test suite for the Tax Assistant agent."""

    def test_create_tax_assistant(self):
        from src.agents.tax_assistant import create_tax_assistant

        agent = create_tax_assistant()

        assert agent.role == "Tax and Reporting Assistant"
        assert "deadline" in agent.goal.lower()
        assert "micro" in agent.backstory.lower()
        assert agent.allow_delegation is False
        assert len(agent.tools) == 11

    def test_tax_assistant_has_calendar_tools(self):
        from src.agents.tax_assistant import create_tax_assistant

        agent = create_tax_assistant()
        tool_names = [t.name for t in agent.tools]

        assert "Generate tax calendar" in tool_names
        assert "Calculate turnover for period" in tool_names
        assert "Check upcoming deadlines" in tool_names


class TestDocumentManager:
    """Test suite for the Document Manager agent."""

    def test_create_document_manager(self):
        from src.agents.document_manager import create_document_manager

        agent = create_document_manager()

        assert agent.role == "Document Manager and Archivist"
        assert "document" in agent.goal.lower()
        assert agent.allow_delegation is False
        assert len(agent.tools) == 9

    def test_document_manager_has_doc_tools(self):
        from src.agents.document_manager import create_document_manager

        agent = create_document_manager()
        tool_names = [t.name for t in agent.tools]

        assert "Link document to transaction" in tool_names
        assert "Search documents" in tool_names
        assert "Get unlinked documents" in tool_names
        assert "Generate accountant package" in tool_names


class TestClientAssistant:
    """Test suite for the Client Assistant agent."""

    def test_create_client_assistant(self):
        from src.agents.client_assistant import create_client_assistant

        agent = create_client_assistant()

        assert agent.role == "Client Communication Assistant"
        assert "communication" in agent.goal.lower() or "reminder" in agent.goal.lower()
        assert agent.allow_delegation is False
        assert len(agent.tools) == 6


class TestOperationsCoordinator:
    """Test suite for the Operations Coordinator agent."""

    def test_create_operations_coordinator(self):
        from src.agents.operations_coordinator import create_operations_coordinator

        agent = create_operations_coordinator()

        assert agent.role == "Operations Coordinator — Chief of Staff"
        assert "briefing" in agent.goal.lower() or "weekly" in agent.goal.lower()
        assert agent.allow_delegation is True
        assert len(agent.tools) == 12

    def test_operations_coordinator_has_all_domain_tools(self):
        from src.agents.operations_coordinator import create_operations_coordinator

        agent = create_operations_coordinator()
        tool_names = [t.name for t in agent.tools]

        assert "Get recent transactions" in tool_names
        assert "Get financial insights" in tool_names
        assert "Get tax obligations" in tool_names
        assert "Check upcoming deadlines" in tool_names
        assert "Get unlinked documents" in tool_names
        assert "Send WhatsApp notification" in tool_names
