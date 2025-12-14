import os
import json
from web3 import Web3
from web3.exceptions import ContractLogicError
from app.core.config import settings
from app.core.logging import logger

# Contract ABI - should be loaded from compiled contract
NETWORK_COMPENSATION_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "deviceId", "type": "string"},
            {"internalType": "uint256", "name": "bytesTransmitted", "type": "uint256"},
            {"internalType": "uint256", "name": "qualityScore", "type": "uint256"}
        ],
        "name": "submitUsageData",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "deviceId", "type": "string"},
            {"internalType": "address", "name": "deviceOwner", "type": "address"}
        ],
        "name": "registerDevice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class BlockchainService:
    def __init__(self):
        provider_url = settings.WEB3_PROVIDER_URL
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = None
        self.oracle_account = None
        self._load_contract()

    def _load_contract(self):
        """Load the smart contract from environment configuration."""
        contract_address = settings.CONTRACT_ADDRESS
        oracle_private_key = settings.ORACLE_PRIVATE_KEY
        
        if not contract_address:
            logger.warning("CONTRACT_ADDRESS not set, blockchain integration disabled")
            return
        
        try:
            # Validate contract address
            if not self.w3.is_address(contract_address):
                logger.error("Invalid contract address format", address=contract_address)
                return
            
            checksum_address = self.w3.to_checksum_address(contract_address)
            self.contract = self.w3.eth.contract(
                address=checksum_address,
                abi=NETWORK_COMPENSATION_ABI
            )
            
            # Set up oracle account for signing transactions
            if oracle_private_key:
                self.oracle_account = self.w3.eth.account.from_key(oracle_private_key)
                logger.info("Blockchain service initialized", contract=checksum_address)
            else:
                logger.warning("ORACLE_PRIVATE_KEY not set, transactions will fail")
                
        except Exception as e:
            logger.error("Failed to load smart contract", error=str(e))
            self.contract = None

    async def submit_compensation_data(
        self, 
        device_id: str, 
        total_bytes: int, 
        owner_address: str,
        quality_score: int = 80
    ) -> str | None:
        """
        Submit usage data to the blockchain for compensation.
        
        Args:
            device_id: The device identifier
            total_bytes: Total bytes transmitted during the period
            owner_address: The device owner's wallet address
            quality_score: Connection quality score (0-100)
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.contract or not self.oracle_account:
            logger.warning("Smart contract not loaded, skipping submission")
            return None
        
        try:
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.oracle_account.address)
            
            tx = self.contract.functions.submitUsageData(
                device_id,
                total_bytes,
                quality_score
            ).build_transaction({
                'from': self.oracle_account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.oracle_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(
                "Compensation data submitted to blockchain",
                device_id=device_id,
                total_bytes=total_bytes,
                owner_address=owner_address,
                tx_hash=tx_hash.hex()
            )
            
            return tx_hash.hex()
            
        except ContractLogicError as e:
            logger.error("Smart contract rejected transaction", error=str(e), device_id=device_id)
            return None
        except Exception as e:
            logger.error("Blockchain submission failed", error=str(e), device_id=device_id)
            return None

    async def register_device_on_chain(self, device_id: str, owner_address: str) -> str | None:
        """
        Register a device on the blockchain.
        
        Args:
            device_id: The device identifier
            owner_address: The device owner's wallet address
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.contract or not self.oracle_account:
            logger.warning("Smart contract not loaded, skipping device registration")
            return None
        
        try:
            nonce = self.w3.eth.get_transaction_count(self.oracle_account.address)
            
            tx = self.contract.functions.registerDevice(
                device_id,
                self.w3.to_checksum_address(owner_address)
            ).build_transaction({
                'from': self.oracle_account.address,
                'nonce': nonce,
                'gas': 150000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.oracle_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(
                "Device registered on blockchain",
                device_id=device_id,
                owner_address=owner_address,
                tx_hash=tx_hash.hex()
            )
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error("Device registration on blockchain failed", error=str(e))
            return None

    def is_connected(self) -> bool:
        """Check if connected to the blockchain network."""
        return self.w3.is_connected()


blockchain_service = BlockchainService()

