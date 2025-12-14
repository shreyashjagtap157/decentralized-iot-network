import asyncio
from datetime import datetime, timedelta
from app.db.models import NetworkUsage, Device, CompensationTransaction
from app.services.blockchain_service import blockchain_service
from app.core.logging import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

class CompensationService:
    def __init__(self):
        self.processing_interval = 300  # 5 minutes

    async def start_background_processing(self):
        """Start the background compensation processing task"""
        while True:
            try:
                await self.process_pending_compensations()
                await asyncio.sleep(self.processing_interval)
            except Exception as e:
                logger.error("Error in compensation processing", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def process_pending_compensations(self):
        """Process all uncompensated usage data"""
        from app.db.models import get_db
        
        async with get_db() as db:
            # Get uncompensated usage data grouped by device
            uncompensated = await db.execute(
                NetworkUsage.__table__.select().where(
                    NetworkUsage.compensated == False
                )
            )
            usage_records = uncompensated.fetchall()
            
            if not usage_records:
                return
            
            # Group by device_id
            device_usage = {}
            for record in usage_records:
                device_id = record.device_id
                if device_id not in device_usage:
                    device_usage[device_id] = {
                        'total_bytes': 0,
                        'avg_quality': 0,
                        'records': []
                    }
                
                total_bytes = record.bytes_transmitted + record.bytes_received
                device_usage[device_id]['total_bytes'] += total_bytes
                device_usage[device_id]['records'].append(record)
            
            # Calculate average quality and submit to blockchain
            for device_id, usage_data in device_usage.items():
                records = usage_data['records']
                avg_quality = sum(r.connection_quality for r in records) / len(records)
                total_bytes = usage_data['total_bytes']
                
                # Get device owner
                device = await db.get(Device, device_id)
                if not device:
                    continue
                
                # Submit to blockchain
                tx_hash = await blockchain_service.submit_compensation_data(
                    device_id, 
                    total_bytes,
                    device.owner_address
                )
                
                if tx_hash:
                    # Mark records as compensated
                    for record in records:
                        record.compensated = True
                    
                    # Create compensation transaction record
                    compensation = CompensationTransaction(
                        device_id=device_id,
                        owner_address=device.owner_address,
                        usage_period_start=min(r.timestamp for r in records),
                        usage_period_end=max(r.timestamp for r in records),
                        total_bytes=total_bytes,
                        average_quality=avg_quality,
                        blockchain_tx_hash=tx_hash,
                        status="COMPLETED"
                    )
                    db.add(compensation)
                    
                    await db.commit()
                    
                    logger.info(
                        "Compensation processed",
                        device_id=device_id,
                        total_bytes=total_bytes,
                        tx_hash=tx_hash
                    )

compensation_service = CompensationService()
