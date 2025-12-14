#!/usr/bin/env python3
"""
Project Status Dashboard
Real-time status of all Decentralized IoT Network components
"""

import requests
import psycopg2
import paho.mqtt.client as mqtt
from web3 import Web3
import time
import os
import subprocess
from datetime import datetime

def check_service(name, url, timeout=5):
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=timeout)
        return "🟢 RUNNING" if response.status_code == 200 else "🟡 ISSUES"
    except:
        return "🔴 DOWN"

def check_database():
    """Check PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host="localhost", port=5432, user="postgres", 
            password="postgres", database="iot_network"
        )
        conn.close()
        return "🟢 CONNECTED"
    except:
        return "🔴 DOWN"

def check_mqtt():
    """Check MQTT broker"""
    try:
        client = mqtt.Client()
        client.connect("localhost", 1883, 60)
        client.disconnect()
        return "🟢 CONNECTED"
    except:
        return "🔴 DOWN"

def check_blockchain():
    """Check blockchain connection"""
    try:
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        return "🟢 CONNECTED" if w3.isConnected() else "🔴 DOWN"
    except:
        return "🔴 DOWN"

def check_docker_services():
    """Check Docker Compose services"""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True, text=True, cwd="."
        )
        running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        expected_services = ["postgres", "grafana", "prometheus", "mosquitto"]
        status = {}
        
        for service in expected_services:
            status[service] = "🟢 RUNNING" if service in running_services else "🔴 DOWN"
        
        return status
    except:
        return {service: "❓ UNKNOWN" for service in ["postgres", "grafana", "prometheus", "mosquitto"]}

def get_file_status():
    """Check if all required files exist"""
    required_files = [
        "docker-compose.yml",
        "backend-services/requirements.txt",
        "web-dashboard/package.json",
        "smart-contracts/package.json",
        "device-firmware/platformio.ini",
        "infrastructure/main.tf",
        "README.md"
    ]
    
    status = {}
    for file_path in required_files:
        status[file_path] = "✅ EXISTS" if os.path.exists(file_path) else "❌ MISSING"
    
    return status

def display_dashboard():
    """Display the complete project status"""
    print("=" * 60)
    print("🚀 DECENTRALIZED IoT NETWORK - STATUS DASHBOARD")
    print("=" * 60)
    print(f"📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Core Services
    print("🔧 CORE SERVICES")
    print("-" * 30)
    print(f"Backend API       : {check_service('Backend', 'http://localhost:8000/health')}")
    print(f"Web Dashboard     : {check_service('Frontend', 'http://localhost:3000')}")
    print(f"Database          : {check_database()}")
    print(f"MQTT Broker       : {check_mqtt()}")
    print(f"Blockchain        : {check_blockchain()}")
    print()
    
    # Monitoring Services
    print("📊 MONITORING SERVICES")
    print("-" * 30)
    print(f"Prometheus        : {check_service('Prometheus', 'http://localhost:9090/-/healthy')}")
    print(f"Grafana          : {check_service('Grafana', 'http://localhost:3001/api/health')}")
    print()
    
    # Docker Services
    print("🐳 DOCKER SERVICES")
    print("-" * 30)
    docker_status = check_docker_services()
    for service, status in docker_status.items():
        print(f"{service:<15} : {status}")
    print()
    
    # File Status
    print("📁 PROJECT FILES")
    print("-" * 30)
    file_status = get_file_status()
    for file_path, status in file_status.items():
        print(f"{file_path:<35} : {status}")
    print()
    
    # Service URLs
    print("🌐 SERVICE URLS")
    print("-" * 30)
    print("Backend API Docs  : http://localhost:8000/docs")
    print("Web Dashboard     : http://localhost:3000")
    print("Grafana          : http://localhost:3001 (admin/admin123)")
    print("Prometheus       : http://localhost:9090")
    print("PostgreSQL       : localhost:5432 (postgres/postgres)")
    print("MQTT Broker      : localhost:1883")
    print()
    
    # Quick Actions
    print("⚡ QUICK ACTIONS")
    print("-" * 30)
    print("Start All        : docker-compose up -d")
    print("Stop All         : docker-compose down")
    print("View Logs        : docker-compose logs -f")
    print("Run Tests        : python test_system.py")
    print("Deploy           : .\\deploy.ps1")
    print()

def main():
    """Main dashboard loop"""
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            display_dashboard()
            print("Press Ctrl+C to exit, waiting 10 seconds for refresh...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")

if __name__ == "__main__":
    main()
