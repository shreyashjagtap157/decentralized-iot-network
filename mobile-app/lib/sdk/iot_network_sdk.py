"""
IoT Network Mobile SDK
Python reference implementation - can be ported to Dart/Swift/Kotlin.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Callable
import asyncio
import aiohttp
import json
import hmac
import hashlib
import time


@dataclass
class SDKConfig:
    """SDK Configuration."""
    api_url: str = "https://api.iot-network.io"
    ws_url: str = "wss://ws.iot-network.io"
    api_key: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    auto_reconnect: bool = True


@dataclass
class Device:
    """Device representation."""
    id: str
    owner: str
    device_type: str
    is_active: bool
    quality_score: float
    total_bytes: int
    created_at: datetime


@dataclass
class Earnings:
    """User earnings data."""
    total_earned: float
    pending_rewards: float
    last_payout: Optional[datetime]
    currency: str = "NWR"


@dataclass
class NetworkStatus:
    """Network status information."""
    is_sharing: bool
    connected_users: int
    bandwidth_used: float
    session_earnings: float
    quality_score: float


class IoTNetworkSDK:
    """
    Main SDK class for IoT Network integration.
    
    Usage:
        sdk = IoTNetworkSDK(config)
        await sdk.connect()
        
        devices = await sdk.get_devices()
        earnings = await sdk.get_earnings()
        
        await sdk.start_sharing()
    """
    
    def __init__(self, config: SDKConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.is_connected = False
        self.auth_token: Optional[str] = None
        
        # Callbacks
        self.on_earnings_update: Optional[Callable[[Earnings], None]] = None
        self.on_status_change: Optional[Callable[[NetworkStatus], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
    # ==================== Connection ====================
    
    async def connect(self, wallet_address: Optional[str] = None):
        """Initialize SDK and authenticate."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Authenticate with API key
        if self.config.api_key:
            headers = {"X-API-Key": self.config.api_key}
            async with self.session.post(
                f"{self.config.api_url}/auth/api-key",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.auth_token = data.get("token")
                    self.is_connected = True
                else:
                    raise Exception(f"Authentication failed: {resp.status}")
        
        # Connect WebSocket for real-time updates
        if self.config.auto_reconnect:
            asyncio.create_task(self._websocket_loop())
    
    async def disconnect(self):
        """Disconnect from SDK."""
        self.is_connected = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
    
    async def _websocket_loop(self):
        """WebSocket connection loop for real-time updates."""
        while self.is_connected:
            try:
                async with self.session.ws_connect(
                    f"{self.config.ws_url}/sdk",
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                ) as ws:
                    self.ws = ws
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                await asyncio.sleep(5)  # Retry after 5 seconds
    
    async def _handle_ws_message(self, data: Dict):
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")
        
        if msg_type == "earnings_update" and self.on_earnings_update:
            earnings = Earnings(
                total_earned=data["total"],
                pending_rewards=data["pending"],
                last_payout=datetime.fromisoformat(data["last_payout"]) if data.get("last_payout") else None
            )
            self.on_earnings_update(earnings)
            
        elif msg_type == "status_update" and self.on_status_change:
            status = NetworkStatus(
                is_sharing=data["sharing"],
                connected_users=data["users"],
                bandwidth_used=data["bandwidth"],
                session_earnings=data["session_earnings"],
                quality_score=data["quality"]
            )
            self.on_status_change(status)
    
    # ==================== API Methods ====================
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated headers."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        return headers
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated API request."""
        url = f"{self.config.api_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.request(
                    method, url,
                    headers=self._get_headers(),
                    json=data
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 401:
                        raise Exception("Unauthorized")
                    elif resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        error = await resp.text()
                        raise Exception(f"API Error {resp.status}: {error}")
            except aiohttp.ClientError as e:
                if attempt == self.config.retry_attempts - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception("Max retries exceeded")
    
    # ==================== Device Management ====================
    
    async def get_devices(self) -> List[Device]:
        """Get all devices for the authenticated user."""
        data = await self._request("GET", "/api/v1/devices/my")
        return [
            Device(
                id=d["id"],
                owner=d["owner"],
                device_type=d["type"],
                is_active=d["is_active"],
                quality_score=d["quality_score"],
                total_bytes=d["total_bytes"],
                created_at=datetime.fromisoformat(d["created_at"])
            )
            for d in data.get("devices", [])
        ]
    
    async def register_device(self, device_id: str, device_type: str = "ESP32") -> Device:
        """Register a new device."""
        data = await self._request("POST", "/api/v1/devices/register", {
            "device_id": device_id,
            "device_type": device_type
        })
        return Device(
            id=data["id"],
            owner=data["owner"],
            device_type=data["type"],
            is_active=True,
            quality_score=100,
            total_bytes=0,
            created_at=datetime.utcnow()
        )
    
    async def deactivate_device(self, device_id: str) -> bool:
        """Deactivate a device."""
        await self._request("POST", f"/api/v1/devices/{device_id}/deactivate")
        return True
    
    # ==================== Network Sharing ====================
    
    async def start_sharing(self, device_id: Optional[str] = None) -> NetworkStatus:
        """Start network sharing for a device."""
        endpoint = f"/api/v1/devices/{device_id}/share/start" if device_id else "/api/v1/share/start"
        data = await self._request("POST", endpoint)
        return NetworkStatus(
            is_sharing=True,
            connected_users=0,
            bandwidth_used=0,
            session_earnings=0,
            quality_score=data.get("quality", 100)
        )
    
    async def stop_sharing(self, device_id: Optional[str] = None) -> NetworkStatus:
        """Stop network sharing for a device."""
        endpoint = f"/api/v1/devices/{device_id}/share/stop" if device_id else "/api/v1/share/stop"
        data = await self._request("POST", endpoint)
        return NetworkStatus(
            is_sharing=False,
            connected_users=0,
            bandwidth_used=data.get("total_bandwidth", 0),
            session_earnings=data.get("session_earnings", 0),
            quality_score=data.get("quality", 100)
        )
    
    async def get_sharing_status(self, device_id: Optional[str] = None) -> NetworkStatus:
        """Get current sharing status."""
        endpoint = f"/api/v1/devices/{device_id}/status" if device_id else "/api/v1/share/status"
        data = await self._request("GET", endpoint)
        return NetworkStatus(
            is_sharing=data.get("is_sharing", False),
            connected_users=data.get("connected_users", 0),
            bandwidth_used=data.get("bandwidth_used", 0),
            session_earnings=data.get("session_earnings", 0),
            quality_score=data.get("quality_score", 100)
        )
    
    # ==================== Earnings ====================
    
    async def get_earnings(self) -> Earnings:
        """Get current earnings."""
        data = await self._request("GET", "/api/v1/analytics/user-earnings")
        return Earnings(
            total_earned=data.get("total_earned", 0),
            pending_rewards=data.get("pending_rewards", 0),
            last_payout=datetime.fromisoformat(data["last_payout"]) if data.get("last_payout") else None
        )
    
    async def claim_rewards(self) -> Dict:
        """Claim pending rewards to wallet."""
        return await self._request("POST", "/api/v1/rewards/claim")
    
    async def get_earnings_history(self, days: int = 30) -> List[Dict]:
        """Get earnings history."""
        return await self._request("GET", f"/api/v1/analytics/earnings-history?days={days}")
    
    # ==================== Analytics ====================
    
    async def get_analytics(self, period: str = "7d") -> Dict:
        """Get analytics data."""
        return await self._request("GET", f"/api/v1/analytics/summary?period={period}")
    
    async def get_network_stats(self) -> Dict:
        """Get global network statistics."""
        return await self._request("GET", "/api/v1/network/stats")


# ==================== Convenience Functions ====================

async def create_sdk(api_key: str, api_url: str = "https://api.iot-network.io") -> IoTNetworkSDK:
    """Create and connect SDK instance."""
    config = SDKConfig(api_url=api_url, api_key=api_key)
    sdk = IoTNetworkSDK(config)
    await sdk.connect()
    return sdk


# ==================== Example Usage ====================

async def example():
    """Example SDK usage."""
    sdk = await create_sdk("your_api_key_here")
    
    # Get devices
    devices = await sdk.get_devices()
    print(f"Found {len(devices)} devices")
    
    # Start sharing
    if devices:
        status = await sdk.start_sharing(devices[0].id)
        print(f"Sharing started: {status.is_sharing}")
    
    # Get earnings
    earnings = await sdk.get_earnings()
    print(f"Total earned: {earnings.total_earned} NWR")
    
    # Set up callbacks
    def on_earnings(e: Earnings):
        print(f"Earnings update: {e.pending_rewards} pending")
    
    sdk.on_earnings_update = on_earnings
    
    # Keep running
    await asyncio.sleep(60)
    
    await sdk.disconnect()


if __name__ == "__main__":
    asyncio.run(example())
