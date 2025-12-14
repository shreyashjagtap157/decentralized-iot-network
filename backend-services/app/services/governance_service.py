"""
Governance Service
Backend integration for NetworkGovernance smart contract.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from web3 import Web3
from web3.contract import Contract
import os

logger = logging.getLogger(__name__)


class ProposalState(Enum):
    PENDING = 0
    ACTIVE = 1
    CANCELED = 2
    DEFEATED = 3
    SUCCEEDED = 4
    QUEUED = 5
    EXECUTED = 6
    EXPIRED = 7


class ProposalType(Enum):
    PARAMETER_CHANGE = 0
    ORACLE_UPDATE = 1
    EMERGENCY_ACTION = 2
    PROTOCOL_UPGRADE = 3
    TREASURY_SPEND = 4


@dataclass
class Proposal:
    """Governance proposal."""
    id: int
    proposer: str
    proposal_type: ProposalType
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    for_votes: float
    against_votes: float
    abstain_votes: float
    state: ProposalState
    executed: bool
    canceled: bool


@dataclass
class VoteReceipt:
    """User vote receipt."""
    proposal_id: int
    voter: str
    has_voted: bool
    support: int  # 0=against, 1=for, 2=abstain
    votes: float


@dataclass
class GovernanceParams:
    """Governance parameters."""
    voting_delay: int      # seconds
    voting_period: int     # seconds
    proposal_threshold: float
    quorum_votes: float
    timelock_delay: int    # seconds


class GovernanceService:
    """Service for interacting with NetworkGovernance contract."""
    
    def __init__(self, web3_url: str = None, contract_address: str = None):
        self.web3_url = web3_url or os.getenv("WEB3_PROVIDER_URL", "http://localhost:8545")
        self.contract_address = contract_address or os.getenv("GOVERNANCE_CONTRACT_ADDRESS")
        self.w3: Optional[Web3] = None
        self.contract: Optional[Contract] = None
        
        # Governance ABI (simplified)
        self.abi = [
            {"inputs": [{"name": "proposalType", "type": "uint8"}, {"name": "title", "type": "string"}, {"name": "description", "type": "string"}, {"name": "target", "type": "address"}, {"name": "callData", "type": "bytes"}, {"name": "value", "type": "uint256"}], "name": "propose", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "support", "type": "uint8"}], "name": "castVote", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "execute", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "cancel", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "state", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "getProposalInfo", "outputs": [{"name": "id", "type": "uint256"}, {"name": "proposer", "type": "address"}, {"name": "proposalType", "type": "uint8"}, {"name": "title", "type": "string"}, {"name": "description", "type": "string"}, {"name": "startTime", "type": "uint256"}, {"name": "endTime", "type": "uint256"}, {"name": "forVotes", "type": "uint256"}, {"name": "againstVotes", "type": "uint256"}, {"name": "abstainVotes", "type": "uint256"}, {"name": "executed", "type": "bool"}, {"name": "canceled", "type": "bool"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "voter", "type": "address"}], "name": "getReceipt", "outputs": [{"name": "hasVoted", "type": "bool"}, {"name": "support", "type": "uint8"}, {"name": "votes", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "proposalCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "votingDelay", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "votingPeriod", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "proposalThreshold", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "quorumVotes", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
    
    async def connect(self):
        """Connect to blockchain."""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.web3_url))
            if self.contract_address:
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self.abi
                )
            logger.info(f"Governance service connected")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def get_proposal(self, proposal_id: int) -> Optional[Proposal]:
        """Get proposal details."""
        if not self.contract:
            return None
        
        try:
            info = self.contract.functions.getProposalInfo(proposal_id).call()
            state = self.contract.functions.state(proposal_id).call()
            
            return Proposal(
                id=info[0],
                proposer=info[1],
                proposal_type=ProposalType(info[2]),
                title=info[3],
                description=info[4],
                start_time=datetime.fromtimestamp(info[5]),
                end_time=datetime.fromtimestamp(info[6]),
                for_votes=Web3.from_wei(info[7], 'ether'),
                against_votes=Web3.from_wei(info[8], 'ether'),
                abstain_votes=Web3.from_wei(info[9], 'ether'),
                state=ProposalState(state),
                executed=info[10],
                canceled=info[11]
            )
        except Exception as e:
            logger.error(f"Failed to get proposal: {e}")
            return None
    
    async def get_proposals(self, limit: int = 20, offset: int = 0) -> List[Proposal]:
        """Get list of proposals."""
        if not self.contract:
            return []
        
        try:
            count = self.contract.functions.proposalCount().call()
            proposals = []
            
            start = max(1, count - offset - limit + 1)
            end = count - offset
            
            for i in range(end, start - 1, -1):
                proposal = await self.get_proposal(i)
                if proposal:
                    proposals.append(proposal)
            
            return proposals
        except Exception as e:
            logger.error(f"Failed to get proposals: {e}")
            return []
    
    async def get_active_proposals(self) -> List[Proposal]:
        """Get only active proposals."""
        proposals = await self.get_proposals(limit=50)
        return [p for p in proposals if p.state == ProposalState.ACTIVE]
    
    async def get_vote_receipt(self, proposal_id: int, voter: str) -> Optional[VoteReceipt]:
        """Get vote receipt for a user."""
        if not self.contract:
            return None
        
        try:
            result = self.contract.functions.getReceipt(
                proposal_id,
                Web3.to_checksum_address(voter)
            ).call()
            
            return VoteReceipt(
                proposal_id=proposal_id,
                voter=voter,
                has_voted=result[0],
                support=result[1],
                votes=Web3.from_wei(result[2], 'ether')
            )
        except Exception as e:
            logger.error(f"Failed to get receipt: {e}")
            return None
    
    async def get_governance_params(self) -> GovernanceParams:
        """Get governance parameters."""
        if not self.contract:
            return GovernanceParams(
                voting_delay=86400,
                voting_period=604800,
                proposal_threshold=10000,
                quorum_votes=100000,
                timelock_delay=172800
            )
        
        try:
            return GovernanceParams(
                voting_delay=self.contract.functions.votingDelay().call(),
                voting_period=self.contract.functions.votingPeriod().call(),
                proposal_threshold=Web3.from_wei(
                    self.contract.functions.proposalThreshold().call(), 'ether'
                ),
                quorum_votes=Web3.from_wei(
                    self.contract.functions.quorumVotes().call(), 'ether'
                ),
                timelock_delay=172800  # Default 2 days
            )
        except Exception as e:
            logger.error(f"Failed to get params: {e}")
            return GovernanceParams(86400, 604800, 10000, 100000, 172800)
    
    async def prepare_propose_tx(
        self,
        proposer: str,
        proposal_type: ProposalType,
        title: str,
        description: str,
        target: str = None,
        call_data: bytes = b'',
        value: int = 0
    ) -> Dict:
        """Prepare proposal creation transaction."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        target = target or "0x0000000000000000000000000000000000000000"
        
        tx = self.contract.functions.propose(
            proposal_type.value,
            title,
            description,
            Web3.to_checksum_address(target),
            call_data,
            value
        ).build_transaction({
            'from': Web3.to_checksum_address(proposer),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(proposer)
            ),
        })
        
        return tx
    
    async def prepare_vote_tx(
        self,
        voter: str,
        proposal_id: int,
        support: int  # 0=against, 1=for, 2=abstain
    ) -> Dict:
        """Prepare vote transaction."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        tx = self.contract.functions.castVote(
            proposal_id, support
        ).build_transaction({
            'from': Web3.to_checksum_address(voter),
            'gas': 150000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(voter)
            ),
        })
        
        return tx
    
    async def prepare_execute_tx(self, executor: str, proposal_id: int) -> Dict:
        """Prepare execute proposal transaction."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        tx = self.contract.functions.execute(
            proposal_id
        ).build_transaction({
            'from': Web3.to_checksum_address(executor),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(executor)
            ),
        })
        
        return tx


# Singleton instance
governance_service = GovernanceService()


async def get_governance_service() -> GovernanceService:
    """Get governance service instance."""
    if governance_service.w3 is None:
        await governance_service.connect()
    return governance_service
