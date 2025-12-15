from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_devices_unauthorized():
    response = client.get("/api/v1/devices")
    # Should fail without auth token
    assert response.status_code in [401, 403]

def test_staking_stats():
    response = client.get("/api/v1/staking/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_staked" in data
    assert "apy" in data

def test_governance_proposals():
    response = client.get("/api/v1/governance/proposals")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
