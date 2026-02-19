"""Tests for CrewAI Flow state management and configuration."""

import pytest
from src.flows.financial_flow import FinancialFlow, FinancialFlowState
from src.flows.tax_flow import TaxFlow, TaxFlowState
from src.flows.document_flow import DocumentFlow, DocumentFlowState
from src.flows.client_flow import ClientFlow, ClientFlowState
from src.flows.operations_flow import OperationsFlow, OperationsFlowState


class TestFlowStates:
    """Test flow state initialization and defaults."""

    def test_financial_flow_state_defaults(self):
        state = FinancialFlowState()
        assert state.account_id == ""
        assert state.trigger == ""
        assert state.status == "pending"
        assert state.analysis_result == ""

    def test_tax_flow_state_defaults(self):
        state = TaxFlowState()
        assert state.account_id == ""
        assert state.status == "pending"
        assert state.calendar_result == ""

    def test_document_flow_state_defaults(self):
        state = DocumentFlowState()
        assert state.account_id == ""
        assert state.status == "pending"
        assert state.document_id == ""

    def test_client_flow_state_defaults(self):
        state = ClientFlowState()
        assert state.account_id == ""
        assert state.status == "pending"

    def test_operations_flow_state_defaults(self):
        state = OperationsFlowState()
        assert state.account_id == ""
        assert state.status == "pending"
        assert state.briefing_result == ""

    def test_financial_flow_state_with_values(self):
        state = FinancialFlowState(
            account_id="test-123",
            trigger="manual",
            status="running",
        )
        assert state.account_id == "test-123"
        assert state.trigger == "manual"
        assert state.status == "running"

    def test_tax_flow_state_with_values(self):
        state = TaxFlowState(
            account_id="test-456",
            trigger="cron",
            status="completed",
            calendar_result='{"obligations": []}',
        )
        assert state.account_id == "test-456"
        assert state.status == "completed"


class TestFlowClasses:
    """Test that flow classes are properly constructed."""

    def test_financial_flow_class_exists(self):
        assert FinancialFlow is not None
        # Verify it's a Flow subclass
        assert hasattr(FinancialFlow, "kickoff")

    def test_tax_flow_class_exists(self):
        assert TaxFlow is not None
        assert hasattr(TaxFlow, "kickoff")

    def test_document_flow_class_exists(self):
        assert DocumentFlow is not None
        assert hasattr(DocumentFlow, "kickoff")

    def test_client_flow_class_exists(self):
        assert ClientFlow is not None
        assert hasattr(ClientFlow, "kickoff")

    def test_operations_flow_class_exists(self):
        assert OperationsFlow is not None
        assert hasattr(OperationsFlow, "kickoff")
