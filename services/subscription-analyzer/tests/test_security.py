"""
Security tests for the subscription-analyzer API.
"""
import os
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.db.session import get_db


def _override_db(session):
    def _dep():
        yield session
    app.dependency_overrides[get_db] = _dep


def _clear_overrides():
    app.dependency_overrides.clear()


class TestCORSSecurity:
    """Tests for CORS configuration security."""

    def test_cors_blocks_unknown_origin(self):
        """CORS should not allow requests from unknown origins."""
        client = TestClient(app)

        # Request from malicious origin
        response = client.options(
            "/health",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            }
        )

        # Should not include allow-origin for unknown origins
        cors_header = response.headers.get("Access-Control-Allow-Origin")
        assert cors_header != "https://malicious-site.com"
        assert cors_header != "*"

    def test_cors_allows_localhost_in_dev(self):
        """CORS should allow localhost in development."""
        from src.main import CORS_ORIGINS

        # In dev mode, localhost should be allowed
        assert "http://localhost:3000" in CORS_ORIGINS or os.getenv("ENVIRONMENT") == "production"


class TestAuthSecurity:
    """Tests for authentication on /v1 routes."""

    def test_missing_auth_headers(self):
        """Request without any auth headers should fail."""
        files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Test,10', 'text/csv')}
        response = client_post(files)
        assert response.status_code in (401, 403, 422)

    def test_missing_account_id(self):
        """Test key without X-Account-ID should fail validation."""
        client = TestClient(app)
        files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Test,10', 'text/csv')}
        response = client.post(
            "/v1/analyses",
            headers={"X-API-Key": "sk_test_123"},
            files=files,
        )
        assert response.status_code == 422

    def test_demo_key_allowed_in_development(self):
        """Demo API keys should work in development mode (with DB overridden)."""
        client = TestClient(app)

        session = MagicMock()
        account_id = str(uuid.uuid4())

        def _add(obj):
            obj.id = uuid.uuid4()
        session.add.side_effect = _add

        _override_db(session)
        try:
            with patch("src.api.v1.analyses.open", create=True), \
                 patch("src.api.v1.analyses.os.makedirs"):
                headers = {
                    "X-API-Key": "demo-key",
                    "X-Account-ID": account_id,
                    "X-User-ID": str(uuid.uuid4()),
                }
                files = {'file': ('test.csv', b'date,description,amount,currency\n2023-01-01,Netflix,15.99,EUR', 'text/csv')}

                response = client.post("/v1/analyses", headers=headers, files=files)
                assert response.status_code == 201
        finally:
            _clear_overrides()


def client_post(files):
    """Helper: POST /v1/analyses with no auth headers."""
    client = TestClient(app)
    return client.post("/v1/analyses", files=files)


class TestAPIKeyLogging:
    """Tests to ensure API keys are not logged."""

    def test_no_api_key_in_logs(self):
        """API keys should never appear in logs."""
        import logging
        from io import StringIO

        # Capture logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)

        logger = logging.getLogger("src.auth.api_key")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            client = TestClient(app)

            test_api_key = "sk_live_super_secret_key_12345"

            headers = {
                "X-API-Key": test_api_key,
                "X-Account-ID": "acc_123",
            }
            files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Test,10', 'text/csv')}

            # Make request (will fail auth but should trigger logging)
            client.post("/v1/analyses", headers=headers, files=files)

            # Get captured logs
            log_output = log_capture.getvalue()

            # API key should NOT appear in logs (even partially)
            assert test_api_key not in log_output
            assert "super_secret" not in log_output
            assert "sk_live" not in log_output or "Test/demo key" in log_output

        finally:
            logger.removeHandler(handler)


class TestSecurityEndpoints:
    """Tests for security info endpoint."""

    def test_security_info_endpoint(self):
        """Security info endpoint should return non-sensitive configuration."""
        client = TestClient(app)

        response = client.get("/security-info")
        assert response.status_code == 200

        data = response.json()
        assert "cors_origins_configured" in data
        assert "is_production" in data
        assert "rate_limiting_enabled" in data

        # Should not include sensitive data
        assert "api_key" not in str(data).lower()
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()


class TestRateLimiting:
    """Tests for rate limiting configuration."""

    def test_rate_limiter_configured(self):
        """Rate limiter should be configured in the app."""
        from src.main import app, limiter

        # Limiter should exist
        assert limiter is not None

        # App should have limiter in state
        assert hasattr(app.state, "limiter")


class TestInputValidation:
    """Tests for input validation security."""

    def test_file_size_limit(self):
        """Large files should be rejected."""
        client = TestClient(app)

        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB

        session = MagicMock()
        _override_db(session)
        try:
            headers = {
                "X-API-Key": "sk_test_123",
                "X-Account-ID": str(uuid.uuid4()),
            }
            files = {'file': ('large.csv', large_content, 'text/csv')}

            response = client.post("/v1/analyses", headers=headers, files=files)

            # Should be rejected due to size
            assert response.status_code in [400, 413, 422]
        finally:
            _clear_overrides()

    def test_unsupported_file_type_rejected(self):
        """Unsupported file types should be rejected."""
        client = TestClient(app)

        session = MagicMock()
        _override_db(session)
        try:
            headers = {
                "X-API-Key": "sk_test_123",
                "X-Account-ID": str(uuid.uuid4()),
            }
            files = {'file': ('script.exe', b'MZ...', 'application/x-msdownload')}

            response = client.post("/v1/analyses", headers=headers, files=files)

            # Should be rejected
            assert response.status_code == 400
        finally:
            _clear_overrides()
