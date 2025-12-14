# Decentralized IoT Network - Complete Deployment Script
# This script sets up the entire project environment

Write-Host "🚀 Starting Decentralized IoT Network Deployment" -ForegroundColor Green

# Create virtual environment for Python backend
Write-Host "📦 Setting up Python backend environment..." -ForegroundColor Yellow
cd backend-services
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..

# Install Node.js dependencies for smart contracts
Write-Host "🔗 Installing smart contract dependencies..." -ForegroundColor Yellow
cd smart-contracts
npm install
cd ..

# Install Node.js dependencies for web dashboard
Write-Host "🌐 Installing web dashboard dependencies..." -ForegroundColor Yellow
cd web-dashboard
npm install
cd ..

# Start Docker services
Write-Host "🐳 Starting Docker services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Services Status:"
Write-Host "   📊 Monitoring: http://localhost:3001 (Grafana)"
Write-Host "   🔧 Backend API: http://localhost:8000"
Write-Host "   🌐 Web Dashboard: http://localhost:3000"
Write-Host "   📊 Prometheus: http://localhost:9090"
Write-Host "   💾 PostgreSQL: localhost:5432"
Write-Host "   📡 MQTT Broker: localhost:1883"
Write-Host ""
Write-Host "🔑 Default Credentials:"
Write-Host "   Grafana: admin / admin123"
Write-Host "   PostgreSQL: postgres / postgres"
Write-Host ""
Write-Host "🚀 To start development servers:"
Write-Host "   Backend: cd backend-services && .\venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload"
Write-Host "   Frontend: cd web-dashboard && npm run dev"
Write-Host "   Hardhat: cd smart-contracts && npx hardhat node"
Write-Host ""
Write-Host "📚 Check README.md for detailed documentation"
