@echo off
REM Comprehensive Setup Script for Decentralized IoT Network Project (Windows)
REM This script automates the complete setup process for the entire project

setlocal enabledelayedexpansion
set "CURRENT_DIR=%cd%"

REM Color output helper (Windows 10+)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

REM ========== Check Prerequisites ==========
echo.
echo %BLUE%==== Checking Prerequisites ====%RESET%
echo.

set "MISSING_TOOLS=0"

REM Check Docker
docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%X Docker not found%RESET%
    set /a MISSING_TOOLS=!MISSING_TOOLS!+1
) else (
    echo %GREEN%✓ Docker found%RESET%
)

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%X Python not found%RESET%
    set /a MISSING_TOOLS=!MISSING_TOOLS!+1
) else (
    echo %GREEN%✓ Python found%RESET%
)

REM Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%X Node.js not found%RESET%
    set /a MISSING_TOOLS=!MISSING_TOOLS!+1
) else (
    echo %GREEN%✓ Node.js found%RESET%
)

if !MISSING_TOOLS! gtr 0 (
    echo %RED%Missing !MISSING_TOOLS! required tool(s). Please install before proceeding.%RESET%
    exit /b 1
)

REM ========== Install Python Dependencies ==========
echo.
echo %BLUE%==== Installing Python Dependencies ====%RESET%
echo.

cd backend-services
if exist "requirements.txt" (
    echo %GREEN%✓ Installing backend requirements...%RESET%
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    echo %GREEN%✓ Python dependencies installed%RESET%
) else (
    echo %YELLOW%⚠ requirements.txt not found%RESET%
)
cd ..

REM ========== Install Node Dependencies ==========
echo.
echo %BLUE%==== Installing Node.js Dependencies ====%RESET%
echo.

if exist "web-dashboard" (
    cd web-dashboard
    if exist "package.json" (
        echo %GREEN%✓ Installing web-dashboard dependencies...%RESET%
        call npm install
        echo %GREEN%✓ Web dashboard dependencies installed%RESET%
    )
    cd ..
)

if exist "smart-contracts" (
    cd smart-contracts
    if exist "package.json" (
        echo %GREEN%✓ Installing smart contracts dependencies...%RESET%
        call npm install
        echo %GREEN%✓ Smart contracts dependencies installed%RESET%
    )
    cd ..
)

REM ========== Build Docker Images ==========
echo.
echo %BLUE%==== Building Docker Images ====%RESET%
echo.

echo %GREEN%✓ Building backend Docker image...%RESET%
docker build -t iot-network/backend:latest backend-services/

echo %GREEN%✓ Building frontend Docker image...%RESET%
docker build -t iot-network/frontend:latest web-dashboard/

echo %GREEN%✓ All Docker images built successfully%RESET%

REM ========== Start Services ==========
echo.
echo %BLUE%==== Starting Docker Services ====%RESET%
echo.

if exist "docker-compose.yml" (
    echo %GREEN%✓ Starting services with Docker Compose...%RESET%
    docker-compose up -d
    
    echo %GREEN%✓ Waiting for services to be ready...%RESET%
    timeout /t 10 /nobreak
    
    echo %GREEN%✓ Docker services started%RESET%
    docker-compose ps
) else (
    echo %YELLOW%⚠ docker-compose.yml not found%RESET%
)

REM ========== Setup Monitoring ==========
echo.
echo %BLUE%==== Setting Up Monitoring ====%RESET%
echo.

if exist "monitoring\docker-compose.monitoring.yml" (
    echo %GREEN%✓ Starting monitoring services...%RESET%
    docker-compose -f monitoring\docker-compose.monitoring.yml up -d
    echo %GREEN%✓ Monitoring services started%RESET%
    echo %GREEN%✓ Prometheus: http://localhost:9090%RESET%
    echo %GREEN%✓ Grafana: http://localhost:3001 ^(admin/admin123^)%RESET%
) else (
    echo %YELLOW%⚠ monitoring\docker-compose.monitoring.yml not found%RESET%
)

REM ========== Validate Project ==========
echo.
echo %BLUE%==== Validating Project Structure ====%RESET%
echo.

if exist "validate_project.py" (
    python validate_project.py
) else (
    echo %YELLOW%⚠ validate_project.py not found%RESET%
)

REM ========== Deployment Information ==========
echo.
echo %BLUE%==== Deployment Information ====%RESET%
echo.

echo %GREEN%✓ Backend API: http://localhost:8000%RESET%
echo %GREEN%✓ Frontend Web Dashboard: http://localhost:3000%RESET%
echo %GREEN%✓ Prometheus: http://localhost:9090%RESET%
echo %GREEN%✓ Grafana: http://localhost:3001 ^(admin/admin123^)%RESET%
echo %GREEN%✓ Mosquitto MQTT: localhost:1883%RESET%

REM ========== Setup Complete ==========
echo.
echo %BLUE%==== Setup Complete! ====%RESET%
echo %GREEN%✓ All components have been set up successfully!%RESET%
echo.

endlocal
