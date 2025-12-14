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

    def on_connect(self, client, flags, rc, properties):
        logger.info("MQTT connected")
        client.subscribe("devices/usage", qos=1)

    async def on_message(self, client, topic, payload, qos, properties):
        logger.info(f"MQTT message received: {topic} {payload.decode()}")
        # Process the message and broadcast to websockets
        await usage_service.process_usage_data(payload.decode())
        from app.services.websocket_manager import manager
        await manager.broadcast(payload.decode())

    def on_disconnect(self, client, packet, exc=None):
        logger.info("MQTT disconnected")

    async def connect(self):
        await self.client.connect("localhost") # Replace with your MQTT broker

    async def disconnect(self):
        await self.client.disconnect()

mqtt_service = MQTTService()
