"""
Backward compatibility layer - re-exports models from app.db.models.
This file exists to maintain backward compatibility with code that imports from app.models.
The canonical model definitions are in app.db.models.
"""

# Re-export all models from the canonical location
from app.db.models import (
    Base,
    engine,
    SessionLocal,
    get_db,
    DeviceStatus,
    TransactionStatus,
    Device,
    NetworkUsage,
    CompensationTransaction,
    User,
)

# DataEntry model - kept here as it's not in db/models
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from datetime import datetime


class DataEntry(Base):
    """
    SQLAlchemy model for device data entries.
    Used for storing sensor readings and other device-generated data.
    """
    __tablename__ = "data_entries"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    data_type = Column(String)
    value = Column(Float)
    quality_score = Column(Integer)
    meta = Column(String, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


__all__ = [
    'Base',
    'engine',
    'SessionLocal',
    'get_db',
    'DeviceStatus',
    'TransactionStatus',
    'Device',
    'NetworkUsage',
    'CompensationTransaction',
    'User',
    'DataEntry',
]

