"""
Notification service for sending alerts to users.
Supports email, push notifications, and in-app notifications.
"""
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()


class NotificationType(str, Enum):
    """Types of notifications."""
    REWARD_EARNED = "reward_earned"
    DEVICE_STATUS = "device_status"
    WITHDRAWAL_COMPLETE = "withdrawal_complete"
    SECURITY_ALERT = "security_alert"
    SYSTEM_UPDATE = "system_update"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    SMS = "sms"
    WEBHOOK = "webhook"


class Notification:
    """Represents a notification to be sent."""
    
    def __init__(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        self.id = f"notif_{datetime.utcnow().timestamp()}"
        self.user_id = user_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.priority = priority
        self.data = data or {}
        self.channels = channels or [NotificationChannel.IN_APP]
        self.created_at = datetime.utcnow()
        self.read = False
        self.delivered = False


class NotificationService:
    """
    Central notification service for the IoT platform.
    Handles routing notifications to appropriate channels.
    """
    
    def __init__(self):
        self._in_app_notifications: Dict[str, List[Notification]] = {}
        self._email_enabled = bool(os.getenv("SMTP_HOST"))
        self._push_enabled = bool(os.getenv("PUSH_SERVER_KEY"))
    
    async def send(self, notification: Notification) -> bool:
        """
        Send a notification through configured channels.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if notification was delivered through at least one channel
        """
        success = False
        
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.EMAIL and self._email_enabled:
                    await self._send_email(notification)
                    success = True
                elif channel == NotificationChannel.PUSH and self._push_enabled:
                    await self._send_push(notification)
                    success = True
                elif channel == NotificationChannel.IN_APP:
                    self._store_in_app(notification)
                    success = True
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(notification)
                    success = True
            except Exception as e:
                logger.error(
                    "notification_delivery_failed",
                    channel=channel.value,
                    notification_id=notification.id,
                    error=str(e)
                )
        
        notification.delivered = success
        return success
    
    async def _send_email(self, notification: Notification) -> None:
        """Send notification via email."""
        # Email implementation would go here
        # Using SMTP or a service like SendGrid
        logger.info(
            "email_notification_sent",
            user_id=notification.user_id,
            notification_type=notification.notification_type.value
        )
    
    async def _send_push(self, notification: Notification) -> None:
        """Send push notification."""
        # Push notification implementation (e.g., Firebase Cloud Messaging)
        logger.info(
            "push_notification_sent",
            user_id=notification.user_id,
            notification_type=notification.notification_type.value
        )
    
    def _store_in_app(self, notification: Notification) -> None:
        """Store notification for in-app display."""
        if notification.user_id not in self._in_app_notifications:
            self._in_app_notifications[notification.user_id] = []
        
        self._in_app_notifications[notification.user_id].insert(0, notification)
        
        # Keep only last 100 notifications per user
        if len(self._in_app_notifications[notification.user_id]) > 100:
            self._in_app_notifications[notification.user_id] = \
                self._in_app_notifications[notification.user_id][:100]
    
    async def _send_webhook(self, notification: Notification) -> None:
        """Send notification to configured webhook."""
        # Webhook implementation
        logger.info(
            "webhook_notification_sent",
            user_id=notification.user_id,
            notification_type=notification.notification_type.value
        )
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.
        
        Args:
            user_id: The user's ID
            unread_only: If True, return only unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries
        """
        notifications = self._in_app_notifications.get(user_id, [])
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        return [
            {
                "id": n.id,
                "type": n.notification_type.value,
                "title": n.title,
                "message": n.message,
                "priority": n.priority.value,
                "data": n.data,
                "read": n.read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications[:limit]
        ]
    
    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        notifications = self._in_app_notifications.get(user_id, [])
        for n in notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False
    
    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        notifications = self._in_app_notifications.get(user_id, [])
        count = 0
        for n in notifications:
            if not n.read:
                n.read = True
                count += 1
        return count
    
    # Convenience methods for common notifications
    
    async def notify_reward_earned(
        self,
        user_id: str,
        amount: float,
        device_id: str
    ) -> None:
        """Send notification when user earns a reward."""
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.REWARD_EARNED,
            title="Reward Earned! 🎉",
            message=f"You earned {amount:.6f} NWR from device {device_id}",
            priority=NotificationPriority.MEDIUM,
            data={"amount": amount, "device_id": device_id},
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
        )
        await self.send(notification)
    
    async def notify_device_status_change(
        self,
        user_id: str,
        device_id: str,
        old_status: str,
        new_status: str
    ) -> None:
        """Send notification when device status changes."""
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.DEVICE_STATUS,
            title="Device Status Changed",
            message=f"Device {device_id} is now {new_status}",
            priority=NotificationPriority.MEDIUM if new_status != "INACTIVE" else NotificationPriority.HIGH,
            data={"device_id": device_id, "old_status": old_status, "new_status": new_status},
            channels=[NotificationChannel.IN_APP]
        )
        await self.send(notification)
    
    async def notify_security_alert(
        self,
        user_id: str,
        alert_type: str,
        details: str
    ) -> None:
        """Send security alert notification."""
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.SECURITY_ALERT,
            title="Security Alert ⚠️",
            message=details,
            priority=NotificationPriority.URGENT,
            data={"alert_type": alert_type},
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.PUSH]
        )
        await self.send(notification)


# Global notification service instance
notification_service = NotificationService()
