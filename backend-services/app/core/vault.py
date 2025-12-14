import hvac
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VaultClient:
    """Wrapper for Vault client with error handling and logging."""
    
    def __init__(self):
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault.vault:8200')
        self.vault_namespace = os.getenv('VAULT_NAMESPACE', 'admin')
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Vault using Kubernetes auth."""
        try:
            self.client = hvac.Client(
                url=self.vault_addr,
                namespace=self.vault_namespace
            )
            
            # Read JWT from Kubernetes service account
            jwt_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
            if os.path.exists(jwt_path):
                with open(jwt_path) as f:
                    jwt = f.read()
                
                # Authenticate using Kubernetes auth method
                response = self.client.auth.kubernetes.login(
                    role=os.getenv('VAULT_ROLE', 'backend'),
                    jwt=jwt
                )
                
                self.client.token = response['auth']['client_token']
                logger.info("Successfully authenticated with Vault using Kubernetes auth")
            else:
                logger.warning("JWT not found, attempting to use token from environment")
                token = os.getenv('VAULT_TOKEN')
                if token:
                    self.client.token = token
                    logger.info("Using VAULT_TOKEN from environment")
        
        except Exception as e:
            logger.error(f"Failed to authenticate with Vault: {str(e)}")
            raise
    
    def get_secret(self, path: str) -> Dict[str, Any]:
        """Retrieve a secret from Vault."""
        try:
            secret = self.client.secrets.kv.read_secret_version(path=path)
            return secret['data']['data']
        except Exception as e:
            logger.error(f"Failed to retrieve secret from {path}: {str(e)}")
            raise
    
    def put_secret(self, path: str, data: Dict[str, str]) -> None:
        """Store a secret in Vault."""
        try:
            self.client.secrets.kv.create_or_update_secret(
                path=path,
                secret_data=data
            )
            logger.info(f"Secret stored at {path}")
        except Exception as e:
            logger.error(f"Failed to store secret at {path}: {str(e)}")
            raise
    
    def list_secrets(self, path: str) -> list:
        """List all secrets under a path."""
        try:
            response = self.client.secrets.kv.list_secrets(path=path)
            return response['data']['keys']
        except Exception as e:
            logger.error(f"Failed to list secrets at {path}: {str(e)}")
            raise
    
    def delete_secret(self, path: str) -> None:
        """Delete a secret from Vault."""
        try:
            self.client.secrets.kv.delete_latest_version_of_secret(path=path)
            logger.info(f"Secret deleted from {path}")
        except Exception as e:
            logger.error(f"Failed to delete secret at {path}: {str(e)}")
            raise
    
    def renew_token(self) -> None:
        """Renew the current token."""
        try:
            self.client.auth.token.renew_self()
            logger.info("Token renewed successfully")
        except Exception as e:
            logger.error(f"Failed to renew token: {str(e)}")
            raise


# Global Vault client instance
_vault_client = None


def get_vault_client() -> VaultClient:
    """Get or create the global Vault client instance."""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client


def get_database_credentials() -> Dict[str, str]:
    """Retrieve database credentials from Vault."""
    client = get_vault_client()
    return client.get_secret('secret/data/database/postgres')


def get_mqtt_credentials() -> Dict[str, str]:
    """Retrieve MQTT credentials from Vault."""
    client = get_vault_client()
    return client.get_secret('secret/data/mqtt/credentials')


def get_api_keys() -> Dict[str, str]:
    """Retrieve API keys from Vault."""
    client = get_vault_client()
    return client.get_secret('secret/data/backend/api-keys')
