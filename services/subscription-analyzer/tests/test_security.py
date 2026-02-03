"""
Security tests for the subscription-analyzer API.
Tests the security fixes implemented in Option B.
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestCORSSecurity:
    """Tests for CORS configuration security."""
    
    def test_cors_blocks_unknown_origin(self):
        """CORS should not allow requests from unknown origins."""
        from src.main import app
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
        from src.main import app, CORS_ORIGINS
        
        # In dev mode, localhost should be allowed
        assert "http://localhost:3000" in CORS_ORIGINS or os.getenv("ENVIRONMENT") == "production"


class TestAuthSecurity:
    """Tests for authentication security."""
    
    def test_test_key_blocked_in_production(self):
        """Test/demo API keys should be rejected in production."""
        # Save original env
        original_env = os.environ.get("ENVIRONMENT")
        
        try:
            # Set production mode
            os.environ["ENVIRONMENT"] = "production"
            
            # Reload module to pick up new env
            import importlib
            import src.auth.api_key as auth_module
            importlib.reload(auth_module)
            
            from src.main import app
            client = TestClient(app)
            
            headers = {
                "X-API-Key": "sk_test_123",
                "X-Account-ID": "acc_123",
            }
            files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Test,10', 'text/csv')}
            
            response = client.post("/v1/analyses", headers=headers, files=files)
            
            # Should be rejected in production
            assert response.status_code == 403
            assert "production" in response.json().get("detail", "").lower() or response.status_code == 403
            
        finally:
            # Restore original env
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            else:
                os.environ.pop("ENVIRONMENT", None)
    
    def test_demo_key_allowed_in_development(self):
        """Demo API keys should work in development mode."""
        # Save original env
        original_env = os.environ.get("ENVIRONMENT")
        
        try:
            # Set development mode
            os.environ["ENVIRONMENT"] = "development"
            
            # Reload module
            import importlib
            import src.auth.api_key as auth_module
            importlib.reload(auth_module)
            
            from src.main import app
            client = TestClient(app)
            
            with patch("src.api.v1.analyses.supabase") as mock_supabase:
                mock_supabase.storage.from_.return_value.upload.return_value = {"path": "some/path"}
                mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "123-uuid"}]
                
                headers = {
                    "X-API-Key": "demo-key",
                    "X-Account-ID": "acc_123",
                }
                files = {'file': ('test.csv', b'date,description,amount,currency\n2023-01-01,Netflix,15.99,EUR', 'text/csv')}
                
                response = client.post("/v1/analyses", headers=headers, files=files)
                
                # Should succeed in development
                assert response.status_code == 201
                
        finally:
            # Restore original env
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            else:
                os.environ.pop("ENVIRONMENT", None)


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
            from src.main import app
            client = TestClient(app)
            
            test_api_key = "sk_live_super_secret_key_12345"
            
            headers = {
                "X-API-Key": test_api_key,
                "X-Account-ID": "acc_123",
            }
            files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Test,10', 'text/csv')}
            
            # Make request (will fail auth but should trigger logging)
            response = client.post("/v1/analyses", headers=headers, files=files)
            
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
        from src.main import app
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
        from src.main import app
        client = TestClient(app)
        
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        with patch("src.api.v1.analyses.get_current_account", return_value="acc_123"):
            headers = {
                "X-API-Key": "sk_test_123",
                "X-Account-ID": "acc_123",
            }
            files = {'file': ('large.csv', large_content, 'text/csv')}
            
            response = client.post("/v1/analyses", headers=headers, files=files)
            
            # Should be rejected due to size
            assert response.status_code in [400, 413, 422]
    
    def test_unsupported_file_type_rejected(self):
        """Unsupported file types should be rejected."""
        from src.main import app
        client = TestClient(app)
        
        with patch("src.auth.api_key.get_current_account", return_value="acc_123"):
            headers = {
                "X-API-Key": "sk_test_123",
                "X-Account-ID": "acc_123",
            }
            files = {'file': ('script.exe', b'MZ...', 'application/x-msdownload')}
            
            response = client.post("/v1/analyses", headers=headers, files=files)
            
            # Should be rejected
            assert response.status_code == 400
