import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch, MagicMock
import os

# Set test environment variable before importing app
os.environ["PYTEST_CURRENT_TEST"] = "true"

from app.main import app
from app.db.models import get_db, Base
from app.models import User, Device, DataEntry

# Mock rate limiter since we don't have it implemented
class MockLimiter:
    def limit(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

limiter = MockLimiter()

# Mock cache manager
class CacheManager:
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value, ttl=300):
        self._cache[key] = value
        return True
    
    def cached(self, prefix="", ttl=300):
        def decorator(func):
            return func
        return decorator

# Mock create_access_token
def create_access_token(data: dict, expires_delta=None):
    return "mock_test_token"


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Mock Redis for testing
@pytest.fixture(scope="module")
def mock_redis():
    with patch('redis.Redis') as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        yield mock_client

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user():
    return {
        "username": "testuser",
        "email": "test@example.com",
            "password": "testpass123"  # Ensure password is well under 72 characters
    }

@pytest.fixture
def test_device():
    return {
        "device_id": "ESP32_TEST_001",
        "name": "Test Sensor",
        "device_type": "temperature",
        "location": "Test Lab"
    }

class TestAuthentication:
    def test_register_user(self, client, test_user):
        response = client.post("/api/v1/users/", json=test_user)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]
        assert "id" in data

    def test_register_duplicate_user(self, client, test_user):
        # Register user first time
        client.post("/api/v1/users/", json=test_user)
        
        # Try to register same user again
        response = client.post("/api/v1/users/", json=test_user)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_login_user(self, client, test_user):
        # Register user first
        client.post("/api/v1/users/", json=test_user)
        
        # Login
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        response = client.post("/users/token", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        response = client.post("/users/token", data=login_data)
        assert response.status_code == 401

    def test_protected_route_without_token(self, client):
        response = client.get("/user/profile")
        assert response.status_code == 401

    def test_protected_route_with_token(self, client, test_user):
        # Register and login
        client.post("/api/v1/users/", json=test_user)
        login_response = client.post("/users/token", data={
            "username": test_user["username"],
            "password": test_user["password"]
        })
        token = login_response.json()["access_token"]
        
        # Access protected route
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/user/profile", headers=headers)
        assert response.status_code == 200

    def test_register_user_invalid_email(self, client):
        invalid_user = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "testpassword123"
        }
        response = client.post("/api/v1/users/", json=invalid_user)
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_login_user_inactive_account(self, client, test_user):
        # Register user and deactivate account
        client.post("/api/v1/users/", json=test_user)
        db_session = TestingSessionLocal()
        user = db_session.query(User).filter_by(username=test_user["username"]).first()
        user.is_active = False
        db_session.commit()
        db_session.close()

        # Attempt login
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        response = client.post("/users/token", data=login_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

class TestDeviceManagement:
    def setup_authenticated_client(self, client, test_user):
        client.post("/auth/register", json=test_user)
        login_response = client.post("/auth/login", data={
            "username": test_user["username"],
            "password": test_user["password"]
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_register_device(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        response = client.post("/devices/register", json=test_device, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == test_device["device_id"]
        assert data["name"] == test_device["name"]

    def test_get_user_devices(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device
        client.post("/devices/register", json=test_device, headers=headers)
        
        # Get devices
        response = client.get("/devices/", headers=headers)
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["device_id"] == test_device["device_id"]

    def test_get_device_details(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device
        client.post("/devices/register", json=test_device, headers=headers)
        
        # Get device details
        response = client.get(f"/devices/{test_device['device_id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == test_device["device_id"]

    def test_update_device(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device
        client.post("/devices/register", json=test_device, headers=headers)
        
        # Update device
        update_data = {"name": "Updated Sensor", "location": "Updated Location"}
        response = client.put(
            f"/devices/{test_device['device_id']}", 
            json=update_data, 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Sensor"
        assert data["location"] == "Updated Location"

    def test_delete_device(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device
        client.post("/devices/register", json=test_device, headers=headers)
        
        # Delete device
        response = client.delete(f"/devices/{test_device['device_id']}", headers=headers)
        assert response.status_code == 204
        
        # Verify device is deleted
        response = client.get(f"/devices/{test_device['device_id']}", headers=headers)
        assert response.status_code == 404

    def test_register_device_missing_fields(self, client, test_user):
        headers = self.setup_authenticated_client(client, test_user)
        incomplete_device = {
            "device_id": "ESP32_TEST_002"
            # Missing name, device_type, and location
        }
        response = client.post("/devices/register", json=incomplete_device, headers=headers)
        assert response.status_code == 422
        assert "detail" in response.json()

class TestDataSubmission:
    def setup_authenticated_client(self, client, test_user):
        client.post("/auth/register", json=test_user)
        login_response = client.post("/auth/login", data={
            "username": test_user["username"],
            "password": test_user["password"]
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_submit_data(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device
        client.post("/devices/register", json=test_device, headers=headers)
        
        # Submit data
        data_entry = {
            "device_id": test_device["device_id"],
            "data_type": "temperature",
            "value": 25.5,
            "quality_score": 95,
            "metadata": {"unit": "celsius", "location": "indoor"}
        }
        
        response = client.post("/data/submit", json=data_entry, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == test_device["device_id"]
        assert data["value"] == 25.5

    def test_get_device_data(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        
        # Register device and submit data
        client.post("/devices/register", json=test_device, headers=headers)
        data_entry = {
            "device_id": test_device["device_id"],
            "data_type": "temperature",
            "value": 25.5,
            "quality_score": 95
        }
        client.post("/data/submit", json=data_entry, headers=headers)
        
        # Get data
        response = client.get(
            f"/data/device/{test_device['device_id']}", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["value"] == 25.5

    def test_submit_data_invalid_device(self, client, test_user):
        headers = self.setup_authenticated_client(client, test_user)
        
        data_entry = {
            "device_id": "NONEXISTENT_DEVICE",
            "data_type": "temperature",
            "value": 25.5,
            "quality_score": 95
        }
        
        response = client.post("/data/submit", json=data_entry, headers=headers)
        assert response.status_code == 404

    def test_submit_data_out_of_range(self, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)

        # Register device
        client.post("/devices/register", json=test_device, headers=headers)

        # Submit out-of-range data
        data_entry = {
            "device_id": test_device["device_id"],
            "data_type": "temperature",
            "value": -9999,  # Unrealistic value
            "quality_score": 95
        }
        response = client.post("/data/submit", json=data_entry, headers=headers)
        assert response.status_code == 400
        assert "out of range" in response.json()["detail"]

class TestEarnings:
    def setup_authenticated_client(self, client, test_user):
        client.post("/auth/register", json=test_user)
        login_response = client.post("/auth/login", data={
            "username": test_user["username"],
            "password": test_user["password"]
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @patch('app.services.blockchain_service.calculate_reward')
    def test_calculate_earnings(self, mock_calculate_reward, client, test_user, test_device):
        headers = self.setup_authenticated_client(client, test_user)
        mock_calculate_reward.return_value = 1000000  # Mock reward in wei
        
        # Register device and submit data
        client.post("/devices/register", json=test_device, headers=headers)
        data_entry = {
            "device_id": test_device["device_id"],
            "data_type": "temperature",
            "value": 25.5,
            "quality_score": 95
        }
        client.post("/data/submit", json=data_entry, headers=headers)
        
        # Get earnings
        response = client.get("/earnings/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_earnings" in data
        assert "earnings_by_device" in data

    def test_earnings_history(self, client, test_user):
        headers = self.setup_authenticated_client(client, test_user)
        
        response = client.get("/earnings/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestRateLimiting:
    def test_rate_limiting_auth(self, client):
        # Make multiple requests quickly to trigger rate limiting
        for i in range(6):  # Exceed the 5/minute limit
            response = client.post("/auth/login", data={
                "username": "test",
                "password": "test"
            })
            if i < 5:
                # First 5 requests should work (though they'll fail auth)
                assert response.status_code in [401, 422]  # Unauthorized or validation error
            else:
                # 6th request should be rate limited
                assert response.status_code == 429

class TestCaching:
    @pytest.fixture
    def cache_manager(self, mock_redis):
        return CacheManager()

    def test_cache_set_and_get(self, cache_manager, mock_redis):
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        # Test cache miss
        result = cache_manager.get("test_key")
        assert result is None
        
        # Test cache set
        cache_manager.set("test_key", {"data": "test"}, ttl=300)
        mock_redis.setex.assert_called_once()

    def test_cache_decorator(self, cache_manager, mock_redis):
        mock_redis.get.return_value = None
        
        @cache_manager.cached(prefix="test", ttl=300)
        def expensive_function(param1, param2):
            return f"result_{param1}_{param2}"
        
        result = expensive_function("a", "b")
        assert result == "result_a_b"

class TestErrorHandling:
    def test_validation_error(self, client):
        # Test with invalid data
        response = client.post("/auth/register", json={
            "username": "",  # Invalid empty username
            "email": "invalid_email",  # Invalid email format
            "password": "123"  # Too short password
        })
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_not_found_error(self, client, test_user):
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/devices/NONEXISTENT_DEVICE", headers=headers)
        assert response.status_code == 401  # Unauthorized due to invalid token

class TestWebSocket:
    @pytest.mark.asyncio
    async def test_websocket_connection(self, client):
        with client.websocket_connect("/ws/device_status") as websocket:
            data = websocket.receive_json()
            assert "type" in data

    @pytest.mark.asyncio
    async def test_websocket_device_updates(self, client):
        with client.websocket_connect("/ws/device_status") as websocket:
            # Simulate device status update
            test_message = {
                "type": "device_status",
                "device_id": "ESP32_001",
                "status": "online"
            }
            websocket.send_json(test_message)
            
            response = websocket.receive_json()
            assert response["type"] == "device_status"

@pytest.fixture(scope="module", autouse=True)
def mock_mqtt_service():
    """Mock MQTT service to avoid real connections during tests."""
    async def mock_connect(*args, **kwargs):
        pass

    async def mock_disconnect(*args, **kwargs):
        pass

    with patch("app.main.mqtt_service.connect", new=mock_connect), \
         patch("app.main.mqtt_service.disconnect", new=mock_disconnect):
        yield

if __name__ == "__main__":
    pytest.main(["-v", __file__])
