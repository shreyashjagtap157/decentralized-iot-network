#!/usr/bin/env python3
"""
Project Completeness Checker
Validates that all required files and configurations exist for the Decentralized IoT Network project
"""

import os
import json
import subprocess
from pathlib import Path

def check_file_exists(file_path, description=""):
    """Check if a file exists and return result"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description or file_path}")
    return exists

def check_directory_exists(dir_path, description=""):
    """Check if a directory exists and return result"""
    exists = os.path.isdir(dir_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description or dir_path}")
    return exists

def check_project_structure():
    """Check the overall project structure"""
    print("🏗️  PROJECT STRUCTURE")
    print("-" * 40)
    
    base_dirs = [
        ("device-firmware", "ESP32 IoT Device Code"),
        ("backend-services", "FastAPI Python Backend"),
        ("mobile-app", "Flutter Mobile Application"),
        ("web-dashboard", "Next.js Web Dashboard"),
        ("smart-contracts", "Solidity Blockchain Contracts"),
        ("monitoring", "Prometheus & Grafana Setup"),
        ("infrastructure", "AWS Terraform & Kubernetes"),
        ("mosquitto", "MQTT Broker Configuration")
    ]
    
    all_exist = True
    for dir_name, description in base_dirs:
        exists = check_directory_exists(dir_name, f"{description}")
        all_exist = all_exist and exists
    
    return all_exist

def check_configuration_files():
    """Check essential configuration files"""
    print("\n⚙️  CONFIGURATION FILES")
    print("-" * 40)
    
    config_files = [
        ("docker-compose.yml", "Docker Compose Configuration"),
        ("README.md", "Project Documentation"),
        ("LICENSE", "Project License"),
        (".gitignore", "Git Ignore Rules"),
        ("backend-services/.env", "Backend Environment Variables"),
        ("backend-services/requirements.txt", "Python Dependencies"),
        ("web-dashboard/package.json", "Web Dashboard Dependencies"),
        ("web-dashboard/tsconfig.json", "TypeScript Configuration"),
        ("web-dashboard/.eslintrc.json", "ESLint Configuration"),
        ("smart-contracts/package.json", "Smart Contract Dependencies"),
        ("smart-contracts/hardhat.config.js", "Hardhat Configuration"),
        ("smart-contracts/tsconfig.json", "Smart Contract TypeScript Config"),
        ("mobile-app/pubspec.yaml", "Flutter Dependencies"),
        ("mobile-app/analysis_options.yaml", "Flutter Analysis Options"),
        ("infrastructure/main.tf", "Terraform Main Configuration"),
        ("monitoring/docker-compose.monitoring.yml", "Monitoring Stack")
    ]
    
    all_exist = True
    for file_path, description in config_files:
        exists = check_file_exists(file_path, f"{description}")
        all_exist = all_exist and exists
    
    return all_exist

def check_source_code():
    """Check essential source code files"""
    print("\n💻 SOURCE CODE FILES")
    print("-" * 40)
    
    source_files = [
        # Backend
        ("backend-services/app/main.py", "FastAPI Main Application"),
        ("backend-services/app/models.py", "Database Models"),
        ("backend-services/app/auth.py", "Authentication Module"),
        ("backend-services/app/api/v1/users.py", "Users API"),
        ("backend-services/app/api/v1/devices.py", "Devices API"),
        
        # Web Dashboard
        ("web-dashboard/pages/index.tsx", "Web Dashboard Main Page"),
        ("web-dashboard/components/Dashboard.tsx", "Dashboard Component"),
        ("web-dashboard/components/LoginPage.tsx", "Login Component"),
        ("web-dashboard/contexts/AuthContext.tsx", "Authentication Context"),
        ("web-dashboard/lib/api.ts", "API Client Configuration"),
        ("web-dashboard/lib/web3.ts", "Web3 Integration"),
        
        # Smart Contracts
        ("smart-contracts/contracts/NetworkCompensation.sol", "Network Compensation Contract"),
        ("smart-contracts/scripts/deploy.ts", "Deployment Script"),
        ("smart-contracts/test/NetworkCompensation.test.ts", "Contract Tests"),
        
        # Mobile App
        ("mobile-app/lib/main.dart", "Flutter Main Application"),
        ("mobile-app/lib/screens/dashboard_screen.dart", "Mobile Dashboard"),
        ("mobile-app/lib/screens/login_screen.dart", "Mobile Login"),
        ("mobile-app/lib/services/auth_service.dart", "Mobile Auth Service"),
        ("mobile-app/lib/services/websocket_service.dart", "Mobile WebSocket Service"),
        
        # Device Firmware
        ("device-firmware/src/main.cpp", "ESP32 Main Code"),
        ("device-firmware/platformio.ini", "PlatformIO Configuration"),
        
        # Infrastructure
        ("infrastructure/variables.tf", "Terraform Variables"),
        ("infrastructure/outputs.tf", "Terraform Outputs"),
        ("infrastructure/iam.tf", "AWS IAM Configuration")
    ]
    
    all_exist = True
    for file_path, description in source_files:
        exists = check_file_exists(file_path, f"{description}")
        all_exist = all_exist and exists
    
    return all_exist

def check_package_files():
    """Validate package.json and other dependency files"""
    print("\n📦 DEPENDENCY VALIDATION")
    print("-" * 40)
    
    # Check Web Dashboard package.json
    web_package_path = "web-dashboard/package.json"
    if os.path.exists(web_package_path):
        try:
            with open(web_package_path, 'r') as f:
                web_package = json.load(f)
            
            required_web_deps = [
                'next', 'react', 'react-dom', '@mui/material', 
                'axios', 'react-chartjs-2', 'chart.js', 
                'react-use-websocket', 'web3'
            ]
            
            missing_deps = []
            dependencies = {**web_package.get('dependencies', {}), **web_package.get('devDependencies', {})}
            
            for dep in required_web_deps:
                if dep not in dependencies:
                    missing_deps.append(dep)
            
            if not missing_deps:
                print("✅ Web Dashboard - All required dependencies present")
            else:
                print(f"❌ Web Dashboard - Missing dependencies: {', '.join(missing_deps)}")
                
        except Exception as e:
            print(f"❌ Web Dashboard - Error reading package.json: {e}")
    
    # Check Smart Contracts package.json
    contracts_package_path = "smart-contracts/package.json"
    if os.path.exists(contracts_package_path):
        try:
            with open(contracts_package_path, 'r') as f:
                contracts_package = json.load(f)
            
            required_contract_deps = [
                'hardhat', '@openzeppelin/contracts', 
                'ethers', '@nomiclabs/hardhat-ethers'
            ]
            
            missing_deps = []
            dependencies = {**contracts_package.get('dependencies', {}), **contracts_package.get('devDependencies', {})}
            
            for dep in required_contract_deps:
                if dep not in dependencies:
                    missing_deps.append(dep)
            
            if not missing_deps:
                print("✅ Smart Contracts - All required dependencies present")
            else:
                print(f"❌ Smart Contracts - Missing dependencies: {', '.join(missing_deps)}")
                
        except Exception as e:
            print(f"❌ Smart Contracts - Error reading package.json: {e}")

def main():
    """Main validation function"""
    print("🔍 DECENTRALIZED IoT NETWORK - PROJECT COMPLETENESS CHECK")
    print("=" * 60)
    
    os.chdir(Path(__file__).parent)
    
    structure_ok = check_project_structure()
    config_ok = check_configuration_files()
    source_ok = check_source_code()
    
    print("\n📊 SUMMARY")
    print("-" * 40)
    
    check_package_files()
    
    if structure_ok and config_ok and source_ok:
        print("\n🎉 PROJECT IS COMPLETE!")
        print("✅ All required files and directories exist")
        print("🚀 Ready for deployment and development")
        return True
    else:
        print("\n⚠️  PROJECT INCOMPLETE")
        print("❌ Some required files or directories are missing")
        print("📋 Please check the items marked with ❌ above")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
