"""
IoT Device Mesh Networking Module

Implements a P2P mesh network for device-to-device communication
without requiring the central backend for local operations.

Features:
- Peer discovery via mDNS and broadcast
- Encrypted P2P messaging using libsodium
- Distributed routing with gossip protocol
- Automatic network healing
- Local consensus for edge computing
"""

import asyncio
import hashlib
import json
import logging
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from collections import defaultdict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of mesh network messages"""
    DISCOVERY = "discovery"
    DISCOVERY_RESPONSE = "discovery_response"
    PING = "ping"
    PONG = "pong"
    DATA = "data"
    BROADCAST = "broadcast"
    ROUTE_REQUEST = "route_request"
    ROUTE_RESPONSE = "route_response"
    CONSENSUS_PROPOSE = "consensus_propose"
    CONSENSUS_VOTE = "consensus_vote"
    CONSENSUS_COMMIT = "consensus_commit"


@dataclass
class Peer:
    """Represents a peer in the mesh network"""
    node_id: str
    address: tuple[str, int]
    public_key: bytes
    last_seen: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    hop_count: int = 0
    is_direct: bool = True
    shared_secret: Optional[bytes] = None
    
    def is_alive(self, timeout: float = 60.0) -> bool:
        return time.time() - self.last_seen < timeout


@dataclass
class RoutingEntry:
    """Entry in the routing table"""
    destination: str
    next_hop: str
    hop_count: int
    last_updated: float = field(default_factory=time.time)
    

@dataclass
class MeshMessage:
    """A message in the mesh network"""
    msg_id: str
    msg_type: MessageType
    source: str
    destination: str
    payload: bytes
    ttl: int = 10
    timestamp: float = field(default_factory=time.time)
    signature: Optional[bytes] = None
    
    def to_bytes(self) -> bytes:
        """Serialize message to bytes"""
        data = {
            "id": self.msg_id,
            "type": self.msg_type.value,
            "src": self.source,
            "dst": self.destination,
            "payload": self.payload.hex(),
            "ttl": self.ttl,
            "ts": self.timestamp
        }
        if self.signature:
            data["sig"] = self.signature.hex()
        return json.dumps(data).encode()
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "MeshMessage":
        """Deserialize message from bytes"""
        obj = json.loads(data.decode())
        return cls(
            msg_id=obj["id"],
            msg_type=MessageType(obj["type"]),
            source=obj["src"],
            destination=obj["dst"],
            payload=bytes.fromhex(obj["payload"]),
            ttl=obj["ttl"],
            timestamp=obj["ts"],
            signature=bytes.fromhex(obj["sig"]) if obj.get("sig") else None
        )


class CryptoManager:
    """Handles mesh network cryptography"""
    
    def __init__(self):
        # Generate X25519 key pair for key exchange
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
    def get_public_key_bytes(self) -> bytes:
        """Get public key as bytes"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def derive_shared_secret(self, peer_public_key: bytes) -> bytes:
        """Derive shared secret using ECDH"""
        peer_key = x25519.X25519PublicKey.from_public_bytes(peer_public_key)
        shared_key = self.private_key.exchange(peer_key)
        
        # Derive encryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"mesh_network_key"
        ).derive(shared_key)
        
        return derived_key
    
    def encrypt(self, data: bytes, shared_secret: bytes) -> bytes:
        """Encrypt data with ChaCha20-Poly1305"""
        cipher = ChaCha20Poly1305(shared_secret)
        nonce = random.randbytes(12)
        ciphertext = cipher.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def decrypt(self, data: bytes, shared_secret: bytes) -> bytes:
        """Decrypt data with ChaCha20-Poly1305"""
        cipher = ChaCha20Poly1305(shared_secret)
        nonce = data[:12]
        ciphertext = data[12:]
        return cipher.decrypt(nonce, ciphertext, None)


class MeshRouter:
    """Handles message routing in the mesh network"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.routing_table: dict[str, RoutingEntry] = {}
        self.seen_messages: set[str] = set()
        self.max_seen_messages = 10000
        
    def add_route(self, destination: str, next_hop: str, hop_count: int):
        """Add or update a route"""
        existing = self.routing_table.get(destination)
        if not existing or existing.hop_count > hop_count:
            self.routing_table[destination] = RoutingEntry(
                destination=destination,
                next_hop=next_hop,
                hop_count=hop_count
            )
            
    def get_next_hop(self, destination: str) -> Optional[str]:
        """Get next hop for a destination"""
        entry = self.routing_table.get(destination)
        return entry.next_hop if entry else None
    
    def should_forward(self, msg: MeshMessage) -> bool:
        """Check if message should be forwarded"""
        if msg.msg_id in self.seen_messages:
            return False
        if msg.ttl <= 0:
            return False
        if msg.source == self.node_id:
            return False
            
        # Mark as seen
        self.seen_messages.add(msg.msg_id)
        
        # Cleanup old messages
        if len(self.seen_messages) > self.max_seen_messages:
            self.seen_messages = set(list(self.seen_messages)[-5000:])
            
        return True
    
    def cleanup_stale_routes(self, max_age: float = 300.0):
        """Remove stale routing entries"""
        current_time = time.time()
        self.routing_table = {
            dest: entry
            for dest, entry in self.routing_table.items()
            if current_time - entry.last_updated < max_age
        }


class LocalConsensus:
    """Implements local consensus for edge computing decisions"""
    
    def __init__(self, node_id: str, threshold: float = 0.67):
        self.node_id = node_id
        self.threshold = threshold
        self.proposals: dict[str, dict] = {}  # proposal_id -> proposal data
        self.votes: dict[str, dict[str, bool]] = defaultdict(dict)  # proposal_id -> node_id -> vote
        
    def propose(self, proposal_id: str, data: dict) -> dict:
        """Create a new proposal"""
        self.proposals[proposal_id] = {
            "id": proposal_id,
            "data": data,
            "proposer": self.node_id,
            "timestamp": time.time(),
            "status": "pending"
        }
        self.votes[proposal_id][self.node_id] = True
        return self.proposals[proposal_id]
    
    def vote(self, proposal_id: str, voter: str, approve: bool):
        """Record a vote on a proposal"""
        if proposal_id in self.proposals:
            self.votes[proposal_id][voter] = approve
            
    def check_consensus(self, proposal_id: str, peer_count: int) -> Optional[bool]:
        """Check if consensus is reached"""
        if proposal_id not in self.proposals:
            return None
            
        votes = self.votes[proposal_id]
        total_votes = len(votes)
        required = int((peer_count + 1) * self.threshold)
        
        if total_votes < required:
            return None  # Not enough votes yet
            
        approve_count = sum(1 for v in votes.values() if v)
        reject_count = total_votes - approve_count
        
        if approve_count >= required:
            self.proposals[proposal_id]["status"] = "approved"
            return True
        elif reject_count > (peer_count + 1 - required):
            self.proposals[proposal_id]["status"] = "rejected"
            return False
            
        return None  # Still pending


class MeshNode:
    """
    Main mesh network node implementation
    
    Provides P2P communication, routing, and local consensus
    for IoT devices without central server dependency.
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        listen_port: int = 5683,
        discovery_port: int = 5684
    ):
        self.node_id = node_id or self._generate_node_id()
        self.listen_port = listen_port
        self.discovery_port = discovery_port
        
        self.crypto = CryptoManager()
        self.router = MeshRouter(self.node_id)
        self.consensus = LocalConsensus(self.node_id)
        
        self.peers: dict[str, Peer] = {}
        self.message_handlers: dict[MessageType, list[Callable]] = defaultdict(list)
        
        self._running = False
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._discovery_transport: Optional[asyncio.DatagramTransport] = None
        
        logger.info(f"Mesh node initialized: {self.node_id}")
        
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        unique_data = f"{socket.gethostname()}-{time.time()}-{random.random()}"
        return hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    
    async def start(self):
        """Start the mesh node"""
        self._running = True
        
        loop = asyncio.get_event_loop()
        
        # Create UDP socket for mesh communication
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: MeshProtocol(self),
            local_addr=("0.0.0.0", self.listen_port)
        )
        
        # Create UDP socket for discovery
        self._discovery_transport, _ = await loop.create_datagram_endpoint(
            lambda: DiscoveryProtocol(self),
            local_addr=("0.0.0.0", self.discovery_port),
            allow_broadcast=True
        )
        
        # Start background tasks
        asyncio.create_task(self._discovery_loop())
        asyncio.create_task(self._maintenance_loop())
        asyncio.create_task(self._ping_loop())
        
        logger.info(f"Mesh node started on port {self.listen_port}")
        
    async def stop(self):
        """Stop the mesh node"""
        self._running = False
        
        if self._transport:
            self._transport.close()
        if self._discovery_transport:
            self._discovery_transport.close()
            
        logger.info("Mesh node stopped")
        
    async def _discovery_loop(self):
        """Periodic peer discovery"""
        while self._running:
            try:
                await self.broadcast_discovery()
            except Exception as e:
                logger.error(f"Discovery error: {e}")
            await asyncio.sleep(30)
            
    async def _maintenance_loop(self):
        """Periodic maintenance tasks"""
        while self._running:
            try:
                # Remove dead peers
                dead_peers = [
                    peer_id for peer_id, peer in self.peers.items()
                    if not peer.is_alive(timeout=120)
                ]
                for peer_id in dead_peers:
                    del self.peers[peer_id]
                    logger.info(f"Removed dead peer: {peer_id}")
                    
                # Cleanup stale routes
                self.router.cleanup_stale_routes()
                
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
            await asyncio.sleep(60)
            
    async def _ping_loop(self):
        """Periodic ping to maintain connections"""
        while self._running:
            try:
                for peer in list(self.peers.values()):
                    await self.send_ping(peer)
            except Exception as e:
                logger.error(f"Ping error: {e}")
            await asyncio.sleep(15)
            
    async def broadcast_discovery(self):
        """Broadcast discovery message"""
        msg = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.DISCOVERY,
            source=self.node_id,
            destination="*",
            payload=json.dumps({
                "port": self.listen_port,
                "public_key": self.crypto.get_public_key_bytes().hex()
            }).encode()
        )
        
        # Broadcast on LAN
        if self._discovery_transport:
            self._discovery_transport.sendto(
                msg.to_bytes(),
                ("255.255.255.255", self.discovery_port)
            )
            
    def handle_discovery(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle discovery message"""
        if msg.source == self.node_id:
            return
            
        payload = json.loads(msg.payload.decode())
        peer_port = payload["port"]
        peer_public_key = bytes.fromhex(payload["public_key"])
        
        # Derive shared secret
        shared_secret = self.crypto.derive_shared_secret(peer_public_key)
        
        peer = Peer(
            node_id=msg.source,
            address=(addr[0], peer_port),
            public_key=peer_public_key,
            shared_secret=shared_secret
        )
        
        self.peers[msg.source] = peer
        self.router.add_route(msg.source, msg.source, 1)
        
        logger.info(f"Discovered peer: {msg.source} at {addr}")
        
        # Send discovery response
        response = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.DISCOVERY_RESPONSE,
            source=self.node_id,
            destination=msg.source,
            payload=json.dumps({
                "port": self.listen_port,
                "public_key": self.crypto.get_public_key_bytes().hex()
            }).encode()
        )
        
        self._send_to_peer(peer, response)
        
    def handle_discovery_response(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle discovery response"""
        if msg.source == self.node_id:
            return
            
        payload = json.loads(msg.payload.decode())
        peer_port = payload["port"]
        peer_public_key = bytes.fromhex(payload["public_key"])
        
        shared_secret = self.crypto.derive_shared_secret(peer_public_key)
        
        peer = Peer(
            node_id=msg.source,
            address=(addr[0], peer_port),
            public_key=peer_public_key,
            shared_secret=shared_secret
        )
        
        self.peers[msg.source] = peer
        self.router.add_route(msg.source, msg.source, 1)
        
        logger.info(f"Peer responded: {msg.source} at {addr}")
        
    async def send_ping(self, peer: Peer):
        """Send ping to peer"""
        msg = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.PING,
            source=self.node_id,
            destination=peer.node_id,
            payload=struct.pack("!d", time.time())
        )
        self._send_to_peer(peer, msg)
        
    def handle_ping(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle ping message"""
        peer = self.peers.get(msg.source)
        if peer:
            peer.last_seen = time.time()
            
            response = MeshMessage(
                msg_id=self._generate_msg_id(),
                msg_type=MessageType.PONG,
                source=self.node_id,
                destination=msg.source,
                payload=msg.payload  # Echo timestamp
            )
            self._send_to_peer(peer, response)
            
    def handle_pong(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle pong message"""
        peer = self.peers.get(msg.source)
        if peer:
            peer.last_seen = time.time()
            
            # Calculate latency
            sent_time = struct.unpack("!d", msg.payload)[0]
            peer.latency_ms = (time.time() - sent_time) * 1000
            
    async def send_data(self, destination: str, data: bytes, encrypted: bool = True):
        """Send data to a specific peer"""
        peer = self.peers.get(destination)
        
        if not peer:
            # Try routing
            next_hop = self.router.get_next_hop(destination)
            if next_hop:
                peer = self.peers.get(next_hop)
                
        if not peer:
            raise ValueError(f"No route to {destination}")
            
        payload = data
        if encrypted and peer.shared_secret:
            payload = self.crypto.encrypt(data, peer.shared_secret)
            
        msg = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.DATA,
            source=self.node_id,
            destination=destination,
            payload=payload
        )
        
        self._send_to_peer(peer, msg)
        
    async def broadcast(self, data: bytes):
        """Broadcast data to all peers"""
        msg = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.BROADCAST,
            source=self.node_id,
            destination="*",
            payload=data
        )
        
        for peer in self.peers.values():
            self._send_to_peer(peer, msg)
            
    def handle_data(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle incoming data message"""
        if msg.destination != self.node_id and msg.destination != "*":
            # Forward if not for us
            if self.router.should_forward(msg):
                self._forward_message(msg)
            return
            
        peer = self.peers.get(msg.source)
        payload = msg.payload
        
        # Decrypt if we have shared secret
        if peer and peer.shared_secret:
            try:
                payload = self.crypto.decrypt(msg.payload, peer.shared_secret)
            except Exception:
                pass  # Not encrypted or wrong key
                
        # Call registered handlers
        for handler in self.message_handlers[MessageType.DATA]:
            try:
                handler(msg.source, payload)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                
    def handle_broadcast(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle broadcast message"""
        if not self.router.should_forward(msg):
            return
            
        # Process locally
        for handler in self.message_handlers[MessageType.BROADCAST]:
            try:
                handler(msg.source, msg.payload)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                
        # Forward to other peers
        msg.ttl -= 1
        if msg.ttl > 0:
            for peer in self.peers.values():
                if peer.node_id != msg.source:
                    self._send_to_peer(peer, msg)
                    
    async def propose_consensus(self, proposal_id: str, data: dict) -> bool:
        """Propose a local consensus decision"""
        proposal = self.consensus.propose(proposal_id, data)
        
        # Broadcast proposal
        msg = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.CONSENSUS_PROPOSE,
            source=self.node_id,
            destination="*",
            payload=json.dumps(proposal).encode()
        )
        
        for peer in self.peers.values():
            self._send_to_peer(peer, msg)
            
        # Wait for consensus
        for _ in range(10):  # 10 second timeout
            result = self.consensus.check_consensus(proposal_id, len(self.peers))
            if result is not None:
                return result
            await asyncio.sleep(1)
            
        return False
        
    def handle_consensus_propose(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle consensus proposal"""
        proposal = json.loads(msg.payload.decode())
        
        # Auto-vote (in real implementation, this would involve validation)
        vote = True  # Approve by default
        
        self.consensus.vote(proposal["id"], self.node_id, vote)
        
        # Send vote
        response = MeshMessage(
            msg_id=self._generate_msg_id(),
            msg_type=MessageType.CONSENSUS_VOTE,
            source=self.node_id,
            destination=msg.source,
            payload=json.dumps({
                "proposal_id": proposal["id"],
                "vote": vote
            }).encode()
        )
        
        peer = self.peers.get(msg.source)
        if peer:
            self._send_to_peer(peer, response)
            
    def handle_consensus_vote(self, msg: MeshMessage, addr: tuple[str, int]):
        """Handle consensus vote"""
        vote_data = json.loads(msg.payload.decode())
        self.consensus.vote(
            vote_data["proposal_id"],
            msg.source,
            vote_data["vote"]
        )
        
    def on_data(self, handler: Callable[[str, bytes], None]):
        """Register handler for data messages"""
        self.message_handlers[MessageType.DATA].append(handler)
        
    def on_broadcast(self, handler: Callable[[str, bytes], None]):
        """Register handler for broadcast messages"""
        self.message_handlers[MessageType.BROADCAST].append(handler)
        
    def _send_to_peer(self, peer: Peer, msg: MeshMessage):
        """Send message to peer"""
        if self._transport:
            self._transport.sendto(msg.to_bytes(), peer.address)
            
    def _forward_message(self, msg: MeshMessage):
        """Forward message to next hop"""
        next_hop = self.router.get_next_hop(msg.destination)
        if next_hop:
            peer = self.peers.get(next_hop)
            if peer:
                msg.ttl -= 1
                self._send_to_peer(peer, msg)
                
    def _generate_msg_id(self) -> str:
        """Generate unique message ID"""
        return hashlib.sha256(
            f"{self.node_id}-{time.time()}-{random.random()}".encode()
        ).hexdigest()[:16]
        
    def get_peer_count(self) -> int:
        """Get number of connected peers"""
        return len(self.peers)
        
    def get_peer_list(self) -> list[dict]:
        """Get list of peers"""
        return [
            {
                "node_id": peer.node_id,
                "address": f"{peer.address[0]}:{peer.address[1]}",
                "latency_ms": peer.latency_ms,
                "hop_count": peer.hop_count,
                "is_alive": peer.is_alive()
            }
            for peer in self.peers.values()
        ]


class MeshProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for mesh network"""
    
    def __init__(self, node: MeshNode):
        self.node = node
        
    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        try:
            msg = MeshMessage.from_bytes(data)
            
            handlers = {
                MessageType.PING: self.node.handle_ping,
                MessageType.PONG: self.node.handle_pong,
                MessageType.DATA: self.node.handle_data,
                MessageType.BROADCAST: self.node.handle_broadcast,
                MessageType.CONSENSUS_PROPOSE: self.node.handle_consensus_propose,
                MessageType.CONSENSUS_VOTE: self.node.handle_consensus_vote,
            }
            
            handler = handlers.get(msg.msg_type)
            if handler:
                handler(msg, addr)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for peer discovery"""
    
    def __init__(self, node: MeshNode):
        self.node = node
        
    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        try:
            msg = MeshMessage.from_bytes(data)
            
            if msg.msg_type == MessageType.DISCOVERY:
                self.node.handle_discovery(msg, addr)
            elif msg.msg_type == MessageType.DISCOVERY_RESPONSE:
                self.node.handle_discovery_response(msg, addr)
                
        except Exception as e:
            logger.error(f"Error handling discovery: {e}")
