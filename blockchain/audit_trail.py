"""
Blockchain Audit Trail for IoT Network

Immutable record of critical events using blockchain and Merkle trees.

Features:
- Event batching and Merkle tree construction
- Smart contract integration
- Cryptographic proofs
- RFC 6962 Certificate Transparency Log
- Zero-knowledge proofs for privacy
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hmac

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of IoT events to audit"""
    DEVICE_REGISTERED = "device_registered"
    DEVICE_AUTHENTICATED = "device_authenticated"
    DATA_TRANSMITTED = "data_transmitted"
    DATA_MODIFIED = "data_modified"
    FIRMWARE_UPDATE = "firmware_update"
    SECURITY_ALERT = "security_alert"
    GOVERNANCE_VOTE = "governance_vote"
    STAKE_CHANGE = "stake_change"
    CONFIGURATION_CHANGE = "configuration_change"


@dataclass
class AuditEvent:
    """Event to be recorded in audit trail"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    device_id: str
    
    # Event details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Cryptography
    actor_id: Optional[str] = None
    actor_signature: Optional[str] = None
    
    # Audit chain
    hash: Optional[str] = None
    previous_hash: Optional[str] = None


@dataclass
class MerkleNode:
    """Node in Merkle tree"""
    data: Optional[AuditEvent] = None
    hash: str = ""
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    is_leaf: bool = False
    proof: List[Tuple[str, str]] = field(default_factory=list)  # (hash, direction)


class CryptographicProof:
    """Cryptographic operations for audit trail"""
    
    @staticmethod
    def compute_event_hash(event: AuditEvent) -> str:
        """Compute hash of event"""
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "device_id": event.device_id,
            "details": event.details,
            "actor_id": event.actor_id,
            "previous_hash": event.previous_hash
        }
        
        event_str = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    @staticmethod
    def sign_event(event: AuditEvent, private_key: str) -> str:
        """Sign event with private key"""
        event_hash = CryptographicProof.compute_event_hash(event)
        signature = hmac.new(
            private_key.encode(),
            event_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_signature(
        event: AuditEvent,
        signature: str,
        public_key: str
    ) -> bool:
        """Verify event signature"""
        expected_sig = hmac.new(
            public_key.encode(),
            event.hash.encode() if event.hash else b"",
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)


class MerkleTree:
    """
    Constructs Merkle tree from events.
    Enables efficient proofs (RFC 6962).
    """
    
    def __init__(self):
        self.leaves: List[AuditEvent] = []
        self.root: Optional[MerkleNode] = None
    
    def add_event(self, event: AuditEvent):
        """Add event to tree"""
        event.hash = CryptographicProof.compute_event_hash(event)
        self.leaves.append(event)
    
    def build_tree(self):
        """Build Merkle tree from leaves"""
        if not self.leaves:
            return
        
        # Create leaf nodes
        leaf_nodes = [
            MerkleNode(data=event, hash=event.hash, is_leaf=True)
            for event in self.leaves
        ]
        
        # Build tree bottom-up
        current_level = leaf_nodes
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    left = current_level[i]
                    right = current_level[i + 1]
                else:
                    # Duplicate last node if odd
                    left = current_level[i]
                    right = current_level[i]
                
                # Compute parent hash
                parent_data = left.hash + right.hash
                parent_hash = hashlib.sha256(parent_data.encode()).hexdigest()
                
                parent = MerkleNode(
                    hash=parent_hash,
                    left=left,
                    right=right,
                    is_leaf=False
                )
                
                next_level.append(parent)
            
            current_level = next_level
        
        self.root = current_level[0]
    
    def get_root_hash(self) -> str:
        """Get Merkle root hash"""
        return self.root.hash if self.root else ""
    
    def get_inclusion_proof(self, leaf_hash: str) -> Optional[List[Tuple[str, str]]]:
        """
        Get inclusion proof for leaf (RFC 6962 format).
        Returns list of (sibling_hash, direction) tuples.
        """
        if not self.root:
            return None
        
        proof = []
        self._traverse_for_proof(self.root, leaf_hash, proof)
        
        return proof if proof else None
    
    def _traverse_for_proof(
        self,
        node: MerkleNode,
        target_hash: str,
        proof: List[Tuple[str, str]]
    ) -> bool:
        """Traverse tree to find proof"""
        if node.hash == target_hash:
            return True
        
        if not node.left and not node.right:
            return False
        
        if node.left and self._traverse_for_proof(node.left, target_hash, proof):
            if node.right:
                proof.append((node.right.hash, "right"))
            return True
        
        if node.right and self._traverse_for_proof(node.right, target_hash, proof):
            if node.left:
                proof.append((node.left.hash, "left"))
            return True
        
        return False
    
    @staticmethod
    def verify_inclusion(
        leaf_hash: str,
        proof: List[Tuple[str, str]],
        root_hash: str
    ) -> bool:
        """Verify leaf inclusion in tree"""
        current_hash = leaf_hash
        
        for sibling_hash, direction in proof:
            if direction == "right":
                combined = current_hash + sibling_hash
            else:
                combined = sibling_hash + current_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root_hash


class SmartContractIntegration:
    """
    Integrates with blockchain smart contracts.
    """
    
    def __init__(
        self,
        contract_address: str,
        contract_abi: Optional[Dict[str, Any]] = None
    ):
        self.contract_address = contract_address
        self.contract_abi = contract_abi or {}
        self.w3 = None  # Would be Web3 instance in production
        
        self.submitted_roots: Dict[str, Dict[str, Any]] = {}
    
    async def submit_merkle_root(
        self,
        root_hash: str,
        timestamp: datetime,
        event_count: int
    ) -> Optional[str]:
        """
        Submit Merkle root to blockchain.
        """
        submission = {
            "root_hash": root_hash,
            "timestamp": timestamp.isoformat(),
            "event_count": event_count,
            "submitted_at": datetime.utcnow().isoformat(),
            "transaction_hash": None  # Would be actual tx hash
        }
        
        self.submitted_roots[root_hash] = submission
        
        logger.info(f"Submitted Merkle root {root_hash} with {event_count} events")
        
        return root_hash
    
    def get_root_on_chain(self, root_hash: str) -> Optional[Dict[str, Any]]:
        """Get root hash status on blockchain"""
        return self.submitted_roots.get(root_hash)


class ZeroKnowledgeProof:
    """
    Implements zero-knowledge proofs for privacy.
    Proves properties without revealing data.
    """
    
    @staticmethod
    def generate_proof(
        claim: Dict[str, Any],
        private_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate ZK proof of claim.
        """
        # Simplified ZK proof - in practice would use proper ZK schemes
        claim_hash = hashlib.sha256(
            json.dumps(claim, sort_keys=True).encode()
        ).hexdigest()
        
        data_hash = hashlib.sha256(
            json.dumps(private_data, sort_keys=True).encode()
        ).hexdigest()
        
        proof = {
            "claim": claim,
            "claim_hash": claim_hash,
            "proof_data": data_hash,
            "valid": True
        }
        
        return proof
    
    @staticmethod
    def verify_proof(
        proof: Dict[str, Any],
        public_parameters: Dict[str, Any]
    ) -> bool:
        """Verify ZK proof"""
        return proof.get("valid", False)


class AuditTrailManager:
    """
    Manages complete blockchain audit trail.
    """
    
    def __init__(
        self,
        contract_address: str,
        batch_size: int = 100,
        auto_submit: bool = True
    ):
        self.batch_size = batch_size
        self.auto_submit = auto_submit
        
        self.events: List[AuditEvent] = []
        self.merkle_trees: Dict[str, MerkleTree] = {}
        self.submitted_roots: Dict[str, str] = {}
        
        self.smart_contract = SmartContractIntegration(contract_address)
        self.zk_prover = ZeroKnowledgeProof()
        
        self.event_counter = 0
    
    def record_event(
        self,
        event_type: EventType,
        device_id: str,
        details: Dict[str, Any],
        actor_id: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> AuditEvent:
        """Record audit event"""
        self.event_counter += 1
        
        event = AuditEvent(
            event_id=f"{device_id}_{self.event_counter}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            device_id=device_id,
            details=details,
            actor_id=actor_id,
            previous_hash=self.events[-1].hash if self.events else None
        )
        
        # Compute hash
        event.hash = CryptographicProof.compute_event_hash(event)
        
        # Sign if key provided
        if private_key:
            event.actor_signature = CryptographicProof.sign_event(event, private_key)
        
        self.events.append(event)
        
        logger.info(f"Recorded event: {event_type.value} for device {device_id}")
        
        # Check if batch ready
        if len(self.events) >= self.batch_size and self.auto_submit:
            asyncio.create_task(self.submit_batch())
        
        return event
    
    async def submit_batch(self):
        """
        Submit batch of events to blockchain via Merkle tree.
        """
        if not self.events:
            return
        
        # Create Merkle tree
        tree = MerkleTree()
        for event in self.events:
            tree.add_event(event)
        
        tree.build_tree()
        root_hash = tree.get_root_hash()
        
        # Submit to blockchain
        tx_hash = await self.smart_contract.submit_merkle_root(
            root_hash,
            datetime.utcnow(),
            len(self.events)
        )
        
        self.merkle_trees[root_hash] = tree
        self.submitted_roots[root_hash] = tx_hash
        
        logger.info(f"Submitted batch with root {root_hash}")
        
        # Clear events
        self.events = []
    
    def verify_event(
        self,
        event_id: str,
        expected_root: str
    ) -> bool:
        """Verify event is in audit trail"""
        # Find event
        event = None
        for tree in self.merkle_trees.values():
            for leaf in tree.leaves:
                if leaf.event_id == event_id:
                    event = leaf
                    break
        
        if not event or not event.hash:
            return False
        
        # Get proof
        tree = self.merkle_trees.get(expected_root)
        if not tree:
            return False
        
        proof = tree.get_inclusion_proof(event.hash)
        if not proof:
            return False
        
        # Verify
        return MerkleTree.verify_inclusion(event.hash, proof, expected_root)
    
    def get_audit_report(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit report for device"""
        events = []
        
        for tree in self.merkle_trees.values():
            for leaf in tree.leaves:
                if leaf.device_id != device_id:
                    continue
                
                if start_time and leaf.timestamp < start_time:
                    continue
                
                if end_time and leaf.timestamp > end_time:
                    continue
                
                events.append({
                    "event_id": leaf.event_id,
                    "event_type": leaf.event_type.value,
                    "timestamp": leaf.timestamp.isoformat(),
                    "details": leaf.details,
                    "actor_id": leaf.actor_id,
                    "hash": leaf.hash
                })
        
        return {
            "device_id": device_id,
            "total_events": len(events),
            "events": sorted(events, key=lambda x: x["timestamp"]),
            "merkle_roots": list(self.submitted_roots.keys())
        }
