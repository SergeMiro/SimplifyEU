"""Tests for the FastAPI endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    with patch("src.db.client.create_client") as mock_create:
        mock_supabase = MagicMock()
        mock_create.return_value = mock_supabase

        with patch("src.auth.api_key.supabase", mock_supabase):
            from src.main import app
            return TestClient(app)


@pytest.fixture
def auth_headers():
    """Standard auth headers for test requests."""
    return {
        "X-API-Key": "sk_test_123",
        "X-Account-ID": "test-account-123",
    }


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "crewai-agents"

    def test_security_info(self, client):
        response = client.get("/security-info")
        assert response.status_code == 200
        data = response.json()
        assert "cors_origins_configured" in data
        assert "rate_limiting_enabled" in data


class TestAgentEndpoints:
    """Test agent settings management endpoints."""

    @patch("src.api.v1.agents.supabase")
    def test_list_agents_creates_defaults(self, mock_db, client, auth_headers):
        """Test that listing agents creates defaults if none exist."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.side_effect = [
            MagicMock(data=[]),  # First call: no settings
            MagicMock(data=[  # Second call: after insert
                {"agent_type": "financial_assistant", "status": "disabled"},
                {"agent_type": "tax_assistant", "status": "disabled"},
            ]),
        ]
        mock_chain.insert.return_value = mock_chain
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/agents", headers=auth_headers)
        assert response.status_code == 200

    @patch("src.api.v1.agents.supabase")
    def test_get_agent_setting(self, mock_db, client, auth_headers):
        """Test getting a specific agent's settings."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "agent_type": "financial_assistant",
            "status": "enabled",
            "notification_channels": ["whatsapp", "in_app"],
        }])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/agents/financial_assistant", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"

    @patch("src.api.v1.agents.supabase")
    def test_toggle_agent_enable(self, mock_db, client, auth_headers):
        """Test enabling an agent."""
        mock_chain = MagicMock()
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "agent_type": "financial_assistant",
            "status": "enabled",
        }])
        mock_db.table.return_value = mock_chain

        response = client.post(
            "/v1/agents/financial_assistant/toggle",
            headers=auth_headers,
            json={"status": "enabled"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"

    @patch("src.api.v1.agents.supabase")
    def test_toggle_agent_disable(self, mock_db, client, auth_headers):
        """Test disabling an agent."""
        mock_chain = MagicMock()
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "agent_type": "tax_assistant",
            "status": "disabled",
        }])
        mock_db.table.return_value = mock_chain

        response = client.post(
            "/v1/agents/tax_assistant/toggle",
            headers=auth_headers,
            json={"status": "disabled"},
        )
        assert response.status_code == 200

    @patch("src.api.v1.agents.supabase")
    def test_get_notifications(self, mock_db, client, auth_headers):
        """Test fetching notifications."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "n1", "title": "Anomaly found", "read": False},
        ])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    @patch("src.api.v1.agents.supabase")
    def test_mark_notification_read(self, mock_db, client, auth_headers):
        """Test marking a notification as read."""
        mock_chain = MagicMock()
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "n1", "read": True}])
        mock_db.table.return_value = mock_chain

        response = client.patch("/v1/notifications/n1/read", headers=auth_headers)
        assert response.status_code == 200


class TestFlowEndpoints:
    """Test flow management and trigger endpoints."""

    @patch("src.api.v1.flows._is_agent_enabled")
    @patch("src.api.v1.flows.supabase")
    def test_list_flows(self, mock_db, mock_enabled, client, auth_headers):
        """Test listing available flows."""
        mock_enabled.return_value = True

        response = client.get("/v1/flows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        flow_names = [f["name"] for f in data["flows"]]
        assert "financial" in flow_names
        assert "tax" in flow_names
        assert "document" in flow_names
        assert "client" in flow_names
        assert "operations" in flow_names

    @patch("src.api.v1.flows._is_agent_enabled")
    def test_trigger_flow_agent_disabled(self, mock_enabled, client, auth_headers):
        """Test that triggering a flow fails when agent is disabled."""
        mock_enabled.return_value = False

        response = client.post(
            "/v1/flows/financial/trigger",
            headers=auth_headers,
            json={"flow_name": "financial", "trigger_data": {}},
        )
        assert response.status_code == 403

    def test_trigger_nonexistent_flow(self, client, auth_headers):
        """Test triggering a flow that doesn't exist."""
        response = client.post(
            "/v1/flows/nonexistent/trigger",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("src.api.v1.flows._is_agent_enabled")
    @patch("src.api.v1.flows.supabase")
    def test_trigger_flow_success(self, mock_db, mock_enabled, client, auth_headers):
        """Test successfully triggering a flow."""
        mock_enabled.return_value = True
        mock_chain = MagicMock()
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value = mock_chain

        response = client.post(
            "/v1/flows/financial/trigger",
            headers=auth_headers,
            json={"flow_name": "financial", "trigger_data": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "execution_id" in data

    @patch("src.api.v1.flows.supabase")
    def test_get_flow_executions(self, mock_db, client, auth_headers):
        """Test fetching flow execution history."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "exec-1", "flow_name": "financial", "status": "completed"},
        ])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/flows/executions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1


class TestSettingsEndpoints:
    """Test business profile and settings endpoints."""

    @patch("src.api.v1.settings.supabase")
    def test_get_business_profile_empty(self, mock_db, client, auth_headers):
        """Test getting business profile when none exists."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/business-profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["profile"] is None

    @patch("src.api.v1.settings.supabase")
    def test_create_business_profile(self, mock_db, client, auth_headers):
        """Test creating a business profile."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.side_effect = [
            MagicMock(data=[]),  # Check existing
            MagicMock(data=[{
                "business_type": "micro_entrepreneur",
                "tax_regime": "micro",
            }]),  # Insert result
        ]
        mock_db.table.return_value = mock_chain

        response = client.post(
            "/v1/business-profile",
            headers=auth_headers,
            json={
                "account_id": "test-account-123",
                "business_type": "micro_entrepreneur",
                "tax_regime": "micro",
                "declaration_frequency": "quarterly",
                "tva_applicable": False,
            },
        )
        assert response.status_code == 200

    @patch("src.api.v1.settings.supabase")
    def test_get_tax_obligations(self, mock_db, client, auth_headers):
        """Test fetching tax obligations."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "tax-1", "title": "Déclaration CA T1", "status": "pending"},
        ])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/tax-obligations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    @patch("src.api.v1.settings.supabase")
    def test_get_financial_insights(self, mock_db, client, auth_headers):
        """Test fetching financial insights."""
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "i1", "title": "Subscription increase", "severity": "warning"},
        ])
        mock_db.table.return_value = mock_chain

        response = client.get("/v1/financial-insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
