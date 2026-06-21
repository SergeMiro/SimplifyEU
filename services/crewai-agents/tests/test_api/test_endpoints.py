"""Tests for the FastAPI endpoints (SQLAlchemy session layer)."""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.db.session import get_db


@pytest.fixture
def client():
    """Create a test client for the app."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Standard auth headers for test requests.

    `sk_test_*` triggers the non-production dev bypass in require_jwt /
    get_current_account, so no real JWT/DB lookup is needed.
    """
    return {
        "X-API-Key": "sk_test_123",
        "X-Account-ID": "test-account-123",
    }


def _scalars(values):
    """Mock a db.scalars(...) result with .all()/.first()."""
    res = MagicMock()
    res.all.return_value = list(values)
    res.first.return_value = values[0] if values else None
    return res


def _override_db(session):
    """Install a get_db override that yields the given (mock) session."""
    def _dep():
        yield session
    app.dependency_overrides[get_db] = _dep


def _clear_overrides():
    app.dependency_overrides.clear()


def _agent_setting(agent_type="financial_assistant", status="disabled"):
    s = MagicMock()
    s.id = uuid.uuid4()
    s.account_id = "test-account-123"
    s.agent_type = agent_type
    s.status = status
    s.notification_channels = ["in_app"]
    s.config = {}
    s.created_at = None
    s.updated_at = None
    return s


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

    def test_list_agents_creates_defaults(self, client, auth_headers):
        """Test that listing agents creates defaults if none exist."""
        session = MagicMock()
        # First scalars() -> empty, second (after insert) -> two defaults
        session.scalars.side_effect = [
            _scalars([]),
            _scalars([
                _agent_setting("financial_assistant"),
                _agent_setting("tax_assistant"),
            ]),
        ]
        _override_db(session)
        try:
            response = client.get("/v1/agents", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
        finally:
            _clear_overrides()

    def test_get_agent_setting(self, client, auth_headers):
        """Test getting a specific agent's settings."""
        session = MagicMock()
        session.scalars.return_value = _scalars([
            _agent_setting("financial_assistant", status="enabled"),
        ])
        _override_db(session)
        try:
            response = client.get("/v1/agents/financial_assistant", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "enabled"
        finally:
            _clear_overrides()

    def test_toggle_agent_enable(self, client, auth_headers):
        """Test enabling an agent."""
        session = MagicMock()
        session.scalars.return_value = _scalars([
            _agent_setting("financial_assistant", status="disabled"),
        ])
        _override_db(session)
        try:
            response = client.post(
                "/v1/agents/financial_assistant/toggle",
                headers=auth_headers,
                json={"status": "enabled"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "enabled"
        finally:
            _clear_overrides()

    def test_toggle_agent_disable(self, client, auth_headers):
        """Test disabling an agent (creates row when missing)."""
        session = MagicMock()
        session.scalars.return_value = _scalars([])  # none exists -> create
        _override_db(session)
        try:
            response = client.post(
                "/v1/agents/tax_assistant/toggle",
                headers=auth_headers,
                json={"status": "disabled"},
            )
            assert response.status_code == 200
        finally:
            _clear_overrides()

    def test_get_notifications(self, client, auth_headers):
        """Test fetching notifications."""
        notif = MagicMock()
        notif.id = uuid.uuid4()
        notif.account_id = "test-account-123"
        notif.title = "Anomaly found"
        notif.message = "msg"
        notif.notification_type = "warning"
        notif.agent_type = None
        notif.action_url = None
        notif.read = False
        notif.created_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([notif])
        _override_db(session)
        try:
            response = client.get("/v1/notifications", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
        finally:
            _clear_overrides()

    def test_mark_notification_read(self, client, auth_headers):
        """Test marking a notification as read."""
        notif = MagicMock()
        notif.read = False

        session = MagicMock()
        session.scalars.return_value = _scalars([notif])
        _override_db(session)
        try:
            nid = str(uuid.uuid4())
            response = client.patch(f"/v1/notifications/{nid}/read", headers=auth_headers)
            assert response.status_code == 200
        finally:
            _clear_overrides()


class TestFlowEndpoints:
    """Test flow management and trigger endpoints."""

    @patch("src.api.v1.flows._is_agent_enabled")
    def test_list_flows(self, mock_enabled, client, auth_headers):
        """Test listing available flows."""
        mock_enabled.return_value = True

        session = MagicMock()
        _override_db(session)
        try:
            response = client.get("/v1/flows", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            flow_names = [f["name"] for f in data["flows"]]
            assert "financial" in flow_names
            assert "tax" in flow_names
            assert "document" in flow_names
            assert "client" in flow_names
            assert "operations" in flow_names
        finally:
            _clear_overrides()

    @patch("src.api.v1.flows._is_agent_enabled")
    def test_trigger_flow_agent_disabled(self, mock_enabled, client, auth_headers):
        """Test that triggering a flow fails when agent is disabled."""
        mock_enabled.return_value = False

        session = MagicMock()
        _override_db(session)
        try:
            response = client.post(
                "/v1/flows/financial/trigger",
                headers=auth_headers,
                json={"flow_name": "financial", "trigger_data": {}},
            )
            assert response.status_code == 403
        finally:
            _clear_overrides()

    def test_trigger_nonexistent_flow(self, client, auth_headers):
        """Test triggering a flow that doesn't exist."""
        session = MagicMock()
        _override_db(session)
        try:
            response = client.post(
                "/v1/flows/nonexistent/trigger",
                headers=auth_headers,
            )
            assert response.status_code == 404
        finally:
            _clear_overrides()

    @patch("src.api.v1.flows._is_agent_enabled")
    def test_trigger_flow_success(self, mock_enabled, client, auth_headers):
        """Test successfully triggering a flow (background task not executed)."""
        mock_enabled.return_value = True

        session = MagicMock()
        _override_db(session)
        try:
            response = client.post(
                "/v1/flows/financial/trigger",
                headers=auth_headers,
                json={"flow_name": "financial", "trigger_data": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "execution_id" in data
        finally:
            _clear_overrides()

    def test_get_flow_executions(self, client, auth_headers):
        """Test fetching flow execution history."""
        log = MagicMock()
        log.id = uuid.uuid4()
        log.account_id = "test-account-123"
        log.agent_type = "financial_assistant"
        log.flow_name = "financial"
        log.trigger = "manual"
        log.status = "completed"
        log.input_data = {}
        log.output_data = {}
        log.error_message = None
        log.started_at = None
        log.completed_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([log])
        _override_db(session)
        try:
            response = client.get("/v1/flows/executions", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
        finally:
            _clear_overrides()


class TestSettingsEndpoints:
    """Test business profile and settings endpoints."""

    def test_get_business_profile_empty(self, client, auth_headers):
        """Test getting business profile when none exists."""
        session = MagicMock()
        session.scalars.return_value = _scalars([])
        _override_db(session)
        try:
            response = client.get("/v1/business-profile", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["profile"] is None
        finally:
            _clear_overrides()

    def test_create_business_profile(self, client, auth_headers):
        """Test creating a business profile."""
        created = MagicMock()
        created.id = uuid.uuid4()
        created.account_id = "test-account-123"
        created.business_type = "micro_entrepreneur"
        created.tax_regime = "micro"
        created.declaration_frequency = "quarterly"
        created.tva_applicable = False
        created.siret = None
        created.created_at = None
        created.updated_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([])  # none exists -> insert
        _override_db(session)
        try:
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
        finally:
            _clear_overrides()

    def test_get_tax_obligations(self, client, auth_headers):
        """Test fetching tax obligations."""
        ob = MagicMock()
        ob.id = uuid.uuid4()
        ob.account_id = "test-account-123"
        ob.obligation_type = "declaration_ca"
        ob.title = "Déclaration CA T1"
        ob.description = None
        ob.deadline = None
        ob.status = "pending"
        ob.draft_data = None
        ob.service_url = None
        ob.created_at = None
        ob.updated_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([ob])
        _override_db(session)
        try:
            response = client.get("/v1/tax-obligations", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
        finally:
            _clear_overrides()

    def test_get_financial_insights(self, client, auth_headers):
        """Test fetching financial insights."""
        ins = MagicMock()
        ins.id = uuid.uuid4()
        ins.account_id = "test-account-123"
        ins.insight_type = "subscription"
        ins.title = "Subscription increase"
        ins.description = "desc"
        ins.severity = "warning"
        ins.data = {}
        ins.acknowledged = False
        ins.created_at = None

        session = MagicMock()
        session.scalars.return_value = _scalars([ins])
        _override_db(session)
        try:
            response = client.get("/v1/financial-insights", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
        finally:
            _clear_overrides()
