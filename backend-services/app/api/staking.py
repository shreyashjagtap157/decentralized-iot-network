"""
Staking API Routes
REST endpoints for staking functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import logging
import re

from app.services.staking_service import get_staking_service, StakingService
from app.api.dependencies import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/staking", tags=["staking"])

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Ethereum address validation regex
ETH_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')

def validate_eth_address(address: str) -> str:
    """Validate Ethereum address format"""
    if not ETH_ADDRESS_PATTERN.match(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Ethereum address format"
        )
    return address


# ==================== Schemas ====================

class StakeRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to stake")
    lock_days: int = Field(..., ge=7, le=730, description="Lock duration in days")


class UnstakeRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to unstake")


class StakeInfoResponse(BaseModel):
    user_address: str
    amount: float
    start_time: datetime
    lock_duration_days: int
    multiplier: float
    pending_rewards: float
    tier_name: str
    can_unstake_without_penalty: bool


class StakingTierResponse(BaseModel):
    tier_id: int
    name: str
    min_amount: float
    multiplier: float
    min_lock_days: int


class StakingStatsResponse(BaseModel):
    total_staked: float
    reward_pool: float
    total_stakers: int
    apy_estimate: float


class TransactionResponse(BaseModel):
    transaction: dict
    message: str


# ==================== Endpoints ====================

@router.get("/stats", response_model=StakingStatsResponse)
async def get_staking_stats(
    service: StakingService = Depends(get_staking_service)
):
    """Get global staking statistics."""
    stats = await service.get_stats()
    return StakingStatsResponse(
        total_staked=float(stats.total_staked),
        reward_pool=float(stats.reward_pool),
        total_stakers=stats.total_stakers,
        apy_estimate=stats.apy_estimate
    )


@router.get("/tiers", response_model=List[StakingTierResponse])
async def get_staking_tiers(
    service: StakingService = Depends(get_staking_service)
):
    """Get all available staking tiers."""
    tiers = await service.get_tiers()
    return [
        StakingTierResponse(
            tier_id=t.tier_id,
            name=t.name,
            min_amount=float(t.min_amount),
            multiplier=t.multiplier,
            min_lock_days=t.min_lock_days
        )
        for t in tiers
    ]


@router.get("/info/{user_address}", response_model=Optional[StakeInfoResponse])
async def get_stake_info(
    user_address: str,
    service: StakingService = Depends(get_staking_service)
):
    """Get staking information for a user."""
    info = await service.get_stake_info(user_address)
    if not info:
        return None
    
    return StakeInfoResponse(
        user_address=info.user_address,
        amount=float(info.amount),
        start_time=info.start_time,
        lock_duration_days=info.lock_duration_days,
        multiplier=info.multiplier,
        pending_rewards=float(info.pending_rewards),
        tier_name=info.tier_name,
        can_unstake_without_penalty=info.can_unstake_without_penalty
    )


@router.get("/voting-power/{user_address}")
async def get_voting_power(
    user_address: str,
    service: StakingService = Depends(get_staking_service)
):
    """Get voting power for a user based on their stake."""
    power = await service.get_voting_power(user_address)
    return {"user_address": user_address, "voting_power": float(power)}


@router.post("/stake", response_model=TransactionResponse)
@limiter.limit("5/minute")
async def prepare_stake(
    request: Request,
    stake_request: StakeRequest,
    user_address: str,
    service: StakingService = Depends(get_staking_service)
):
    """Prepare a stake transaction for signing."""
    validate_eth_address(user_address)
    try:
        tx = await service.prepare_stake_tx(
            user_address=user_address,
            amount=stake_request.amount,
            lock_days=stake_request.lock_days
        )
        return TransactionResponse(
            transaction=tx,
            message=f"Stake {stake_request.amount} NWR for {stake_request.lock_days} days"
        )
    except Exception as e:
        logger.error(f"Failed to prepare stake: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/unstake", response_model=TransactionResponse)
@limiter.limit("5/minute")
async def prepare_unstake(
    request: Request,
    unstake_request: UnstakeRequest,
    user_address: str,
    service: StakingService = Depends(get_staking_service)
):
    """Prepare an unstake transaction for signing."""
    validate_eth_address(user_address)
    try:
        tx = await service.prepare_unstake_tx(
            user_address=user_address,
            amount=unstake_request.amount
        )
        return TransactionResponse(
            transaction=tx,
            message=f"Unstake {unstake_request.amount} NWR"
        )
    except Exception as e:
        logger.error(f"Failed to prepare unstake: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/claim", response_model=TransactionResponse)
@limiter.limit("10/minute")
async def prepare_claim_rewards(
    request: Request,
    user_address: str,
    service: StakingService = Depends(get_staking_service)
):
    """Prepare a claim rewards transaction for signing."""
    validate_eth_address(user_address)
    try:
        tx = await service.prepare_claim_tx(user_address)
        return TransactionResponse(
            transaction=tx,
            message="Claim pending staking rewards"
        )
    except Exception as e:
        logger.error(f"Failed to prepare claim: {e}")
        raise HTTPException(status_code=400, detail=str(e))
