from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import NetworkUsageRequest
from app.db.models import Device, NetworkUsage, get_db
from app.core.exceptions import DeviceNotFoundError, InvalidUsageDataError
from app.core.logging import logger
from app.core.metrics import usage_reports_total
from datetime import datetime
import uuid
from app.api.dependencies import get_current_device

router = APIRouter(prefix="/api/v1/devices", tags=["usage"])

@router.post("/{device_id}/usage")
async def record_usage(
    device_id: str,
    usage_data: NetworkUsageRequest,
    db: AsyncSession = Depends(get_db),
    current_device: Device = Depends(get_current_device)
):
    """
    Record network usage for a device.
    Args:
        device_id (str): Device identifier.
        usage_data (NetworkUsageRequest): Usage data payload.
        db (AsyncSession): Database session.
    Returns:
        dict: Success status and usage_id.
    Raises:
        DeviceNotFoundError: If device is not found or inactive.
        HTTPException: On error.
    """
    # 1. Validate device exists and is active
    if device_id != current_device.device_id:
        raise HTTPException(status_code=403, detail="Not authorized to record usage for this device")
    
    device = current_device
    if not device or device.status != "ACTIVE":
        usage_reports_total.labels(status="invalid_device").inc()
        logger.error("Usage record failed: device not found or inactive", device_id=device_id)
        raise DeviceNotFoundError(device_id)
    # 2. Validate usage_data structure and ranges (handled by Pydantic)
    # 3. Store usage record in database
    try:
        usage = NetworkUsage(
            usage_id=str(uuid.uuid4()),
            device_id=device_id,
            bytes_transmitted=usage_data.bytes_transmitted,
            bytes_received=usage_data.bytes_received,
            connection_quality=usage_data.connection_quality,
            user_sessions=usage_data.user_sessions,
            timestamp=datetime.utcnow(),
            compensated=False
        )
        db.add(usage)
        # 4. Update device last_heartbeat
        device.last_heartbeat = datetime.utcnow()
        await db.commit()
        usage_reports_total.labels(status="success").inc()
        logger.info(
            "Usage recorded",
            device_id=device_id,
            usage_id=usage.usage_id,
            bytes_transmitted=usage.bytes_transmitted,
            timestamp=usage.timestamp.isoformat()
        )
        # 5. Queue compensation calculation (placeholder)
        # queue_compensation_calculation(device_id, usage.usage_id)
        # 6. Return success response with usage_id
        return {"success": True, "usage_id": usage.usage_id}
    except Exception as e:
        usage_reports_total.labels(status="error").inc()
        logger.error("Usage record error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
