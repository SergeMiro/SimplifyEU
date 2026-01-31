from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_analysis_csv_unauthorized():
    # Attempt without headers
    files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Netflix,10', 'text/csv')}
    response = client.post("/v1/analyses", files=files)
    # Depending on implementation, might be 403 or 422 (validation error for missing header)
    assert response.status_code in [401, 403, 422]

def test_upload_analysis_csv_mocked():
    # Mock Supabase authentication/insertion to test the controller logic
    with patch("src.api.v1.analyses.supabase") as mock_supabase:
        # Mock file upload response
        mock_supabase.storage.from_.return_value.upload.return_value = {"path": "some/path"}
        # Mock db insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "123-uuid"}]
        
        headers = {
            "X-API-Key": "sk_test_123", # Uses dev override logic
            "X-Account-ID": "acc_123",
            "X-User-ID": "user_123"
        }
        files = {'file': ('test.csv', b'date,description,amount,currency\n2023-01-01,Netflix,15.99,EUR', 'text/csv')}
        
        response = client.post("/v1/analyses", headers=headers, files=files)
        
        # We expect success if auth passes and mocks work
        # Note: If real supabase client tries to connect in dependency injection, this might fail without deeper mocking.
        # But for now, let's see if 201 is returned.
        if response.status_code != 201:
            print(response.json())
            
        assert response.status_code == 201
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "pending"
