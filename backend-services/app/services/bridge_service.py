"""
Bridge Service
Backend integration for CrossChainBridge smart contract.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from web3 import Web3
import os

logger = logging.getLogger(__name__)


class ChainId(Enum):
    ETHEREUM = 1
    POLYGON = 137
    BSC = 56
    ARBITRUM = 42161
    OPTIMISM = 10


@dataclass
class ChainConfig:
    """Chain configuration."""
    chain_id: int
    name: str
    enabled: bool
    min_amount: float
    max_amount: float
    daily_limit: float
    daily_remaining: float
    rpc_url: str
    explorer_url: str


@dataclass
class BridgeRequest:
    """Bridge transfer request."""
    request_id: str
    sender: str
    recipient: str
    amount: float
    source_chain: int
    dest_chain: int
    timestamp: datetime
    status: str  # pending, completed, failed
    tx_hash: Optional[str]


@dataclass
class BridgeStats:
    """Bridge statistics."""
    total_bridged: float
    total_fees_collected: float
    pending_requests: int
    completed_requests: int


class BridgeService:
    """Service for cross-chain bridge operations."""
    
    CHAIN_NAMES = {
        1: "Ethereum",
        137: "Polygon",
        56: "BNB Chain",
        42161: "Arbitrum",
        10: "Optimism"
    }
    
    CHAIN_EXPLORERS = {
        1: "https://etherscan.io",
        137: "https://polygonscan.com",
        56: "https://bscscan.com",
        42161: "https://arbiscan.io",
        10: "https://optimistic.etherscan.io"
    }
    
    def __init__(self):
        self.web3_providers: Dict[int, Web3] = {}
        self.contracts: Dict[int, any] = {}
        self.current_chain_id = int(os.getenv("CHAIN_ID", "1"))
        self.fee_basis_points = 50  # 0.5%
        
        # Simplified ABI
        self.abi = [
            {"inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}, {"name": "destChain", "type": "uint256"}], "name": "bridge", "outputs": [{"name": "", "type": "bytes32"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "chainId", "type": "uint256"}], "name": "getChainConfig", "outputs": [{"name": "enabled", "type": "bool"}, {"name": "minAmount", "type": "uint256"}, {"name": "maxAmount", "type": "uint256"}, {"name": "dailyLimit", "type": "uint256"}, {"name": "dailyRemaining", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "getSupportedChains", "outputs": [{"name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "amount", "type": "uint256"}], "name": "estimateFee", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "requestId", "type": "bytes32"}], "name": "getRequest", "outputs": [{"name": "sender", "type": "address"}, {"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}, {"name": "sourceChain", "type": "uint256"}, {"name": "destChain", "type": "uint256"}, {"name": "timestamp", "type": "uint256"}, {"name": "processed", "type": "bool"}], "stateMutability": "view", "type": "function"},
        ]
    
    async def connect(self, chain_id: int, rpc_url: str, contract_address: str):
        """Connect to a specific chain."""
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            self.web3_providers[chain_id] = w3
            
            if contract_address:
                self.contracts[chain_id] = w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=self.abi
                )
            
            logger.info(f"Connected to chain {chain_id}")
        except Exception as e:
            logger.error(f"Failed to connect to chain {chain_id}: {e}")
            raise
    
    async def get_supported_chains(self) -> List[ChainConfig]:
        """Get list of supported chains."""
        chains = []
        
        for chain_id in [1, 137, 56, 42161, 10]:
            if chain_id == self.current_chain_id:
                continue
            
            config = await self.get_chain_config(chain_id)
            if config:
                chains.append(config)
        
        # Return default chains if no contract connection
        if not chains:
            for chain_id, name in self.CHAIN_NAMES.items():
                if chain_id != self.current_chain_id:
                    chains.append(ChainConfig(
                        chain_id=chain_id,
                        name=name,
                        enabled=True,
                        min_amount=10,
                        max_amount=1000000,
                        daily_limit=10000000,
                        daily_remaining=10000000,
                        rpc_url="",
                        explorer_url=self.CHAIN_EXPLORERS.get(chain_id, "")
                    ))
        
        return chains
    
    async def get_chain_config(self, chain_id: int) -> Optional[ChainConfig]:
        """Get configuration for a specific chain."""
        contract = self.contracts.get(self.current_chain_id)
        
        if not contract:
            return ChainConfig(
                chain_id=chain_id,
                name=self.CHAIN_NAMES.get(chain_id, f"Chain {chain_id}"),
                enabled=True,
                min_amount=10,
                max_amount=1000000,
                daily_limit=10000000,
                daily_remaining=10000000,
                rpc_url="",
                explorer_url=self.CHAIN_EXPLORERS.get(chain_id, "")
            )
        
        try:
            result = contract.functions.getChainConfig(chain_id).call()
            enabled, min_amt, max_amt, daily_limit, daily_remaining = result
            
            return ChainConfig(
                chain_id=chain_id,
                name=self.CHAIN_NAMES.get(chain_id, f"Chain {chain_id}"),
                enabled=enabled,
                min_amount=Web3.from_wei(min_amt, 'ether'),
                max_amount=Web3.from_wei(max_amt, 'ether'),
                daily_limit=Web3.from_wei(daily_limit, 'ether'),
                daily_remaining=Web3.from_wei(daily_remaining, 'ether'),
                rpc_url="",
                explorer_url=self.CHAIN_EXPLORERS.get(chain_id, "")
            )
        except Exception as e:
            logger.error(f"Failed to get chain config: {e}")
            return None
    
    async def estimate_fee(self, amount: float) -> float:
        """Estimate bridge fee for an amount."""
        return amount * self.fee_basis_points / 10000
    
    async def estimate_received(self, amount: float) -> float:
        """Estimate amount received after fees."""
        fee = await self.estimate_fee(amount)
        return amount - fee
    
    async def prepare_bridge_tx(
        self,
        sender: str,
        recipient: str,
        amount: float,
        dest_chain: int
    ) -> Dict:
        """Prepare bridge transaction for signing."""
        contract = self.contracts.get(self.current_chain_id)
        w3 = self.web3_providers.get(self.current_chain_id)
        
        if not contract or not w3:
            raise Exception("Not connected to current chain")
        
        # Validate amount
        chain_config = await self.get_chain_config(dest_chain)
        if not chain_config or not chain_config.enabled:
            raise Exception(f"Chain {dest_chain} not supported")
        
        if amount < chain_config.min_amount:
            raise Exception(f"Amount below minimum ({chain_config.min_amount})")
        
        if amount > chain_config.max_amount:
            raise Exception(f"Amount above maximum ({chain_config.max_amount})")
        
        amount_wei = Web3.to_wei(amount, 'ether')
        
        tx = contract.functions.bridge(
            Web3.to_checksum_address(recipient),
            amount_wei,
            dest_chain
        ).build_transaction({
            'from': Web3.to_checksum_address(sender),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(
                Web3.to_checksum_address(sender)
            ),
        })
        
        return tx
    
    async def get_bridge_history(
        self,
        user_address: str,
        limit: int = 20
    ) -> List[BridgeRequest]:
        """Get bridge history for a user."""
        # In production, this would query from database/indexer
        return []
    
    async def get_pending_bridges(self, user_address: str) -> List[BridgeRequest]:
        """Get pending bridge requests for a user."""
        history = await self.get_bridge_history(user_address, limit=50)
        return [r for r in history if r.status == "pending"]
    
    async def get_stats(self) -> BridgeStats:
        """Get bridge statistics."""
        return BridgeStats(
            total_bridged=0,
            total_fees_collected=0,
            pending_requests=0,
            completed_requests=0
        )


# Singleton instance
bridge_service = BridgeService()


async def get_bridge_service() -> BridgeService:
    """Get bridge service instance."""
    return bridge_service
