"""
Staking Service
Backend integration for NetworkStaking smart contract.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class StakeInfo:
    """User stake information."""
    user_address: str
    amount: float
    start_time: datetime
    lock_duration_days: int
    multiplier: float
    pending_rewards: float
    tier_name: str
    can_unstake_without_penalty: bool


@dataclass
class StakingTier:
    """Staking tier configuration."""
    tier_id: int
    name: str
    min_amount: float
    multiplier: float
    min_lock_days: int


@dataclass
class StakingStats:
    """Global staking statistics."""
    total_staked: float
    reward_pool: float
    total_stakers: int
    apy_estimate: float


class StakingService:
    """Service for interacting with NetworkStaking contract."""
    
    def __init__(self, web3_url: str = None, contract_address: str = None):
        self.web3_url = web3_url or os.getenv("WEB3_PROVIDER_URL", "http://localhost:8545")
        self.contract_address = contract_address or os.getenv("STAKING_CONTRACT_ADDRESS")
        self.w3: Optional[Web3] = None
        self.contract: Optional[Contract] = None
        
        # Staking ABI (simplified)
        self.abi = [
            {"inputs": [{"name": "amount", "type": "uint256"}, {"name": "lockDays", "type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "amount", "type": "uint256"}], "name": "unstake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "claimRewards", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "user", "type": "address"}], "name": "getStakeInfo", "outputs": [{"name": "amount", "type": "uint256"}, {"name": "startTime", "type": "uint256"}, {"name": "lockDuration", "type": "uint256"}, {"name": "multiplier", "type": "uint256"}, {"name": "pendingRewards", "type": "uint256"}, {"name": "canUnstakeWithoutPenalty", "type": "bool"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "user", "type": "address"}], "name": "getVotingPower", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "tierId", "type": "uint256"}], "name": "getTier", "outputs": [{"name": "minAmount", "type": "uint256"}, {"name": "multiplier", "type": "uint256"}, {"name": "minLockDays", "type": "uint256"}, {"name": "name", "type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "totalStaked", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "rewardPool", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "tierCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
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
            logger.info(f"Connected to blockchain at {self.web3_url}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def get_stake_info(self, user_address: str) -> Optional[StakeInfo]:
        """Get staking information for a user."""
        if not self.contract:
            return None
            
        try:
            result = self.contract.functions.getStakeInfo(
                Web3.to_checksum_address(user_address)
            ).call()
            
            amount, start_time, lock_duration, multiplier, pending, can_unstake = result
            
            # Determine tier name based on multiplier
            tier_name = self._get_tier_name(multiplier)
            
            return StakeInfo(
                user_address=user_address,
                amount=Web3.from_wei(amount, 'ether'),
                start_time=datetime.fromtimestamp(start_time),
                lock_duration_days=lock_duration // 86400,
                multiplier=multiplier / 10000,
                pending_rewards=Web3.from_wei(pending, 'ether'),
                tier_name=tier_name,
                can_unstake_without_penalty=can_unstake
            )
        except Exception as e:
            logger.error(f"Failed to get stake info: {e}")
            return None
    
    def _get_tier_name(self, multiplier: int) -> str:
        """Map multiplier to tier name."""
        if multiplier >= 30000:
            return "Diamond"
        elif multiplier >= 20000:
            return "Platinum"
        elif multiplier >= 15000:
            return "Gold"
        elif multiplier >= 12500:
            return "Silver"
        return "Bronze"
    
    async def get_tiers(self) -> List[StakingTier]:
        """Get all staking tiers."""
        if not self.contract:
            # Return default tiers
            return [
                StakingTier(0, "Bronze", 1000, 1.0, 7),
                StakingTier(1, "Silver", 10000, 1.25, 30),
                StakingTier(2, "Gold", 50000, 1.5, 90),
                StakingTier(3, "Platinum", 100000, 2.0, 180),
                StakingTier(4, "Diamond", 500000, 3.0, 365),
            ]
        
        try:
            tier_count = self.contract.functions.tierCount().call()
            tiers = []
            
            for i in range(tier_count):
                result = self.contract.functions.getTier(i).call()
                min_amount, multiplier, min_lock, name = result
                
                tiers.append(StakingTier(
                    tier_id=i,
                    name=name,
                    min_amount=Web3.from_wei(min_amount, 'ether'),
                    multiplier=multiplier / 10000,
                    min_lock_days=min_lock
                ))
            
            return tiers
        except Exception as e:
            logger.error(f"Failed to get tiers: {e}")
            return []
    
    async def get_voting_power(self, user_address: str) -> float:
        """Get voting power for a user."""
        if not self.contract:
            return 0
            
        try:
            power = self.contract.functions.getVotingPower(
                Web3.to_checksum_address(user_address)
            ).call()
            return Web3.from_wei(power, 'ether')
        except Exception as e:
            logger.error(f"Failed to get voting power: {e}")
            return 0
    
    async def get_stats(self) -> StakingStats:
        """Get global staking statistics."""
        if not self.contract:
            return StakingStats(
                total_staked=0,
                reward_pool=0,
                total_stakers=0,
                apy_estimate=12.5
            )
        
        try:
            total_staked = self.contract.functions.totalStaked().call()
            reward_pool = self.contract.functions.rewardPool().call()
            
            return StakingStats(
                total_staked=Web3.from_wei(total_staked, 'ether'),
                reward_pool=Web3.from_wei(reward_pool, 'ether'),
                total_stakers=0,  # Would need to track separately
                apy_estimate=12.5  # Estimated APY
            )
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return StakingStats(0, 0, 0, 0)
    
    async def prepare_stake_tx(
        self,
        user_address: str,
        amount: float,
        lock_days: int
    ) -> Dict:
        """Prepare stake transaction for signing."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        amount_wei = Web3.to_wei(amount, 'ether')
        
        tx = self.contract.functions.stake(
            amount_wei, lock_days
        ).build_transaction({
            'from': Web3.to_checksum_address(user_address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(user_address)
            ),
        })
        
        return tx
    
    async def prepare_unstake_tx(
        self,
        user_address: str,
        amount: float
    ) -> Dict:
        """Prepare unstake transaction for signing."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        amount_wei = Web3.to_wei(amount, 'ether')
        
        tx = self.contract.functions.unstake(
            amount_wei
        ).build_transaction({
            'from': Web3.to_checksum_address(user_address),
            'gas': 150000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(user_address)
            ),
        })
        
        return tx
    
    async def prepare_claim_tx(self, user_address: str) -> Dict:
        """Prepare claim rewards transaction."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        tx = self.contract.functions.claimRewards().build_transaction({
            'from': Web3.to_checksum_address(user_address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(user_address)
            ),
        })
        
        return tx


# Singleton instance
staking_service = StakingService()


async def get_staking_service() -> StakingService:
    """Get staking service instance."""
    if staking_service.w3 is None:
        await staking_service.connect()
    return staking_service
