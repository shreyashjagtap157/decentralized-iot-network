from app.db.models import NetworkUsage
from app.services.blockchain_service import blockchain_service
from app.core.logging import logger
import json

class UsageService:
    async def process_usage_data(self, raw_data: str):
        try:
            data = json.loads(raw_data)
            # TODO: In a real app, you would aggregate this data before submitting
            # For now, we submit directly
            total_bytes = data.get("bytesTransmitted", 0) + data.get("bytesReceived", 0)
            device_id = data.get("deviceId")

            if device_id and total_bytes > 0:
                logger.info("Processing usage data", device_id=device_id, total_bytes=total_bytes)
                await blockchain_service.submit_compensation_data(device_id, total_bytes)
        except json.JSONDecodeError:
            logger.error("Failed to decode usage data JSON", data=raw_data)
        except Exception as e:
            logger.error("Error processing usage data", error=str(e))

usage_service = UsageService()
