"""
NFT Service
Backend integration for DeviceNFT smart contract.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from web3 import Web3
import os
import json

logger = logging.getLogger(__name__)


@dataclass
class DeviceNFT:
    """Device NFT representation."""
    token_id: int
    device_id: str
    device_type: str
    owner: str
    registration_date: datetime
    total_rewards_earned: float
    total_data_transferred: float  # GB
    quality_score: int
    is_active: bool
    token_uri: str
    image_url: Optional[str]


@dataclass
class NFTMetadata:
    """NFT metadata for IPFS."""
    name: str
    description: str
    image: str
    attributes: List[Dict]


class NFTService:
    """Service for interacting with DeviceNFT contract."""
    
    def __init__(self, web3_url: str = None, contract_address: str = None):
        self.web3_url = web3_url or os.getenv("WEB3_PROVIDER_URL", "http://localhost:8545")
        self.contract_address = contract_address or os.getenv("NFT_CONTRACT_ADDRESS")
        self.w3: Optional[Web3] = None
        self.contract = None
        self.base_uri = os.getenv("NFT_BASE_URI", "https://api.iot-network.io/nft/")
        
        # Simplified ABI
        self.abi = [
            {"inputs": [{"name": "to", "type": "address"}, {"name": "deviceId", "type": "string"}, {"name": "deviceType", "type": "string"}, {"name": "tokenURI", "type": "string"}], "name": "mintDevice", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "deviceId", "type": "string"}, {"name": "rewardsEarned", "type": "uint256"}, {"name": "dataTransferred", "type": "uint256"}, {"name": "qualityScore", "type": "uint256"}], "name": "updateDeviceStats", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "deviceId", "type": "string"}], "name": "deactivateDevice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "tokenId", "type": "uint256"}], "name": "getDeviceMetadata", "outputs": [{"name": "deviceId", "type": "string"}, {"name": "deviceType", "type": "string"}, {"name": "registrationDate", "type": "uint256"}, {"name": "totalRewardsEarned", "type": "uint256"}, {"name": "totalDataTransferred", "type": "uint256"}, {"name": "qualityScore", "type": "uint256"}, {"name": "isActive", "type": "bool"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "deviceId", "type": "string"}], "name": "getDeviceByDeviceId", "outputs": [{"name": "tokenId", "type": "uint256"}, {"name": "metadata", "type": "tuple", "components": [{"name": "deviceId", "type": "string"}, {"name": "deviceType", "type": "string"}, {"name": "registrationDate", "type": "uint256"}, {"name": "totalRewardsEarned", "type": "uint256"}, {"name": "totalDataTransferred", "type": "uint256"}, {"name": "qualityScore", "type": "uint256"}, {"name": "isActive", "type": "bool"}]}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "owner", "type": "address"}], "name": "getOwnerDevices", "outputs": [{"name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "totalDevices", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "tokenId", "type": "uint256"}], "name": "ownerOf", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "tokenId", "type": "uint256"}], "name": "tokenURI", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
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
            logger.info("NFT service connected")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def get_device_nft(self, token_id: int) -> Optional[DeviceNFT]:
        """Get NFT by token ID."""
        if not self.contract:
            return None
        
        try:
            owner = self.contract.functions.ownerOf(token_id).call()
            metadata = self.contract.functions.getDeviceMetadata(token_id).call()
            token_uri = self.contract.functions.tokenURI(token_id).call()
            
            device_id, device_type, reg_date, rewards, data, quality, is_active = metadata
            
            return DeviceNFT(
                token_id=token_id,
                device_id=device_id,
                device_type=device_type,
                owner=owner,
                registration_date=datetime.fromtimestamp(reg_date),
                total_rewards_earned=Web3.from_wei(rewards, 'ether'),
                total_data_transferred=data / (1024 ** 3),  # Convert to GB
                quality_score=quality,
                is_active=is_active,
                token_uri=token_uri,
                image_url=f"{self.base_uri}{token_id}/image.png"
            )
        except Exception as e:
            logger.error(f"Failed to get NFT: {e}")
            return None
    
    async def get_device_by_device_id(self, device_id: str) -> Optional[DeviceNFT]:
        """Get NFT by device ID."""
        if not self.contract:
            return None
        
        try:
            result = self.contract.functions.getDeviceByDeviceId(device_id).call()
            token_id = result[0]
            
            if token_id == 0:
                return None
            
            return await self.get_device_nft(token_id)
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            return None
    
    async def get_user_devices(self, owner: str) -> List[DeviceNFT]:
        """Get all NFTs owned by a user."""
        if not self.contract:
            return []
        
        try:
            token_ids = self.contract.functions.getOwnerDevices(
                Web3.to_checksum_address(owner)
            ).call()
            
            devices = []
            for token_id in token_ids:
                device = await self.get_device_nft(token_id)
                if device:
                    devices.append(device)
            
            return devices
        except Exception as e:
            logger.error(f"Failed to get user devices: {e}")
            return []
    
    async def get_total_devices(self) -> int:
        """Get total number of device NFTs."""
        if not self.contract:
            return 0
        
        try:
            return self.contract.functions.totalDevices().call()
        except Exception as e:
            logger.error(f"Failed to get total: {e}")
            return 0
    
    def generate_metadata(
        self,
        device_id: str,
        device_type: str,
        quality_score: int = 100
    ) -> NFTMetadata:
        """Generate NFT metadata for IPFS."""
        tier = self._get_device_tier(quality_score)
        
        return NFTMetadata(
            name=f"IoT Device #{device_id[:8]}",
            description=f"A verified {device_type} device on the IoT Network. "
                       f"This NFT represents ownership and tracks earnings from network participation.",
            image=f"{self.base_uri}images/{device_type.lower()}.png",
            attributes=[
                {"trait_type": "Device Type", "value": device_type},
                {"trait_type": "Device ID", "value": device_id},
                {"trait_type": "Quality Tier", "value": tier},
                {"trait_type": "Quality Score", "value": quality_score, "max_value": 100},
                {"trait_type": "Status", "value": "Active"},
            ]
        )
    
    def _get_device_tier(self, quality_score: int) -> str:
        """Get tier based on quality score."""
        if quality_score >= 90:
            return "Diamond"
        elif quality_score >= 75:
            return "Gold"
        elif quality_score >= 50:
            return "Silver"
        return "Bronze"
    
    async def prepare_mint_tx(
        self,
        owner: str,
        device_id: str,
        device_type: str
    ) -> Dict:
        """Prepare mint transaction for signing."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        metadata = self.generate_metadata(device_id, device_type)
        token_uri = f"{self.base_uri}metadata/{device_id}.json"
        
        tx = self.contract.functions.mintDevice(
            Web3.to_checksum_address(owner),
            device_id,
            device_type,
            token_uri
        ).build_transaction({
            'from': Web3.to_checksum_address(owner),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(owner)
            ),
        })
        
        return {
            'transaction': tx,
            'metadata': metadata.__dict__
        }
    
    async def prepare_deactivate_tx(self, owner: str, device_id: str) -> Dict:
        """Prepare deactivate transaction."""
        if not self.contract:
            raise Exception("Contract not connected")
        
        tx = self.contract.functions.deactivateDevice(
            device_id
        ).build_transaction({
            'from': Web3.to_checksum_address(owner),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(
                Web3.to_checksum_address(owner)
            ),
        })
        
        return tx


# Singleton instance
nft_service = NFTService()


async def get_nft_service() -> NFTService:
    """Get NFT service instance."""
    if nft_service.w3 is None:
        await nft_service.connect()
    return nft_service
