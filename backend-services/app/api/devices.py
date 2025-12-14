from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas import DeviceRegistration, DeviceResponse, DeviceUpdate
from app.db.models import Device, get_db
from app.core.exceptions import DeviceNotFoundError
from app.core.logging import logger
from app.core.metrics import device_registrations_total
from app.services.auth_service import auth_service
from app.services.blockchain_service import blockchain_service
from app.api.dependencies import get_current_user
from app.db.models import User
from datetime import datetime

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.post("/register", response_model=DeviceResponse)
async def register_device(
    device_data: DeviceRegistration,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    # api_key: str = Depends(verify_api_key)  # Placeholder for API key verification
):
    """
    Register a new device.
    Args:
        device_data (DeviceRegistration): Device registration data.
        db (AsyncSession): Database session.
    Returns:
        DeviceResponse: Registered device info.
    Raises:
        HTTPException: If device ID already exists or on error.
    """
    # 1. Validate device_data with Pydantic (handled by FastAPI)
    # 2. Check for duplicate device_id
    existing = await db.execute(
        select(Device).where(Device.device_id == device_data.device_id)
    )
    if existing.scalar():
        device_registrations_total.labels(status="duplicate").inc()
        logger.error("Device registration failed: duplicate device_id", device_id=device_data.device_id)
        raise HTTPException(status_code=409, detail="Device ID already exists")
    # 3. Validate owner_address format (handled by Pydantic)
    # 4. Create device record with proper error handling
    try:
        hashed_signature = auth_service.get_password_hash(device_data.signature)
        device = Device(
            device_id=device_data.device_id,
            device_type=device_data.device_type,
            owner_address=device_data.owner_address,
            location_lat=device_data.location_lat,
            location_lng=device_data.location_lng,
            hashed_signature=hashed_signature,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        # Trigger blockchain registration
        background_tasks.add_task(
            blockchain_service.register_device_on_chain,
            device_id=device.device_id,
            owner_address=device.owner_address
        )

        device_registrations_total.labels(status="success").inc()
        logger.info(
            "Device registered successfully",
            device_id=device.device_id,
            owner_address=device.owner_address,
            location={"lat": device.location_lat, "lng": device.location_lng},
            timestamp=datetime.utcnow().isoformat()
        )
        # 6. Return structured response with created device info
        return DeviceResponse(
            device_id=device.device_id,
            device_type=device.device_type,
            owner_address=device.owner_address,
            status=device.status,
            created_at=device.created_at
        )
    except Exception as e:
        device_registrations_total.labels(status="error").inc()
        logger.error("Device registration error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me", response_model=list[DeviceResponse])
async def read_user_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve devices registered by the current authenticated user.
    """
    devices = await db.execute(
        select(Device).where(Device.owner_address == current_user.username) # Assuming username is the owner identifier
    )
    return devices.scalars().all()

@router.get("/", response_model=list[DeviceResponse])
async def get_all_devices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all devices (Admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    devices = await db.execute(
        select(Device).offset(skip).limit(limit)
    )
    return devices.scalars().all()

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a device.
    """
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
         raise HTTPException(status_code=404, detail="Device not found")
         
    if device.owner_address != current_user.username and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")

    if device_update.location_lat is not None:
        device.location_lat = device_update.location_lat
    if device_update.location_lng is not None:
        device.location_lng = device_update.location_lng
    if device_update.status:
        device.status = device_update.status
    if device_update.device_type:
        device.device_type = device_update.device_type
        
    await db.commit()
    await db.refresh(device)
    return device
