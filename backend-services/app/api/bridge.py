"""
Bridge API Routes
REST endpoints for cross-chain bridge functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from app.services.bridge_service import get_bridge_service, BridgeService
from app.api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ==================== Schemas ====================

class ChainResponse(BaseModel):
    chain_id: int
    name: str
    enabled: bool
    min_amount: float
    max_amount: float
    daily_remaining: float
    explorer_url: str


class BridgeRequest(BaseModel):
    recipient: str = Field(..., description="Recipient address on destination chain")
    amount: float = Field(..., gt=0, description="Amount to bridge")
    dest_chain: int = Field(..., description="Destination chain ID")


class BridgeHistoryResponse(BaseModel):
    id: str
    from_chain: int
    to_chain: int
    amount: float
    fee: float
    status: str
    timestamp: datetime
    tx_hash: Optional[str]


class FeeEstimateResponse(BaseModel):
    amount: float
    fee: float
    received: float
    fee_percentage: float


class BridgeStatsResponse(BaseModel):
    total_bridged: float
    total_fees_collected: float
    pending_requests: int
    completed_requests: int


class TransactionResponse(BaseModel):
    transaction: dict
    message: str


# ==================== Endpoints ====================

@router.get("/chains", response_model=List[ChainResponse])
async def get_supported_chains(
    service: BridgeService = Depends(get_bridge_service)
):
    """Get list of supported chains for bridging."""
    chains = await service.get_supported_chains()
    return [
        ChainResponse(
            chain_id=c.chain_id,
            name=c.name,
            enabled=c.enabled,
            min_amount=float(c.min_amount),
            max_amount=float(c.max_amount),
            daily_remaining=float(c.daily_remaining),
            explorer_url=c.explorer_url
        )
        for c in chains
    ]


@router.get("/chains/{chain_id}", response_model=Optional[ChainResponse])
async def get_chain_config(
    chain_id: int,
    service: BridgeService = Depends(get_bridge_service)
):
    """Get configuration for a specific chain."""
    config = await service.get_chain_config(chain_id)
    if not config:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return ChainResponse(
        chain_id=config.chain_id,
        name=config.name,
        enabled=config.enabled,
        min_amount=float(config.min_amount),
        max_amount=float(config.max_amount),
        daily_remaining=float(config.daily_remaining),
        explorer_url=config.explorer_url
    )


@router.get("/fee", response_model=FeeEstimateResponse)
async def estimate_fee(
    amount: float = Query(..., gt=0),
    service: BridgeService = Depends(get_bridge_service)
):
    """Estimate bridge fee for a given amount."""
    fee = await service.estimate_fee(amount)
    received = await service.estimate_received(amount)
    
    return FeeEstimateResponse(
        amount=amount,
        fee=fee,
        received=received,
        fee_percentage=0.5
    )


@router.get("/stats", response_model=BridgeStatsResponse)
async def get_bridge_stats(
    service: BridgeService = Depends(get_bridge_service)
):
    """Get global bridge statistics."""
    stats = await service.get_stats()
    return BridgeStatsResponse(
        total_bridged=float(stats.total_bridged),
        total_fees_collected=float(stats.total_fees_collected),
        pending_requests=stats.pending_requests,
        completed_requests=stats.completed_requests
    )


@router.get("/history/{user_address}", response_model=List[BridgeHistoryResponse])
async def get_bridge_history(
    user_address: str,
    limit: int = Query(20, ge=1, le=100),
    service: BridgeService = Depends(get_bridge_service)
):
    """Get bridge history for a user."""
    history = await service.get_bridge_history(user_address, limit)
    return [
        BridgeHistoryResponse(
            id=h.request_id,
            from_chain=h.source_chain,
            to_chain=h.dest_chain,
            amount=float(h.amount),
            fee=float(h.amount * 0.005),  # 0.5% fee
            status=h.status,
            timestamp=h.timestamp,
            tx_hash=h.tx_hash
        )
        for h in history
    ]


@router.get("/pending/{user_address}", response_model=List[BridgeHistoryResponse])
async def get_pending_bridges(
    user_address: str,
    service: BridgeService = Depends(get_bridge_service)
):
    """Get pending bridge requests for a user."""
    pending = await service.get_pending_bridges(user_address)
    return [
        BridgeHistoryResponse(
            id=h.request_id,
            from_chain=h.source_chain,
            to_chain=h.dest_chain,
            amount=float(h.amount),
            fee=float(h.amount * 0.005),
            status=h.status,
            timestamp=h.timestamp,
            tx_hash=h.tx_hash
        )
        for h in pending
    ]


@router.post("/bridge", response_model=TransactionResponse)
async def initiate_bridge(
    request: BridgeRequest,
    sender_address: str,
    service: BridgeService = Depends(get_bridge_service)
):
    """Initiate a cross-chain bridge transfer."""
    try:
        tx = await service.prepare_bridge_tx(
            sender=sender_address,
            recipient=request.recipient,
            amount=request.amount,
            dest_chain=request.dest_chain
        )
        
        chain_config = await service.get_chain_config(request.dest_chain)
        chain_name = chain_config.name if chain_config else f"Chain {request.dest_chain}"
        
        return TransactionResponse(
            transaction=tx,
            message=f"Bridge {request.amount} NWR to {chain_name}"
        )
    except Exception as e:
        logger.error(f"Failed to initiate bridge: {e}")
        raise HTTPException(status_code=400, detail=str(e))
