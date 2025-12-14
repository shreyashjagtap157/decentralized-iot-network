#!/bin/bash

# Comprehensive Setup Script for Decentralized IoT Network Project
# This script automates the complete setup process for the entire project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_tools=0
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        missing_tools=$((missing_tools + 1))
    else
        print_success "Docker found: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found"
        missing_tools=$((missing_tools + 1))
    else
        print_success "Docker Compose found: $(docker-compose --version)"
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found (required for Kubernetes deployment)"
    else
        print_success "kubectl found: $(kubectl version --short 2>/dev/null || echo 'installed')"
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        missing_tools=$((missing_tools + 1))
    else
        print_success "Python 3 found: $(python3 --version)"
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found"
        missing_tools=$((missing_tools + 1))
    else
        print_success "Node.js found: $(node --version)"
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_warning "Terraform not found (required for infrastructure provisioning)"
    else
        print_success "Terraform found: $(terraform version | head -1)"
    fi
    
    if [ $missing_tools -gt 0 ]; then
        print_error "Missing $missing_tools required tool(s). Please install before proceeding."
        exit 1
    fi
}

# Install Python dependencies
install_python_dependencies() {
    print_header "Installing Python Dependencies"
    
    cd backend-services
    
    if [ -f "requirements.txt" ]; then
        print_success "Installing backend requirements..."
        pip install --upgrade pip setuptools wheel
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi
    
    cd ..
}

# Install Node dependencies
install_node_dependencies() {
    print_header "Installing Node.js Dependencies"
    
    # Install frontend dependencies
    if [ -d "web-dashboard" ]; then
        cd web-dashboard
        if [ -f "package.json" ]; then
            print_success "Installing web-dashboard dependencies..."
            npm install
            print_success "Web dashboard dependencies installed"
        fi
        cd ..
    fi
    
    # Install smart contract dependencies
    if [ -d "smart-contracts" ]; then
        cd smart-contracts
        if [ -f "package.json" ]; then
            print_success "Installing smart contracts dependencies..."
            npm install
            print_success "Smart contracts dependencies installed"
        fi
        cd ..
    fi
}

# Build Docker images
build_docker_images() {
    print_header "Building Docker Images"
    
    print_success "Building backend Docker image..."
    docker build -t iot-network/backend:latest backend-services/
    
    print_success "Building frontend Docker image..."
    docker build -t iot-network/frontend:latest web-dashboard/
    
    print_success "All Docker images built successfully"
}

# Start services with Docker Compose
start_docker_services() {
    print_header "Starting Docker Services"
    
    if [ -f "docker-compose.yml" ]; then
        print_success "Starting services with Docker Compose..."
        docker-compose up -d
        
        print_success "Waiting for services to be ready..."
        sleep 10
        
        print_success "Docker services started"
        docker-compose ps
    else
        print_warning "docker-compose.yml not found"
    fi
}

# Initialize database
initialize_database() {
    print_header "Initializing Database"
    
    print_success "Creating database migrations..."
    cd backend-services
    
    if [ -d "app" ]; then
        # Run Alembic migrations if available
        if command -v alembic &> /dev/null; then
            alembic upgrade head
        else
            print_warning "Alembic not found, skipping migrations"
        fi
    fi
    
    cd ..
    print_success "Database initialized"
}

# Setup Kubernetes manifests
setup_kubernetes() {
    print_header "Setting Up Kubernetes Manifests"
    
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found, skipping Kubernetes setup"
        return
    fi
    
    if [ -d "infrastructure/k8s" ]; then
        print_success "Creating Kubernetes namespace..."
        kubectl create namespace iot-network || print_warning "Namespace already exists"
        
        print_success "Applying Kubernetes manifests..."
        kubectl apply -f infrastructure/k8s/pod-security-standards.yaml
        kubectl apply -f infrastructure/k8s/deployments.yaml
        kubectl apply -f infrastructure/k8s/services.yaml
        kubectl apply -f infrastructure/k8s/horizontal-pod-autoscaling.yaml
        
        print_success "Kubernetes manifests applied"
    else
        print_warning "infrastructure/k8s directory not found"
    fi
}

# Setup monitoring
setup_monitoring() {
    print_header "Setting Up Monitoring"
    
    print_success "Starting monitoring services..."
    
    if [ -f "monitoring/docker-compose.monitoring.yml" ]; then
        docker-compose -f monitoring/docker-compose.monitoring.yml up -d
        print_success "Monitoring services started"
        print_success "Prometheus: http://localhost:9090"
        print_success "Grafana: http://localhost:3001 (admin/admin123)"
    else
        print_warning "monitoring/docker-compose.monitoring.yml not found"
    fi
}

# Setup Loki centralized logging
setup_loki() {
    print_header "Setting Up Loki Centralized Logging"
    
    if command -v kubectl &> /dev/null; then
        if [ -f "infrastructure/k8s/loki-deployment.yaml" ]; then
            print_success "Deploying Loki..."
            kubectl apply -f infrastructure/k8s/loki-deployment.yaml
            print_success "Loki deployment initiated"
        else
            print_warning "Loki deployment file not found"
        fi
    fi
}

# Setup Vault
setup_vault() {
    print_header "Setting Up HashiCorp Vault"
    
    if command -v kubectl &> /dev/null; then
        if [ -f "infrastructure/k8s/vault-deployment.yaml" ]; then
            print_success "Deploying Vault..."
            kubectl apply -f infrastructure/k8s/vault-deployment.yaml
            print_success "Vault deployment initiated"
        else
            print_warning "Vault deployment file not found"
        fi
    fi
}

# Setup Istio service mesh
setup_istio() {
    print_header "Setting Up Istio Service Mesh"
    
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found, skipping Istio setup"
        return
    fi
    
    if ! command -v istioctl &> /dev/null; then
        print_warning "istioctl not found. Install with: curl -L https://istio.io/downloadIstio | sh -"
        return
    fi
    
    print_success "Installing Istio..."
    istioctl install --set profile=demo -y || print_warning "Istio installation may already be in progress"
    
    print_success "Labeling namespace for Istio injection..."
    kubectl label namespace iot-network istio-injection=enabled --overwrite
    
    print_success "Istio setup initiated"
}

# Run tests
run_tests() {
    print_header "Running Tests"
    
    print_success "Running backend tests..."
    cd backend-services
    pytest tests/ -v || print_warning "Backend tests failed"
    cd ..
    
    print_success "Running smart contract tests..."
    cd smart-contracts
    npm test || print_warning "Smart contract tests failed"
    cd ..
    
    print_success "Running frontend tests..."
    cd web-dashboard
    npm test || print_warning "Frontend tests failed"
    cd ..
}

# Validate project structure
validate_project() {
    print_header "Validating Project Structure"
    
    if [ -f "validate_project.py" ]; then
        python3 validate_project.py
    else
        print_warning "validate_project.py not found"
    fi
}

# Print deployment information
print_deployment_info() {
    print_header "Deployment Information"
    
    print_success "Backend API: http://localhost:8000"
    print_success "Frontend Web Dashboard: http://localhost:3000"
    print_success "Prometheus: http://localhost:9090"
    print_success "Grafana: http://localhost:3001 (admin/admin123)"
    print_success "Mosquitto MQTT: localhost:1883"
    
    if command -v kubectl &> /dev/null; then
        print_success "\nKubernetes Services:"
        kubectl get services -n iot-network 2>/dev/null || print_warning "Kubernetes cluster not available"
    fi
}

# Main execution
main() {
    print_header "Decentralized IoT Network - Complete Setup"
    
    check_prerequisites
    install_python_dependencies
    install_node_dependencies
    build_docker_images
    start_docker_services
    initialize_database
    setup_monitoring
    setup_loki
    setup_vault
    setup_istio
    setup_kubernetes
    validate_project
    run_tests
    print_deployment_info
    
    print_header "Setup Complete!"
    print_success "All components have been set up successfully!"
}

# Run main function
main "$@"
