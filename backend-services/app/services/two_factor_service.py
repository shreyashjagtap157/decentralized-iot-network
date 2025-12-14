"""
Two-Factor Authentication (2FA) Service.
Provides TOTP-based 2FA for enhanced account security.
"""
import os
import hmac
import time
import struct
import hashlib
import base64
import secrets
from typing import Optional, Tuple
from datetime import datetime


class TOTPService:
    """
    Time-based One-Time Password (TOTP) service for 2FA.
    Compatible with Google Authenticator, Authy, etc.
    """
    
    def __init__(
        self,
        digits: int = 6,
        interval: int = 30,
        algorithm: str = "sha1"
    ):
        """
        Initialize TOTP service.
        
        Args:
            digits: Number of digits in OTP (usually 6)
            interval: Time interval in seconds (usually 30)
            algorithm: Hash algorithm (sha1, sha256, sha512)
        """
        self.digits = digits
        self.interval = interval
        self.algorithm = algorithm
        self.issuer = "IoT Network"
    
    def generate_secret(self, length: int = 32) -> str:
        """
        Generate a random base32-encoded secret key.
        
        Args:
            length: Length of the secret in bytes
            
        Returns:
            Base32-encoded secret string
        """
        secret_bytes = secrets.token_bytes(length)
        return base64.b32encode(secret_bytes).decode('utf-8').rstrip('=')
    
    def _get_hotp_token(self, secret: str, counter: int) -> str:
        """Generate HOTP token."""
        # Decode the base32 secret
        key = base64.b32decode(secret + '=' * (8 - len(secret) % 8))
        
        # Pack counter as big-endian 64-bit integer
        counter_bytes = struct.pack('>Q', counter)
        
        # Calculate HMAC
        if self.algorithm == "sha256":
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha256).digest()
        elif self.algorithm == "sha512":
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha512).digest()
        else:
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        binary = struct.unpack('>I', hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
        
        # Generate OTP
        otp = binary % (10 ** self.digits)
        return str(otp).zfill(self.digits)
    
    def get_totp_token(self, secret: str, timestamp: Optional[float] = None) -> str:
        """
        Generate current TOTP token.
        
        Args:
            secret: Base32-encoded secret
            timestamp: Unix timestamp (defaults to current time)
            
        Returns:
            TOTP token string
        """
        if timestamp is None:
            timestamp = time.time()
        
        counter = int(timestamp // self.interval)
        return self._get_hotp_token(secret, counter)
    
    def verify_token(
        self,
        secret: str,
        token: str,
        window: int = 1
    ) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: Base32-encoded secret
            token: Token to verify
            window: Number of intervals to check before/after current time
            
        Returns:
            True if token is valid
        """
        if len(token) != self.digits:
            return False
        
        current_time = time.time()
        current_counter = int(current_time // self.interval)
        
        # Check current interval and surrounding windows
        for offset in range(-window, window + 1):
            counter = current_counter + offset
            expected_token = self._get_hotp_token(secret, counter)
            
            if hmac.compare_digest(token, expected_token):
                return True
        
        return False
    
    def get_provisioning_uri(
        self,
        secret: str,
        account_name: str,
        issuer: Optional[str] = None
    ) -> str:
        """
        Generate otpauth:// URI for QR code.
        
        Args:
            secret: Base32-encoded secret
            account_name: User's email or username
            issuer: Service name (defaults to self.issuer)
            
        Returns:
            otpauth URI string
        """
        issuer = issuer or self.issuer
        
        # URL-encode the account name and issuer
        from urllib.parse import quote
        
        label = f"{issuer}:{account_name}"
        params = f"secret={secret}&issuer={quote(issuer)}&algorithm={self.algorithm.upper()}&digits={self.digits}&period={self.interval}"
        
        return f"otpauth://totp/{quote(label)}?{params}"
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            List of backup code strings
        """
        return [
            secrets.token_hex(4).upper()
            for _ in range(count)
        ]


class TwoFactorAuthService:
    """
    High-level 2FA service for managing user 2FA settings.
    """
    
    def __init__(self):
        self.totp = TOTPService()
        # In-memory storage for demo; use database in production
        self._user_secrets: dict[str, dict] = {}
    
    def setup_2fa(self, user_id: str, email: str) -> Tuple[str, str, list[str]]:
        """
        Initialize 2FA setup for a user.
        
        Args:
            user_id: User's unique ID
            email: User's email for the authenticator app
            
        Returns:
            Tuple of (secret, provisioning_uri, backup_codes)
        """
        secret = self.totp.generate_secret()
        uri = self.totp.get_provisioning_uri(secret, email)
        backup_codes = self.totp.generate_backup_codes()
        
        # Store temporarily until verification
        self._user_secrets[user_id] = {
            "secret": secret,
            "backup_codes": backup_codes,
            "verified": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return secret, uri, backup_codes
    
    def verify_and_enable(self, user_id: str, token: str) -> bool:
        """
        Verify token and enable 2FA for user.
        
        Args:
            user_id: User's unique ID
            token: Token from authenticator app
            
        Returns:
            True if verification successful and 2FA enabled
        """
        user_data = self._user_secrets.get(user_id)
        if not user_data:
            return False
        
        if self.totp.verify_token(user_data["secret"], token):
            user_data["verified"] = True
            return True
        
        return False
    
    def verify_login(self, user_id: str, token: str) -> bool:
        """
        Verify 2FA token during login.
        
        Args:
            user_id: User's unique ID
            token: Token from authenticator app
            
        Returns:
            True if token is valid
        """
        user_data = self._user_secrets.get(user_id)
        if not user_data or not user_data.get("verified"):
            return False
        
        # Check TOTP token
        if self.totp.verify_token(user_data["secret"], token):
            return True
        
        # Check backup codes
        if token.upper() in user_data.get("backup_codes", []):
            # Remove used backup code
            user_data["backup_codes"].remove(token.upper())
            return True
        
        return False
    
    def disable_2fa(self, user_id: str) -> bool:
        """
        Disable 2FA for a user.
        
        Args:
            user_id: User's unique ID
            
        Returns:
            True if 2FA was disabled
        """
        if user_id in self._user_secrets:
            del self._user_secrets[user_id]
            return True
        return False
    
    def is_enabled(self, user_id: str) -> bool:
        """Check if 2FA is enabled for a user."""
        user_data = self._user_secrets.get(user_id)
        return bool(user_data and user_data.get("verified"))
    
    def regenerate_backup_codes(self, user_id: str) -> Optional[list[str]]:
        """
        Generate new backup codes for a user.
        
        Args:
            user_id: User's unique ID
            
        Returns:
            New backup codes or None if 2FA not enabled
        """
        user_data = self._user_secrets.get(user_id)
        if not user_data or not user_data.get("verified"):
            return None
        
        new_codes = self.totp.generate_backup_codes()
        user_data["backup_codes"] = new_codes
        return new_codes


# Global 2FA service instance
two_factor_service = TwoFactorAuthService()
