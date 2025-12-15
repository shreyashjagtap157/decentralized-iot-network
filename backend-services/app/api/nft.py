"""
NFT API Routes
REST endpoints for Device NFT functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.services.nft_service import get_nft_service, NFTService
from app.api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nft", tags=["nft"])


# ==================== Schemas ====================

class DeviceNFTResponse(BaseModel):
    token_id: int
    device_id: str
    device_type: str
    owner: str
    registration_date: datetime
    total_rewards_earned: float
    total_data_transferred_gb: float
    quality_score: int
    is_active: bool
    token_uri: str
    image_url: Optional[str]


class MintDeviceRequest(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=100)
    device_type: str = Field(..., min_length=2, max_length=50)


class NFTMetadataResponse(BaseModel):
    name: str
    description: str
    image: str
    attributes: List[Dict[str, Any]]


class MintTransactionResponse(BaseModel):
    transaction: dict
    metadata: NFTMetadataResponse
    message: str


class TransactionResponse(BaseModel):
    transaction: dict
    message: str


class NFTStatsResponse(BaseModel):
    total_devices: int
    active_devices: int
    total_rewards_distributed: float


# ==================== Endpoints ====================

@router.get("/stats", response_model=NFTStatsResponse)
async def get_nft_stats(
    service: NFTService = Depends(get_nft_service)
):
    """Get global NFT statistics."""
    total = await service.get_total_devices()
    return NFTStatsResponse(
        total_devices=total,
        active_devices=total,  # Would need to track separately
        total_rewards_distributed=0  # Would need to aggregate
    )


@router.get("/device/id/{device_id}", response_model=Optional[DeviceNFTResponse])
async def get_device_by_device_id(
    device_id: str,
    service: NFTService = Depends(get_nft_service)
):
    """Get NFT by device ID."""
    nft = await service.get_device_by_device_id(device_id)
    if not nft:
        raise HTTPException(status_code=404, detail="Device NFT not found")
    
    return DeviceNFTResponse(
        token_id=nft.token_id,
        device_id=nft.device_id,
        device_type=nft.device_type,
        owner=nft.owner,
        registration_date=nft.registration_date,
        total_rewards_earned=float(nft.total_rewards_earned),
        total_data_transferred_gb=float(nft.total_data_transferred),
        quality_score=nft.quality_score,
        is_active=nft.is_active,
        token_uri=nft.token_uri,
        image_url=nft.image_url
    )


@router.get("/device/token/{token_id}", response_model=Optional[DeviceNFTResponse])
async def get_device_by_token_id(
    token_id: int,
    service: NFTService = Depends(get_nft_service)
):
    """Get NFT by token ID."""
    nft = await service.get_device_nft(token_id)
    if not nft:
        raise HTTPException(status_code=404, detail="Device NFT not found")
    
    return DeviceNFTResponse(
        token_id=nft.token_id,
        device_id=nft.device_id,
        device_type=nft.device_type,
        owner=nft.owner,
        registration_date=nft.registration_date,
        total_rewards_earned=float(nft.total_rewards_earned),
        total_data_transferred_gb=float(nft.total_data_transferred),
        quality_score=nft.quality_score,
        is_active=nft.is_active,
        token_uri=nft.token_uri,
        image_url=nft.image_url
    )


@router.get("/owner/{owner_address}", response_model=List[DeviceNFTResponse])
async def get_owner_devices(
    owner_address: str,
    service: NFTService = Depends(get_nft_service)
):
    """Get all device NFTs owned by an address."""
    devices = await service.get_user_devices(owner_address)
    return [
        DeviceNFTResponse(
            token_id=d.token_id,
            device_id=d.device_id,
            device_type=d.device_type,
            owner=d.owner,
            registration_date=d.registration_date,
            total_rewards_earned=float(d.total_rewards_earned),
            total_data_transferred_gb=float(d.total_data_transferred),
            quality_score=d.quality_score,
            is_active=d.is_active,
            token_uri=d.token_uri,
            image_url=d.image_url
        )
        for d in devices
    ]


@router.get("/metadata/{device_id}", response_model=NFTMetadataResponse)
async def generate_metadata(
    device_id: str,
    device_type: str = Query(...),
    quality_score: int = Query(100, ge=0, le=100),
    service: NFTService = Depends(get_nft_service)
):
    """Generate NFT metadata for a device."""
    metadata = service.generate_metadata(device_id, device_type, quality_score)
    return NFTMetadataResponse(
        name=metadata.name,
        description=metadata.description,
        image=metadata.image,
        attributes=metadata.attributes
    )


@router.post("/mint", response_model=MintTransactionResponse)
async def mint_device_nft(
    request: MintDeviceRequest,
    owner_address: str,
    service: NFTService = Depends(get_nft_service)
):
    """Mint a new device NFT."""
    try:
        result = await service.prepare_mint_tx(
            owner=owner_address,
            device_id=request.device_id,
            device_type=request.device_type
        )
        
        metadata = result.get('metadata', {})
        
        return MintTransactionResponse(
            transaction=result['transaction'],
            metadata=NFTMetadataResponse(
                name=metadata.get('name', ''),
                description=metadata.get('description', ''),
                image=metadata.get('image', ''),
                attributes=metadata.get('attributes', [])
            ),
            message=f"Mint NFT for device {request.device_id}"
        )
    except Exception as e:
        logger.error(f"Failed to mint NFT: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deactivate/{device_id}", response_model=TransactionResponse)
async def deactivate_device(
    device_id: str,
    owner_address: str,
    service: NFTService = Depends(get_nft_service)
):
    """Deactivate a device NFT."""
    try:
        tx = await service.prepare_deactivate_tx(owner_address, device_id)
        return TransactionResponse(
            transaction=tx,
            message=f"Deactivate device {device_id}"
        )
    except Exception as e:
        logger.error(f"Failed to deactivate: {e}")
        raise HTTPException(status_code=400, detail=str(e))
