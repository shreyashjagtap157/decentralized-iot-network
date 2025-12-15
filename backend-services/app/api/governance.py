"""
Governance API Routes
REST endpoints for DAO governance functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import logging

from app.services.governance_service import (
    get_governance_service, GovernanceService,
    ProposalState, ProposalType
)
from app.api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/governance", tags=["governance"])


# ==================== Schemas ====================

class ProposalTypeEnum(str, Enum):
    parameter = "parameter"
    oracle = "oracle"
    emergency = "emergency"
    upgrade = "upgrade"
    treasury = "treasury"


class CreateProposalRequest(BaseModel):
    proposal_type: ProposalTypeEnum
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    target_address: Optional[str] = None
    call_data: Optional[str] = None
    value: int = 0


class VoteRequest(BaseModel):
    support: int = Field(..., ge=0, le=2, description="0=Against, 1=For, 2=Abstain")


class ProposalResponse(BaseModel):
    id: int
    proposer: str
    proposal_type: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    for_votes: float
    against_votes: float
    abstain_votes: float
    state: str
    executed: bool
    canceled: bool


class VoteReceiptResponse(BaseModel):
    proposal_id: int
    voter: str
    has_voted: bool
    support: int
    votes: float


class GovernanceParamsResponse(BaseModel):
    voting_delay: int
    voting_period: int
    proposal_threshold: float
    quorum_votes: float
    timelock_delay: int


class TransactionResponse(BaseModel):
    transaction: dict
    message: str


# ==================== Endpoints ====================

@router.get("/params", response_model=GovernanceParamsResponse)
async def get_governance_params(
    service: GovernanceService = Depends(get_governance_service)
):
    """Get governance parameters."""
    params = await service.get_governance_params()
    return GovernanceParamsResponse(
        voting_delay=params.voting_delay,
        voting_period=params.voting_period,
        proposal_threshold=float(params.proposal_threshold),
        quorum_votes=float(params.quorum_votes),
        timelock_delay=params.timelock_delay
    )


@router.get("/proposals", response_model=List[ProposalResponse])
async def get_proposals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: GovernanceService = Depends(get_governance_service)
):
    """Get list of proposals."""
    proposals = await service.get_proposals(limit=limit, offset=offset)
    return [
        ProposalResponse(
            id=p.id,
            proposer=p.proposer,
            proposal_type=p.proposal_type.name.lower(),
            title=p.title,
            description=p.description,
            start_time=p.start_time,
            end_time=p.end_time,
            for_votes=float(p.for_votes),
            against_votes=float(p.against_votes),
            abstain_votes=float(p.abstain_votes),
            state=p.state.name.lower(),
            executed=p.executed,
            canceled=p.canceled
        )
        for p in proposals
    ]


@router.get("/proposals/active", response_model=List[ProposalResponse])
async def get_active_proposals(
    service: GovernanceService = Depends(get_governance_service)
):
    """Get only active proposals that can be voted on."""
    proposals = await service.get_active_proposals()
    return [
        ProposalResponse(
            id=p.id,
            proposer=p.proposer,
            proposal_type=p.proposal_type.name.lower(),
            title=p.title,
            description=p.description,
            start_time=p.start_time,
            end_time=p.end_time,
            for_votes=float(p.for_votes),
            against_votes=float(p.against_votes),
            abstain_votes=float(p.abstain_votes),
            state=p.state.name.lower(),
            executed=p.executed,
            canceled=p.canceled
        )
        for p in proposals
    ]


@router.get("/proposals/{proposal_id}", response_model=Optional[ProposalResponse])
async def get_proposal(
    proposal_id: int,
    service: GovernanceService = Depends(get_governance_service)
):
    """Get a specific proposal by ID."""
    proposal = await service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return ProposalResponse(
        id=proposal.id,
        proposer=proposal.proposer,
        proposal_type=proposal.proposal_type.name.lower(),
        title=proposal.title,
        description=proposal.description,
        start_time=proposal.start_time,
        end_time=proposal.end_time,
        for_votes=float(proposal.for_votes),
        against_votes=float(proposal.against_votes),
        abstain_votes=float(proposal.abstain_votes),
        state=proposal.state.name.lower(),
        executed=proposal.executed,
        canceled=proposal.canceled
    )


@router.get("/proposals/{proposal_id}/receipt/{voter}", response_model=Optional[VoteReceiptResponse])
async def get_vote_receipt(
    proposal_id: int,
    voter: str,
    service: GovernanceService = Depends(get_governance_service)
):
    """Get vote receipt for a specific voter on a proposal."""
    receipt = await service.get_vote_receipt(proposal_id, voter)
    if not receipt:
        return None
    
    return VoteReceiptResponse(
        proposal_id=receipt.proposal_id,
        voter=receipt.voter,
        has_voted=receipt.has_voted,
        support=receipt.support,
        votes=float(receipt.votes)
    )


@router.post("/proposals", response_model=TransactionResponse)
async def create_proposal(
    request: CreateProposalRequest,
    proposer_address: str,
    service: GovernanceService = Depends(get_governance_service)
):
    """Create a new governance proposal."""
    try:
        proposal_type_map = {
            "parameter": ProposalType.PARAMETER_CHANGE,
            "oracle": ProposalType.ORACLE_UPDATE,
            "emergency": ProposalType.EMERGENCY_ACTION,
            "upgrade": ProposalType.PROTOCOL_UPGRADE,
            "treasury": ProposalType.TREASURY_SPEND,
        }
        
        tx = await service.prepare_propose_tx(
            proposer=proposer_address,
            proposal_type=proposal_type_map[request.proposal_type.value],
            title=request.title,
            description=request.description,
            target=request.target_address,
            call_data=bytes.fromhex(request.call_data[2:]) if request.call_data else b'',
            value=request.value
        )
        return TransactionResponse(
            transaction=tx,
            message=f"Create proposal: {request.title}"
        )
    except Exception as e:
        logger.error(f"Failed to create proposal: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/vote", response_model=TransactionResponse)
async def vote_on_proposal(
    proposal_id: int,
    request: VoteRequest,
    voter_address: str,
    service: GovernanceService = Depends(get_governance_service)
):
    """Cast a vote on a proposal."""
    try:
        tx = await service.prepare_vote_tx(
            voter=voter_address,
            proposal_id=proposal_id,
            support=request.support
        )
        vote_type = ["Against", "For", "Abstain"][request.support]
        return TransactionResponse(
            transaction=tx,
            message=f"Vote {vote_type} on proposal #{proposal_id}"
        )
    except Exception as e:
        logger.error(f"Failed to vote: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/execute", response_model=TransactionResponse)
async def execute_proposal(
    proposal_id: int,
    executor_address: str,
    service: GovernanceService = Depends(get_governance_service)
):
    """Execute a succeeded proposal."""
    try:
        tx = await service.prepare_execute_tx(executor_address, proposal_id)
        return TransactionResponse(
            transaction=tx,
            message=f"Execute proposal #{proposal_id}"
        )
    except Exception as e:
        logger.error(f"Failed to execute: {e}")
        raise HTTPException(status_code=400, detail=str(e))
