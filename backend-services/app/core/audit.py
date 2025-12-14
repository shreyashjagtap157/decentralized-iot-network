"""
Audit logging service for tracking user actions and security events.
Provides compliance-ready logging for sensitive operations.
"""
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AuditAction(str, Enum):
    """Enumeration of auditable actions."""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_UPDATE = "user.update"
    DEVICE_REGISTER = "device.register"
    DEVICE_UPDATE = "device.update"
    DEVICE_DELETE = "device.delete"
    REWARD_CLAIM = "reward.claim"
    REWARD_WITHDRAW = "reward.withdraw"
    ADMIN_ACTION = "admin.action"
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"


class AuditLogger:
    """
    Centralized audit logging for security and compliance.
    Logs are structured for easy parsing by SIEM systems.
    """
    
    def __init__(self):
        self._logger = structlog.get_logger("audit")
    
    def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log an auditable event.
        
        Args:
            action: The type of action being audited
            user_id: ID of the user performing the action
            resource_id: ID of the affected resource
            resource_type: Type of the affected resource (e.g., "device", "user")
            details: Additional context about the action
            ip_address: Client IP address
            user_agent: Client user agent string
            success: Whether the action succeeded
            error_message: Error message if action failed
        """
        self._logger.info(
            "audit_event",
            action=action.value,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            timestamp=datetime.utcnow().isoformat(),
            event_type="audit"
        )
    
    def log_login(self, user_id: str, ip_address: str, success: bool, error: str = None):
        """Convenience method for login events."""
        self.log(
            action=AuditAction.USER_LOGIN,
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            error_message=error
        )
    
    def log_device_action(
        self,
        action: AuditAction,
        user_id: str,
        device_id: str,
        details: Dict[str, Any] = None
    ):
        """Convenience method for device-related events."""
        self.log(
            action=action,
            user_id=user_id,
            resource_id=device_id,
            resource_type="device",
            details=details
        )


# Global audit logger instance
audit_logger = AuditLogger()
