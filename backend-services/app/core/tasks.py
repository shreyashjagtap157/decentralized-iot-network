"""
Background task queue for heavy operations
"""
from celery import Celery
import os
from typing import Optional, Dict, Any
import logging
from .monitoring import log_error

# Celery configuration
celery_app = Celery(
    "iot_network_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["app.tasks.blockchain", "app.tasks.notifications", "app.tasks.analytics"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@celery_app.task(bind=True, max_retries=3)
def process_blockchain_transaction(self, transaction_data: Dict[str, Any]):
    """Process blockchain transaction in background"""
    try:
        from app.services.blockchain import process_reward_distribution
        
        result = process_reward_distribution(
            device_id=transaction_data["device_id"],
            amount=transaction_data["amount"],
            quality_score=transaction_data["quality_score"]
        )
        
        logging.info(f"Blockchain transaction processed: {result}")
        return result
        
    except Exception as exc:
        log_error(exc, {"task": "process_blockchain_transaction", "data": transaction_data})
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        raise exc

@celery_app.task(bind=True)
def send_notification(self, notification_data: Dict[str, Any]):
    """Send notification in background"""
    try:
        from app.services.notifications import send_push_notification
        
        result = send_push_notification(
            user_id=notification_data["user_id"],
            title=notification_data["title"],
            message=notification_data["message"],
            data=notification_data.get("data", {})
        )
        
        logging.info(f"Notification sent: {result}")
        return result
        
    except Exception as exc:
        log_error(exc, {"task": "send_notification", "data": notification_data})
        raise exc

@celery_app.task(bind=True)
def generate_analytics_report(self, user_id: str, report_type: str):
    """Generate analytics report in background"""
    try:
        from app.services.analytics import generate_user_report
        
        result = generate_user_report(user_id, report_type)
        
        logging.info(f"Analytics report generated for user {user_id}")
        return result
        
    except Exception as exc:
        log_error(exc, {"task": "generate_analytics_report", "user_id": user_id})
        raise exc

@celery_app.task(bind=True)
def update_device_metrics(self, device_id: str):
    """Update device metrics and quality scores"""
    try:
        from app.services.device_metrics import calculate_device_quality
        
        result = calculate_device_quality(device_id)
        
        logging.info(f"Device metrics updated for {device_id}")
        return result
        
    except Exception as exc:
        log_error(exc, {"task": "update_device_metrics", "device_id": device_id})
        raise exc

@celery_app.task(bind=True)
def cleanup_old_data(self):
    """Clean up old data and optimize database"""
    try:
        from app.services.cleanup import perform_data_cleanup
        
        result = perform_data_cleanup()
        
        logging.info("Data cleanup completed")
        return result
        
    except Exception as exc:
        log_error(exc, {"task": "cleanup_old_data"})
        raise exc

# Task scheduling
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-data': {
        'task': 'app.core.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'update-all-device-metrics': {
        'task': 'app.tasks.analytics.update_all_device_metrics',
        'schedule': crontab(minute='*/10'),  # Run every 10 minutes
    },
}

def enqueue_blockchain_transaction(device_id: str, amount: float, quality_score: int):
    """Enqueue blockchain transaction task"""
    return process_blockchain_transaction.delay({
        "device_id": device_id,
        "amount": amount,
        "quality_score": quality_score
    })

def enqueue_notification(user_id: str, title: str, message: str, data: Dict[str, Any] = None):
    """Enqueue notification task"""
    return send_notification.delay({
        "user_id": user_id,
        "title": title,
        "message": message,
        "data": data or {}
    })

def enqueue_analytics_report(user_id: str, report_type: str):
    """Enqueue analytics report generation"""
    return generate_analytics_report.delay(user_id, report_type)
