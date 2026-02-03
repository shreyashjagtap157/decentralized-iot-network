"""
Batch API endpoints for high-throughput operations.
Reduces overhead by processing multiple records per request.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.models import Device, NetworkUsage, get_db
from app.core.logging import logger
from app.services.blockchain_service import blockchain_service
from app.api.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


class UsageRecord(BaseModel):
    device_id: str
    bytes_transmitted: int
    bytes_received: int
    connection_quality: int = 80
    user_sessions: int = 1


class BatchUsageSubmission(BaseModel):
    records: List[UsageRecord]


class BatchUsageResponse(BaseModel):
    processed: int
    failed: int
    errors: List[str]


class DeviceStatusUpdate(BaseModel):
    device_id: str
    status: str


class BatchStatusUpdate(BaseModel):
    updates: List[DeviceStatusUpdate]


@router.post("/usage", response_model=BatchUsageResponse)
async def submit_batch_usage(
    data: BatchUsageSubmission,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit multiple usage records in a single request.
    Maximum 100 records per batch for optimal performance.
    """
    if len(data.records) > 100:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 100 records per batch"
        )
    
    processed = 0
    failed = 0
    errors = []
    
    # Validate all device IDs exist first (single query)
    device_ids = [r.device_id for r in data.records]
    result = await db.execute(
        select(Device.device_id).where(Device.device_id.in_(device_ids))
    )
    valid_device_ids = set(result.scalars().all())
    
    # Create usage records for valid devices
    usage_records = []
    for record in data.records:
        if record.device_id not in valid_device_ids:
            failed += 1
            errors.append(f"Device {record.device_id} not found")
            continue
        
        usage = NetworkUsage(
            device_id=record.device_id,
            bytes_transmitted=record.bytes_transmitted,
            bytes_received=record.bytes_received,
            connection_quality=record.connection_quality,
            user_sessions=record.user_sessions,
            timestamp=datetime.utcnow(),
        )
        usage_records.append(usage)
        processed += 1
    
    # Bulk insert
    if usage_records:
        db.add_all(usage_records)
        await db.commit()
        
        # Queue blockchain submissions in background
        background_tasks.add_task(
            _submit_batch_to_blockchain,
            usage_records
        )
    
    logger.info(
        "Batch usage submission",
        processed=processed,
        failed=failed,
        total=len(data.records)
    )
    
    return BatchUsageResponse(
        processed=processed,
        failed=failed,
        errors=errors[:10]  # Limit error messages returned
    )


async def _submit_batch_to_blockchain(usage_records: List[NetworkUsage]):
    """Background task to submit usage to blockchain"""
    for record in usage_records:
        try:
            await blockchain_service.submit_compensation_data(
                device_id=record.device_id,
                total_bytes=record.bytes_transmitted + record.bytes_received,
                owner_address="",  # Would be fetched from device
                quality_score=record.connection_quality
            )
        except Exception as e:
            logger.error(f"Blockchain submission failed for {record.device_id}: {e}")


@router.post("/device-status")
async def batch_update_device_status(
    data: BatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update status of multiple devices in a single request.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    if len(data.updates) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 updates per batch"
        )
    
    updated = 0
    not_found = 0
    
    for update in data.updates:
        result = await db.execute(
            select(Device).where(Device.device_id == update.device_id)
        )
        device = result.scalar_one_or_none()
        
        if device:
            device.status = update.status
            updated += 1
        else:
            not_found += 1
    
    await db.commit()
    
    return {
        "updated": updated,
        "not_found": not_found
    }


@router.get("/devices")
async def batch_get_devices(
    device_ids: str,  # Comma-separated list
    db: AsyncSession = Depends(get_db),
):
    """
    Get multiple devices by ID in a single request.
    Pass device IDs as comma-separated string.
    """
    ids = [id.strip() for id in device_ids.split(",") if id.strip()]
    
    if len(ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 device IDs per request"
        )
    
    result = await db.execute(
        select(Device).where(Device.device_id.in_(ids))
    )
    devices = result.scalars().all()
    
    return {
        "requested": len(ids),
        "found": len(devices),
        "devices": devices
    }
