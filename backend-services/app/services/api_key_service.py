"""
API Key Authentication Service.
Provides secure API key generation, validation, and management for programmatic access.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session


class APIKeyService:
    """
    Service for managing API keys for machine-to-machine authentication.
    """
    
    # In-memory store for demo; in production, use database
    _api_keys: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure API key."""
        return f"iot_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def create_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str] = None,
        expires_in_days: int = 365
    ) -> Dict[str, Any]:
        """
        Create a new API key for a user.
        
        Args:
            user_id: The ID of the user creating the key
            name: A friendly name for the key
            scopes: List of allowed scopes (e.g., ["devices:read", "analytics:read"])
            expires_in_days: Number of days until the key expires
        
        Returns:
            Dictionary containing the key details (key is only shown once!)
        """
        raw_key = self.generate_key()
        hashed_key = self.hash_key(raw_key)
        
        key_data = {
            "id": secrets.token_hex(8),
            "user_id": user_id,
            "name": name,
            "hashed_key": hashed_key,
            "scopes": scopes or ["*"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
            "last_used": None,
            "is_active": True
        }
        
        self._api_keys[hashed_key] = key_data
        
        # Return with the raw key (only time it's visible)
        return {
            **key_data,
            "api_key": raw_key  # Only shown once!
        }
    
    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return its metadata.
        
        Args:
            api_key: The raw API key to validate
        
        Returns:
            Key metadata if valid, None if invalid or expired
        """
        hashed_key = self.hash_key(api_key)
        key_data = self._api_keys.get(hashed_key)
        
        if not key_data:
            return None
        
        if not key_data["is_active"]:
            return None
        
        if datetime.fromisoformat(key_data["expires_at"]) < datetime.utcnow():
            return None
        
        # Update last used
        key_data["last_used"] = datetime.utcnow().isoformat()
        
        return key_data
    
    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The ID of the key to revoke
            user_id: The ID of the user (for authorization)
        
        Returns:
            True if key was revoked, False if not found
        """
        for hashed_key, key_data in self._api_keys.items():
            if key_data["id"] == key_id and key_data["user_id"] == user_id:
                key_data["is_active"] = False
                return True
        return False
    
    def list_keys(self, user_id: str) -> list[Dict[str, Any]]:
        """
        List all API keys for a user.
        
        Args:
            user_id: The ID of the user
        
        Returns:
            List of key metadata (excluding the hashed key)
        """
        return [
            {k: v for k, v in data.items() if k != "hashed_key"}
            for data in self._api_keys.values()
            if data["user_id"] == user_id
        ]
    
    def has_scope(self, key_data: Dict[str, Any], required_scope: str) -> bool:
        """
        Check if a key has the required scope.
        
        Args:
            key_data: The key metadata
            required_scope: The scope to check (e.g., "devices:write")
        
        Returns:
            True if the key has the required scope
        """
        scopes = key_data.get("scopes", [])
        
        # Wildcard allows all
        if "*" in scopes:
            return True
        
        # Check exact match
        if required_scope in scopes:
            return True
        
        # Check category wildcard (e.g., "devices:*")
        category = required_scope.split(":")[0]
        if f"{category}:*" in scopes:
            return True
        
        return False


# Global instance
api_key_service = APIKeyService()
