import asyncio
from gmqtt import Client as MQTTClient
from app.core.logging import logger
from app.services.usage_service import usage_service

class MQTTService:
    def __init__(self):
        self.client = MQTTClient("backend-client")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self._client = None
        self._should_reconnect = True
        self._reconnect_interval = 5
        self._max_reconnect_interval = 60
        self._broker_host = "localhost"

    def on_connect(self, client, flags, rc, properties):
        logger.info("MQTT connected")
        client.subscribe("devices/usage", qos=1)
        self._reconnect_interval = 5  # Reset on successful connection

    async def on_message(self, client, topic, payload, qos, properties):
        logger.info(f"MQTT message received: {topic} {payload.decode()}")
        # Process the message and broadcast to websockets
        await usage_service.process_usage_data(payload.decode())
        from app.services.websocket_manager import manager
        await manager.broadcast(payload.decode())

    def on_disconnect(self, client, packet, exc=None):
        logger.info("MQTT disconnected")
        if self._should_reconnect:
            asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        while self._should_reconnect:
            try:
                logger.info(f"Attempting MQTT reconnection in {self._reconnect_interval}s...")
                await asyncio.sleep(self._reconnect_interval)
                await self.client.connect(self._broker_host)
                logger.info("MQTT reconnection successful")
                break
            except Exception as e:
                logger.error(f"MQTT reconnection failed: {e}")
                # Exponential backoff with max limit
                self._reconnect_interval = min(
                    self._reconnect_interval * 2, 
                    self._max_reconnect_interval
                )

    async def connect(self, host: str = "localhost"):
        self._broker_host = host
        self._should_reconnect = True
        await self.client.connect(host)

    async def disconnect(self):
        self._should_reconnect = False
        await self.client.disconnect()

mqtt_service = MQTTService()

