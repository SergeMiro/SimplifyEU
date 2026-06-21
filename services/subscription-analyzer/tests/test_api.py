import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.db.session import get_db

client = TestClient(app)


def _override_db(session):
    """Install a get_db override that yields the given (mock) session."""
    def _dep():
        yield session
    app.dependency_overrides[get_db] = _dep


def _clear_overrides():
    app.dependency_overrides.clear()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data  # New: includes environment info


def test_upload_analysis_csv_unauthorized():
    # Attempt without headers
    files = {'file': ('test.csv', b'date,desc,amount\n2023-01-01,Netflix,10', 'text/csv')}
    response = client.post("/v1/analyses", files=files)
    # Depending on implementation, might be 403 or 422 (validation error for missing header)
    assert response.status_code in [401, 403, 422]


def test_upload_analysis_csv_mocked():
    # Mock the DB session + local file write to test the controller logic.
    session = MagicMock()
    account_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # db.add(analysis) assigns the row; emulate the DB-side id by stamping it
    # on the object the route created.
    def _add(obj):
        obj.id = uuid.uuid4()
    session.add.side_effect = _add

    _override_db(session)
    try:
        with patch("src.api.v1.analyses.open", create=True), \
             patch("src.api.v1.analyses.os.makedirs"):
            headers = {
                "X-API-Key": "sk_test_123",  # Uses dev override logic
                "X-Account-ID": account_id,
                "X-User-ID": user_id,
            }
            files = {'file': ('test.csv', b'date,description,amount,currency\n2023-01-01,Netflix,15.99,EUR', 'text/csv')}

            response = client.post("/v1/analyses", headers=headers, files=files)

            if response.status_code != 201:
                print(response.json())

            assert response.status_code == 201
            data = response.json()
            assert "analysis_id" in data
            assert data["status"] == "pending"
    finally:
        _clear_overrides()
