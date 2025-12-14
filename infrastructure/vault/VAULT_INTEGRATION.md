# HashiCorp Vault Integration Guide

This guide explains how to integrate HashiCorp Vault for secret management in the Decentralized IoT Network project.

## Overview

Vault is a tool for securely storing and accessing sensitive data. Instead of storing secrets in Kubernetes Secrets, environment files, or configuration management systems, we use Vault as a centralized secrets management system.

## Installation

### Prerequisites
- Kubernetes cluster running
- kubectl configured
- Helm 3 installed

### Install Vault using Helm

```bash
# Add the HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Install Vault
helm install vault hashicorp/vault \
  --namespace vault \
  --create-namespace \
  --values vault-values.yaml
```

## Configuration

### 1. Initialize Vault

```bash
# Port-forward to Vault
kubectl port-forward -n vault svc/vault 8200:8200

# Initialize Vault (generates unseal keys and root token)
vault operator init \
  -key-shares=5 \
  -key-threshold=3

# Store the unseal keys and root token securely
```

### 2. Unseal Vault

```bash
# Unseal Vault with 3 of 5 keys
vault operator unseal
vault operator unseal
vault operator unseal
```

### 3. Enable Kubernetes Authentication

```bash
# Login with root token
vault login <root-token>

# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token \
  kubernetes_host=https://$KUBERNETES_SERVICE_HOST:$KUBERNETES_SERVICE_PORT \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
```

### 4. Create Policies and Secrets

```bash
# Create a policy for backend services
vault policy write backend-policy - <<EOF
path "secret/data/backend/*" {
  capabilities = ["read", "list"]
}
path "secret/data/database/*" {
  capabilities = ["read"]
}
path "secret/data/mqtt/*" {
  capabilities = ["read"]
}
EOF

# Create secrets
vault kv put secret/backend/api-keys \
  jwt-secret="your-jwt-secret" \
  api-key="your-api-key"

vault kv put secret/database/postgres \
  username="postgres" \
  password="your-db-password" \
  host="postgres.default.svc.cluster.local" \
  port="5432"

vault kv put secret/mqtt/credentials \
  username="mqtt-user" \
  password="mqtt-password"
```

## Kubernetes Integration

### 1. Create Service Account

```bash
kubectl create serviceaccount backend -n iot-network
```

### 2. Create Vault Auth Role

```bash
vault write auth/kubernetes/role/backend \
  bound_service_account_names=backend \
  bound_service_account_namespaces=iot-network \
  policies=backend-policy \
  ttl=24h
```

### 3. Update Kubernetes Deployment

Modify your deployment to authenticate with Vault and retrieve secrets.

## Python Integration

### Install Vault Client

```bash
pip install hvac
```

### Example Usage

```python
import hvac
import os

def get_vault_secrets():
    # Initialize Vault client
    client = hvac.Client(
        url=os.getenv('VAULT_ADDR', 'http://vault.vault:8200'),
        namespace=os.getenv('VAULT_NAMESPACE', 'admin')
    )
    
    # Authenticate using Kubernetes
    response = client.auth.kubernetes.login(
        role='backend',
        jwt=open('/var/run/secrets/kubernetes.io/serviceaccount/token').read()
    )
    
    client.token = response['auth']['client_token']
    
    # Read secrets
    secret = client.secrets.kv.read_secret_version(path='backend/api-keys')
    return secret['data']['data']

# Usage in FastAPI
from fastapi import Depends

async def get_secrets():
    return get_vault_secrets()
```

## Environment Variables

Add the following environment variables to your deployment:

```yaml
env:
  - name: VAULT_ADDR
    value: "http://vault.vault:8200"
  - name: VAULT_NAMESPACE
    value: "admin"
  - name: VAULT_SKIP_VERIFY
    value: "false"
```

## Monitoring and Auditing

### Enable Audit Logging

```bash
vault audit enable file file_path=/vault/logs/audit.log
```

### Monitor Vault Status

```bash
# Check Vault health
vault status

# View audit logs
kubectl logs -n vault vault-0 | grep audit
```

## Best Practices

1. **Rotation**: Implement automatic secret rotation using Vault's secret engines
2. **RBAC**: Use fine-grained policies to limit access to secrets
3. **Encryption**: Enable encryption at rest in Vault
4. **Backup**: Regularly backup Vault data
5. **Monitoring**: Monitor all secret access and API calls
6. **High Availability**: Deploy Vault in HA mode for production

## Troubleshooting

### Connection Issues

```bash
# Check Vault service
kubectl get svc -n vault

# Port-forward if needed
kubectl port-forward -n vault svc/vault 8200:8200
```

### Authentication Failures

```bash
# Verify service account
kubectl get sa backend -n iot-network

# Check Kubernetes auth configuration
vault read auth/kubernetes/config
```

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [Vault Kubernetes Auth](https://www.vaultproject.io/docs/auth/kubernetes)
- [HVAC Python Client](https://hvac.readthedocs.io/)
