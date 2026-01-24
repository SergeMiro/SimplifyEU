import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

@patch("src.api.v1.analyses.supabase")
def test_create_analysis_no_auth(mock_supabase):
    # Should fail without headers
    # Provide file to avoid 422 validation error
    file_content = b"test"
    files = {"file": ("test.csv", file_content, "text/csv")}
    # Provide X-User-ID to avoid 422 validation error for missing header
    headers = {"X-User-ID": "user1"}
    response = client.post("/v1/analyses", files=files, headers=headers)
    assert response.status_code in [401, 422]

@patch("src.api.v1.analyses.supabase")
def test_create_analysis_success(mock_supabase):
    # Mock upload
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.get_public_url.return_value = "http://mock.url/file.csv"

    # Mock db insert
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "123"}]

    file_content = b"Date,Desc,Amount\n2023-01-01,Test,-10"
    files = {"file": ("test.csv", file_content, "text/csv")}
    headers = {
        "X-API-Key": "demo-key",
        "X-Account-ID": "acc-123",
        "X-User-ID": "user-123"
    }

    response = client.post("/v1/analyses", files=files, headers=headers)
    assert response.status_code == 201
    assert response.json()["analysis_id"] == "123"
    assert response.json()["status"] == "pending"
