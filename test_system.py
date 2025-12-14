#!/usr/bin/env python3
"""
Comprehensive Test Suite for Decentralized IoT Network
Tests all components: Backend, Smart Contracts, Database, MQTT
"""

import asyncio
import json
import requests
import psycopg2
import paho.mqtt.client as mqtt
from web3 import Web3
import time
import sys

# Configuration
API_BASE = "http://localhost:8000"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "iot_network"
}
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
BLOCKCHAIN_URL = "http://localhost:8545"

class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, name, success, message=""):
        self.tests.append({"name": name, "success": success, "message": message})
        if success:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            print(f"❌ {name}: {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print("❌ Failed tests:")
            for test in self.tests:
                if not test["success"]:
                    print(f"   - {test['name']}: {test['message']}")

def test_api_health(results):
    """Test API health endpoint"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        results.add_result("API Health Check", response.status_code == 200)
    except Exception as e:
        results.add_result("API Health Check", False, str(e))

def test_database_connection(results):
    """Test PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        results.add_result("Database Connection", True)
    except Exception as e:
        results.add_result("Database Connection", False, str(e))

def test_user_registration(results):
    """Test user registration and authentication"""
    try:
        # Register test user
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        response = requests.post(f"{API_BASE}/api/v1/auth/register", json=user_data)
        
        if response.status_code in [200, 409]:  # 409 if user already exists
            results.add_result("User Registration", True)
        else:
            results.add_result("User Registration", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("User Registration", False, str(e))

def test_mqtt_connection(results):
    """Test MQTT broker connection"""
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.disconnect()
        results.add_result("MQTT Connection", True)
    except Exception as e:
        results.add_result("MQTT Connection", False, str(e))

def test_blockchain_connection(results):
    """Test blockchain connection"""
    try:
        w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))
        is_connected = w3.isConnected()
        results.add_result("Blockchain Connection", is_connected)
    except Exception as e:
        results.add_result("Blockchain Connection", False, str(e))

def test_device_endpoints(results):
    """Test device-related endpoints"""
    try:
        # First login to get token
        login_data = {
            "username": "test@example.com",
            "password": "testpassword123"
        }
        login_response = requests.post(f"{API_BASE}/api/v1/auth/login", data=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test device registration
            device_data = {
                "device_id": "TEST_DEVICE_001",
                "device_type": "ESP32",
                "location": {"lat": 40.7128, "lng": -74.0060}
            }
            response = requests.post(f"{API_BASE}/api/v1/devices/register", 
                                   json=device_data, headers=headers)
            
            success = response.status_code in [200, 409]  # 409 if device already exists
            results.add_result("Device Registration", success)
            
            # Test device listing
            response = requests.get(f"{API_BASE}/api/v1/devices/me", headers=headers)
            results.add_result("Device Listing", response.status_code == 200)
        else:
            results.add_result("Device Endpoints", False, "Login failed")
    except Exception as e:
        results.add_result("Device Endpoints", False, str(e))

def test_websocket_connection(results):
    """Test WebSocket connection"""
    try:
        import websocket
        ws_url = "ws://localhost:8000/ws/dashboard"
        ws = websocket.create_connection(ws_url)
        ws.close()
        results.add_result("WebSocket Connection", True)
    except Exception as e:
        results.add_result("WebSocket Connection", False, str(e))

def test_monitoring_endpoints(results):
    """Test monitoring and metrics endpoints"""
    try:
        # Test Prometheus metrics
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        results.add_result("Prometheus Health", response.status_code == 200)
        
        # Test Grafana
        response = requests.get("http://localhost:3001/api/health", timeout=5)
        results.add_result("Grafana Health", response.status_code == 200)
    except Exception as e:
        results.add_result("Monitoring Services", False, str(e))

def main():
    print("🧪 Starting Decentralized IoT Network Test Suite\n")
    
    results = TestResults()
    
    # Run all tests
    test_api_health(results)
    test_database_connection(results)
    test_mqtt_connection(results)
    test_blockchain_connection(results)
    test_user_registration(results)
    test_device_endpoints(results)
    test_websocket_connection(results)
    test_monitoring_endpoints(results)
    
    # Print summary
    results.summary()
    
    # Exit with error code if any tests failed
    if results.failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
